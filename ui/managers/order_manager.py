import uuid
import time
import logging
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

# --- استيراد البنية التحتية الأساسية ---
from ui.core.config_provider import config
from ui.core.state_store import state_store
from ui.core.event_hub import event_hub
from ui.core.bridge import bridge
from ui.core.logger_sink import logger_sink

class AlphaOrderManager(QObject):
    """
    The Gatekeeper of Liquidity.
    
    الوظيفة:
    1. استلام طلبات التداول من الواجهة.
    2. إجراء فحوصات السلامة (Sanity Checks) والمخاطر (Risk Checks) محلياً.
    3. توليد معرفات تتبع فريدة (UUID) للأغراض الجنائية.
    4. تمرير الأمر إلى الجسر (Bridge) فقط إذا كان سليماً.
    
    المبدأ الأمني: "لا تثق بالواجهة أبداً" (Zero Trust UI).
    """

    # إشارات لإبلاغ الواجهة بمصير الأمر فوراً (قبل رد السيرفر)
    # Payload: (client_order_id, message)
    order_rejected_locally = pyqtSignal(str, str)
    
    # Payload: (client_order_id, status) -> 'PENDING', 'SENT', 'ACKNOWLEDGED'
    order_status_changed = pyqtSignal(str, str)

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaOrderManager._instance is not None:
            raise Exception("OrderManager is a Singleton!")
        
        # --- Memory State ---
        # تتبع الأوامر الحية محلياً حتى نعرف مصيرها
        self._active_orders: Dict[str, Dict] = {}
        
        # لمنع التكرار (Debouncing)
        self._last_order_time = 0.0
        self._last_order_hash = ""

        # --- Configuration Limits ---
        self.min_order_value = config.get("logic.risk.min_order_value_usd", 10.0)
        self.max_order_value = config.get("logic.risk.max_order_value_usd", 100000.0)
        
        # الاشتراك في استجابات الأوامر القادمة من الجسر
        event_hub.command_response_received.connect(self._on_bridge_response)

        logger_sink.log_system_event("OrderManager", "INFO", "🛡️ Pre-Trade Validation Engine Online.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaOrderManager()
        return cls._instance

    # =========================================================================
    # 1. The Execution Method (نقطة الدخول)
    # =========================================================================
    def submit_order(self, symbol: str, side: str, order_type: str, 
                     qty: float, price: float = 0.0, time_in_force: str = "GTC"):
        """
        محاولة إرسال أمر تداول.
        لن يمر هذا الأمر إلا إذا اجتاز جميع الفحوصات الجنائية.
        """
        with QMutexLocker(self._lock):
            # 1. Generate Forensic ID (هوية الأمر)
            # نستخدم UUID4 لضمان عدم تكرار المعرف عالمياً حتى لو أعدنا تشغيل الجهاز
            client_order_id = str(uuid.uuid4())
            
            # 2. Forensic Context Logging (توثيق النية)
            logger_sink.log_system_event(
                "OrderManager", "DEBUG", 
                f"📝 Intent to trade: {side} {qty} {symbol} @ {price} (ID: {client_order_id[:8]})"
            )

            # 3. Pre-Trade Checks (المحكمة الميدانية)
            is_valid, rejection_reason = self._run_pre_trade_checks(
                symbol, side, qty, price
            )

            if not is_valid:
                # رفض الأمر محلياً وحماية الشبكة من التلوث
                logger_sink.log_system_event(
                    "OrderManager", "WARNING", 
                    f"⛔ Order Blocked Locally: {rejection_reason} (ID: {client_order_id[:8]})"
                )
                self.order_rejected_locally.emit(client_order_id, rejection_reason)
                return

            # 4. Debouncing (منع التكرار)
            current_time = time.time()
            order_hash = f"{symbol}{side}{qty}{price}"
            if (current_time - self._last_order_time < 0.5) and (order_hash == self._last_order_hash):
                logger_sink.log_system_event("OrderManager", "WARNING", "🚫 Duplicate order click detected. Ignored.")
                return
            
            self._last_order_time = current_time
            self._last_order_hash = order_hash

            # 5. Construct Payload (تجهيز الشحنة)
            order_payload = {
                "client_order_id": client_order_id,
                "symbol": symbol,
                "side": side.upper(),
                "type": order_type.upper(),
                "quantity": qty,
                "price": price,
                "time_in_force": time_in_force,
                "timestamp": int(current_time * 1000)
            }

            # 6. Store in Memory (Optimistic State)
            self._active_orders[client_order_id] = {
                "status": "SENDING",
                "details": order_payload,
                "sent_at": current_time
            }

            # 7. Transmit via Bridge (الإطلاق)
            self.order_status_changed.emit(client_order_id, "SENDING")
            bridge.send_command("PLACE_ORDER", order_payload)
            
            logger_sink.log_system_event(
                "OrderManager", "INFO", 
                f"🚀 Order Transmitted: {client_order_id[:8]} -> Bridge"
            )

    # =========================================================================
    # 2. Pre-Trade Logic (قواعد الاشتباك)
    # =========================================================================
    def _run_pre_trade_checks(self, symbol: str, side: str, qty: float, price: float) -> (bool, str):
        """
        فحص القواعد قبل الإزعاج وإرسال البيانات عبر الشبكة.
        """
        # A. فحص حالة النظام
        if state_store.get_value("risk_level") == "PANIC":
            return False, "System is in PANIC mode. Trading halted."
        
        if not bridge.is_connected:
            return False, "No connection to Neural Engine."

        # B. فحص المدخلات المنطقية
        if qty <= 0:
            return False, "Quantity must be positive."
        if price < 0:
            return False, "Price cannot be negative."

        # C. فحص الحدود المالية (Estimated)
        estimated_value = qty * price if price > 0 else 0 # لأوامر السوق قد يكون السعر 0
        if estimated_value > 0:
            if estimated_value < self.min_order_value:
                return False, f"Order value (${estimated_value:.2f}) below minimum (${self.min_order_value})."
            if estimated_value > self.max_order_value:
                return False, f"Order value (${estimated_value:.2f}) exceeds safety limit (${self.max_order_value})."

        # D. فحص الرصيد التقريبي (اختياري - يعتمد على دقة StateStore)
        # هذا الفحص "استشاري" وليس نهائي، لأن الرصيد قد يتغير في السيرفر في اجزاء من الثانية
        # لكنه مفيد لمنع الأوامر الغبية الواضحة
        # account_balance = state_store.get_value("account_balance", 0.0)
        # if side.upper() == "BUY" and estimated_value > account_balance:
        #    return False, "Insufficient funds (Local Check)."

        return True, ""

    def cancel_order(self, client_order_id: str):
        """إلغاء أمر محدد"""
        logger_sink.log_system_event("OrderManager", "INFO", f"❌ Requesting Cancel for: {client_order_id}")
        bridge.send_command("CANCEL_ORDER", {"client_order_id": client_order_id})

    def panic_cancel_all(self):
        """زر التدمير الذاتي: إلغاء كل الأوامر فوراً"""
        logger_sink.log_system_event("OrderManager", "CRITICAL", "☢️ PANIC: CANCELLING ALL ORDERS")
        bridge.send_command("CANCEL_ALL", {})

    # =========================================================================
    # 3. Response Handling (استلام النتائج)
    # =========================================================================
    def _on_bridge_response(self, command_id: str, result: str, success: bool):
        """
        يتم استدعاؤها عندما يرد الجسر على أمر أرسلناه.
        ملاحظة: command_id هنا يجب أن يطابق client_order_id الذي أرسلناه.
        """
        with QMutexLocker(self._lock):
            if command_id in self._active_orders:
                if success:
                    self._active_orders[command_id]["status"] = "ACCEPTED"
                    self.order_status_changed.emit(command_id, "ACCEPTED")
                    # لا نحذفها من هنا، بل ننتظر تحديث Execution Report من StreamHandler
                    # لتأكيد التنفيذ الفعلي.
                else:
                    self._active_orders[command_id]["status"] = "REJECTED"
                    self.order_rejected_locally.emit(command_id, f"Engine Rejected: {result}")
                    logger_sink.log_system_event("OrderManager", "ERROR", f"❌ Engine Rejected Order {command_id}: {result}")
                    # حذف الأمر المرفوض لتنظيف الذاكرة
                    del self._active_orders[command_id]

# Global Accessor
order_manager = AlphaOrderManager.get_instance()