import time
import logging
from collections import deque, defaultdict
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker

# استيراد البنية التحتية
from ui.core.config_provider import config
from ui.core.event_hub import event_hub
from ui.core.logger_sink import logger_sink

class AlphaStreamHandler(QObject):
    """
    The Traffic Controller & Data Sanitizer.
    
    الوظيفة الأساسية:
    حماية الواجهة (UI) من الغرق في طوفان البيانات القادمة من المحرك.
    
    الميكانيكية (Technique):
    يستخدم نمط "Throttling / Conflation". يستقبل آلاف التحديثات،
    لكنه يجمعها في الذاكرة ويرسل "دفعة" (Batch) واحدة للواجهة كل فترة محددة (UI_REFRESH_RATE).
    
    الميزات الجنائية:
    1. Anomaly Filter: كشف البيانات الشاذة وحجبها.
    2. Latency Tracker: مراقبة صحة تدفق البيانات.
    3. Blackbox Recorder: الاحتفاظ بآخر 100 حزمة خام للتحليل بعد الانهيار.
    """

    # إشارة الدفعة المجمعة (Batch Signal) - هذه التي يجب أن تستمع لها الواجهة
    # Payload: { 'BTC-USDT': {'price': 50000, 'vol': 1.5, ...}, ... }
    market_data_batch_ready = pyqtSignal(dict)
    
    # إشارة تحذير عند اكتشاف شذوذ في البيانات
    anomaly_detected = pyqtSignal(str, str, float) # ticker, type, value

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaStreamHandler._instance is not None:
            raise Exception("StreamHandler is a Singleton!")

        # --- Configuration ---
        # معدل تحديث الواجهة بالميلي ثانية (30 FPS ≈ 33ms, 10 FPS = 100ms)
        # نستخدم 100ms كقيمة آمنة جداً للأجهزة المتوسطة
        self.refresh_rate_ms = config.get("logic.ui.refresh_rate_ms", 100)
        
        # حدود كشف الشذوذ (مثلاً: تغير 10% في تحديث واحد)
        self.max_price_change_pct = config.get("logic.risk.max_tick_move_pct", 0.10)

        # --- State Buffers (الذاكرة المؤقتة) ---
        # القاموس الذي يجمع أحدث البيانات (Conflation Buffer)
        self._pending_updates: Dict[str, Dict[str, Any]] = {}
        
        # الصندوق الأسود (تخزين آخر الحزم الخام)
        self._blackbox_buffer = deque(maxlen=200)
        
        # تتبع السعر السابق للكشف عن الشذوذ
        self._last_known_prices: Dict[str, float] = {}

        # --- The Heartbeat (الناظم) ---
        self._timer = QTimer()
        self._timer.timeout.connect(self._flush_updates)
        self._timer.start(self.refresh_rate_ms)

        # الاشتراك في القناة الخام (Firehose) القادمة من الجسر
        event_hub.market_tick_received.connect(self._ingest_tick)

        logger_sink.log_system_event("StreamHandler", "INFO", "🌊 Data Conflation Engine Started.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaStreamHandler()
        return cls._instance

    # =========================================================================
    # 1. Ingestion (استقبال البيانات الخام)
    # =========================================================================
    def _ingest_tick(self, ticker: str, price: float, volume: float):
        """
        يتم استدعاء هذه الدالة آلاف المرات في الثانية.
        يجب أن تكون سريعة جداً (O(1)).
        """
        with QMutexLocker(self._lock):
            # 1. Forensic Check: Data Integrity (فحص النزاهة)
            if price <= 0:
                self._report_anomaly(ticker, "ZERO_PRICE", price)
                return

            # 2. Forensic Check: Sudden Moves (فحص القفزات غير المنطقية)
            if ticker in self._last_known_prices:
                last_price = self._last_known_prices[ticker]
                change_pct = abs(price - last_price) / last_price
                if change_pct > self.max_price_change_pct:
                    self._report_anomaly(ticker, "FLASH_MOVE", price)
                    # يمكننا هنا اتخاذ قرار: هل نتجاهل السعر أم نقبله بحذر؟
                    # للسلامة، سنقوم بتسجيله لكن مع تحذير
            
            # 3. Update State (Conflation)
            # نقوم فقط بتحديث القيم في الذاكرة، لا نرسل للواجهة الآن
            self._pending_updates[ticker] = {
                'price': price,
                'volume': volume,
                'timestamp': time.time(),
                'change_pct': 0.0 # سيتم حسابه لاحقاً
            }
            
            # تحديث السعر المرجعي
            self._last_known_prices[ticker] = price
            
            # 4. Blackbox Recording (للتشخيص المستقبلي)
            self._blackbox_buffer.append((time.time(), ticker, price, volume))

    # =========================================================================
    # 2. Flushing (ضخ البيانات للواجهة)
    # =========================================================================
    def _flush_updates(self):
        """
        يتم استدعاؤها بواسطة المؤقت (Timer).
        تقوم بأخذ كل ما تجمع في الذاكرة وإرساله كحزمة واحدة.
        """
        # فحص سريع بدون قفل (Optimization)
        if not self._pending_updates:
            return

        payload = {}
        with QMutexLocker(self._lock):
            # نسخ البيانات وتفريغ المخزن الأصلي فوراً لتقليل وقت القفل
            payload = self._pending_updates.copy()
            self._pending_updates.clear()

        # إرسال الدفعة للواجهة
        if payload:
            self.market_data_batch_ready.emit(payload)
            # لا نسجل في اللوج هنا لأن التكرار عالٍ جداً

    # =========================================================================
    # 3. Forensic & Diagnostic Tools
    # =========================================================================
    def _report_anomaly(self, ticker: str, error_type: str, value: float):
        """الإبلاغ عن بيانات مشبوهة"""
        msg = f"Data Anomaly detected for {ticker}: {error_type} (Value: {value})"
        logger_sink.log_system_event("StreamHandler", "WARNING", msg)
        self.anomaly_detected.emit(ticker, error_type, value)

    def dump_blackbox(self) -> List[tuple]:
        """
        استخراج البيانات الخام الأخيرة.
        يستخدم عند حدوث خطأ لمعرفة ماذا حدث قبل الانهيار مباشرة.
        """
        with QMutexLocker(self._lock):
            return list(self._blackbox_buffer)

    def get_last_price(self, ticker: str) -> float:
        """للاستخدام المتزامن من قبل المديرين (Managers)"""
        with QMutexLocker(self._lock):
            return self._last_known_prices.get(ticker, 0.0)

# Global Accessor
stream_handler = AlphaStreamHandler.get_instance()