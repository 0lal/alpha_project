import grpc
import time
import logging
import threading
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker

# -----------------------------------------------------------------------------
# Core Infrastructure Imports
# استيراد البنية التحتية التي بنيناها سابقاً
# -----------------------------------------------------------------------------
from ui.core.config_provider import config
from ui.core.event_hub import event_hub
from ui.core.logger_sink import logger_sink

# -----------------------------------------------------------------------------
# gRPC Generated Modules Import
# محاولة استيراد ملفات البروتوكول المولدة آلياً.
# التنبؤ بالمشكلة: إذا لم يتم توليد الملفات بعد، لا يجب أن ينهار البرنامج بالكامل.
# -----------------------------------------------------------------------------
try:
    # نفترض أن الملفات المولدة موجودة في brain/generated أو مسار مشابه
    # بناءً على الملفات التي رفعتها: brain/generated/brain_service_pb2.py
    import sys
    from pathlib import Path
    
    # إضافة مسار المجلدات المولدة للتأكد من رؤيتها
    generated_path = config.project_root / "brain" / "generated"
    if str(generated_path) not in sys.path:
        sys.path.append(str(generated_path))

    import brain_service_pb2 as pb
    import brain_service_pb2_grpc as pb_grpc
    import common_types_pb2 as common_pb
    PROTO_AVAILABLE = True
except ImportError as e:
    logger_sink.log_system_event("Bridge", "CRITICAL", f"❌ gRPC Modules missing: {e}. Running in Offline Mode.")
    PROTO_AVAILABLE = False

# -----------------------------------------------------------------------------
# The Bridge Class
# -----------------------------------------------------------------------------
class AlphaBridge(QObject):
    """
    The High-Speed Uplink between UI (Python) and Engine (Rust).
    
    المهام الجنائية والتشغيلية:
    1. إدارة قناة gRPC بشكل آمن (Thread-Safe).
    2. استعادة الاتصال تلقائياً عند انقطاع المحرك (Resilience).
    3. تحويل البيانات الثنائية (Protobuf) إلى إشارات بايثون (Signals).
    """
    
    _instance = None
    _lock = QMutex() # قفل لمنع تضارب البيانات بين الخيوط

    def __init__(self):
        super().__init__()
        if AlphaBridge._instance is not None:
            raise Exception("AlphaBridge is a Singleton!")
        
        self.channel = None
        self.stub = None
        self.is_connected = False
        self._shutdown_flag = False
        
        # خيط الاستماع الخلفي (Background Listener Thread)
        # وظيفته: البقاء مستيقظاً لانتظار الرسائل من السيرفر
        self.listener_thread = None

        logger_sink.log_system_event("Bridge", "INFO", "🌉 Alpha Bridge Initialized.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaBridge()
        return cls._instance

    # -------------------------------------------------------------------------
    # Connection Management (إدارة الاتصال)
    # -------------------------------------------------------------------------
    def connect_engine(self):
        """
        إنشاء الاتصال مع محرك Rust.
        يتم قراءة العنوان والمنفذ من ConfigProvider لضمان المرونة.
        """
        if not PROTO_AVAILABLE:
            logger_sink.log_system_event("Bridge", "ERROR", "Cannot connect: Protobuf files missing.")
            return

        host = config.get("network.grpc.brain_service.host", "localhost")
        port = config.get("network.grpc.brain_service.port", 50051)
        address = f"{host}:{port}"

        logger_sink.log_system_event("Bridge", "INFO", f"🔌 Attempting connection to Nervous System at {address}...")

        try:
            # إنشاء قناة اتصال
            self.channel = grpc.insecure_channel(address)
            self.stub = pb_grpc.BrainServiceStub(self.channel)
            
            # اختبار الاتصال (Ping)
            # نستخدم مهلة زمنية قصيرة (Timeout) لعدم تجميد الواجهة
            future = grpc.channel_ready_future(self.channel)
            future.result(timeout=2.0)
            
            self.is_connected = True
            event_hub.connection_state_changed.emit("RustEngine", "CONNECTED", 0.0)
            logger_sink.log_system_event("Bridge", "SUCCESS", "✅ Bridge Established. Uplink Active.")

            # بدء خيط الاستماع للبيانات المتدفقة
            self._start_listener()

        except grpc.FutureTimeoutError:
            self.is_connected = False
            event_hub.connection_state_changed.emit("RustEngine", "TIMEOUT", 999.0)
            logger_sink.log_system_event("Bridge", "WARNING", "⚠️ Connection Timed out. Is the Rust Engine running?")
        except Exception as e:
            self.is_connected = False
            event_hub.connection_state_changed.emit("RustEngine", "ERROR", 999.0)
            logger_sink.log_system_event("Bridge", "ERROR", f"❌ Connection Failed: {e}")

    def disconnect_engine(self):
        """قطع الاتصال بأمان وتنظيف الموارد"""
        self._shutdown_flag = True
        if self.channel:
            self.channel.close()
        self.is_connected = False
        logger_sink.log_system_event("Bridge", "INFO", "🛑 Bridge Disconnected Manually.")

    # -------------------------------------------------------------------------
    # Background Listening (التنصت الخلفي)
    # -------------------------------------------------------------------------
    def _start_listener(self):
        """تشغيل خيط منفصل لاستقبال البيانات المتدفقة (Streaming)"""
        if self.listener_thread and self.listener_thread.isRunning():
            return

        self.listener_thread = StreamListenerThread(self.stub)
        # ربط إشارات الخيط بمركز الأحداث الرئيسي
        # هذا هو "التحويل" من بيانات خام إلى أحداث نظام
        self.listener_thread.market_data_received.connect(self._handle_market_data)
        self.listener_thread.log_received.connect(self._handle_remote_log)
        self.listener_thread.start()

    # -------------------------------------------------------------------------
    # Command Execution (إرسال الأوامر)
    # -------------------------------------------------------------------------
    def send_command(self, command_type: str, payload: Dict[str, Any]):
        """
        إرسال أمر إلى العقل (Brain).
        تحذير جنائي: يتم تغليف الأمر في Try/Except لمنع انهيار الواجهة إذا فشل الإرسال.
        """
        if not self.is_connected or not self.stub:
            logger_sink.log_system_event("Bridge", "WARNING", "🚫 Cannot send command: Offline.")
            return

        # تشغيل الأمر في خيط منفصل (QThread) لمنع تجميد الزر الذي تم ضغطه
        # (Fire and Forget)
        threading.Thread(target=self._send_command_worker, args=(command_type, payload)).start()

    def _send_command_worker(self, command_type: str, payload: Dict):
        """Worker function for sending commands blocking-ly in a background thread"""
        try:
            # تحويل القاموس إلى Protobuf Request (هنا نحتاج منطق تحويل دقيق)
            # للتبسيط، نفترض أن لدينا رسالة عامة "ControlCommand"
            req = pb.ControlCommand(
                type=command_type,
                params=str(payload) # إرسال البيانات كسلسلة نصية مبدئياً
            )
            
            response = self.stub.ExecuteCommand(req, timeout=5.0)
            
            # إرسال الاستجابة عبر EventHub
            event_hub.command_response_received.emit(
                response.command_id, 
                response.result, 
                response.success
            )
            
        except grpc.RpcError as e:
            logger_sink.log_system_event("Bridge", "ERROR", f"❌ RPC Error: {e.details()}")

    # -------------------------------------------------------------------------
    # Data Handlers (معالجات البيانات الواردة)
    # -------------------------------------------------------------------------
    def _handle_market_data(self, ticker, price, volume):
        """توجيه بيانات السوق إلى EventHub"""
        event_hub.post_market_tick(ticker, price, volume)

    def _handle_remote_log(self, level, source, msg):
        """توجيه سجلات Rust إلى LoggerSink"""
        logger_sink.process_external_log(level, source, msg)


# -----------------------------------------------------------------------------
# Stream Listener Thread (الخيط الخفي)
# -----------------------------------------------------------------------------
class StreamListenerThread(QThread):
    """
    خيط متخصص في الاستماع لتدفق البيانات (Telemetry Stream).
    يعمل بشكل مستقل عن الواجهة الرسومية.
    """
    market_data_received = pyqtSignal(str, float, float)
    log_received = pyqtSignal(str, str, str)

    def __init__(self, stub):
        super().__init__()
        self.stub = stub
        self._keep_running = True

    def run(self):
        """
        حلقة الاستقبال اللانهائية.
        التحليل الجنائي: هذه الحلقة يجب أن تكون صلبة جداً. إذا انقطع الاتصال،
        يجب أن تنهي نفسها بهدوء أو تحاول إعادة الاتصال (متروك للـ Bridge).
        """
        try:
            # طلب فتح قناة البث
            request = pb.StreamRequest(client_id="UI_Main_Cockpit")
            
            # هذا الاستدعاء يبقى مفتوحاً (Blocking Iterator)
            stream = self.stub.StreamTelemetry(request)
            
            for message in stream:
                if not self._keep_running:
                    break
                
                # توجيه الرسالة حسب نوعها (Oneof field in Protobuf)
                if message.HasField("market_tick"):
                    self.market_data_received.emit(
                        message.market_tick.symbol,
                        message.market_tick.price,
                        message.market_tick.volume
                    )
                elif message.HasField("log_entry"):
                    self.log_received.emit(
                        message.log_entry.level,
                        message.log_entry.source,
                        message.log_entry.message
                    )
                # يمكن إضافة المزيد من الحالات هنا (Alerts, Heartbeats)

        except grpc.RpcError as e:
            # التعامل مع انقطاع الاتصال
            if e.code() == grpc.StatusCode.CANCELLED:
                pass # إغلاق طبيعي
            else:
                event_hub.connection_state_changed.emit("Listener", "BROKEN", 0.0)
        except Exception as e:
            event_hub.system_log_received.emit("ERROR", "StreamThread", str(e))

    def stop(self):
        self._keep_running = False
        self.wait()

# -----------------------------------------------------------------------------
# Global Accessor
# -----------------------------------------------------------------------------
bridge = AlphaBridge.get_instance()