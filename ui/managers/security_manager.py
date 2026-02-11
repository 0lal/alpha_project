import time
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

# --- استيراد البنية التحتية ---
from ui.core.config_provider import config
from ui.core.state_store import state_store
from ui.core.event_hub import event_hub
from ui.core.logger_sink import logger_sink
from ui.core.bridge import bridge

# نحتاج الوصول لمدير الأوامر لتنفيذ "الإعدام الفوري" للصفقات
from ui.managers.order_manager import order_manager

class AlphaSecurityManager(QObject):
    """
    The Guardian of the Citadel.
    
    الوظيفة:
    1. إدارة حالات الطوارئ (Panic Mode) وتنفيذ بروتوكولات الإيقاف.
    2. التحكم في قفل الواجهة (Session Lock) لمنع المتطفلين.
    3. التحقق من الصلاحيات (Authorization) قبل تنفيذ الإجراءات الحساسة.
    
    المبدأ الجنائي:
    "الأمن ليس ميزة، بل هو الأساس". أي إجراء أمني يجب أن يكون قاطعاً، فورياً، ومسجلاً.
    """

    # إشارات الحالة الأمنية
    # Payload: (is_locked: bool, reason: str)
    session_lock_changed = pyqtSignal(bool, str)
    
    # Payload: (timestamp: float, triggered_by: str)
    panic_mode_activated = pyqtSignal(float, str)
    
    # Payload: (timestamp: float, authorized_by: str)
    panic_mode_deactivated = pyqtSignal(float, str)

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaSecurityManager._instance is not None:
            raise Exception("SecurityManager is a Singleton!")

        # --- Security State ---
        self._is_interface_locked = False
        self._master_pin = config.get_secret("APP_MASTER_PIN", "0000") # يجب تغييره في الإنتاج
        self._active_session_token = None

        logger_sink.log_system_event("SecurityManager", "INFO", "🛡️ Citadel Guardian Active.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaSecurityManager()
        return cls._instance

    # =========================================================================
    # 1. The Panic Protocol (بروتوكول الطوارئ)
    # =========================================================================
    def trigger_panic(self, reason: str = "User Initiated"):
        """
        THE BIG RED BUTTON.
        عند استدعاء هذه الدالة، يجب أن يتوقف كل شيء فوراً.
        """
        with QMutexLocker(self._lock):
            # 1. Forensic Logging: توثيق اللحظة والسبب بدقة
            logger_sink.log_system_event(
                "SecurityManager", "CRITICAL", 
                f"🚨 PANIC TRIGGERED! Reason: {reason}"
            )

            # 2. Update System State (Single Source of Truth)
            # هذا سيجعل الواجهة بالكامل تتحول للون الأحمر
            state_store.set_risk_level("PANIC")
            
            # 3. Kill Switch: Cancel All Orders Locally & Remotely
            # نأمر مدير الأوامر بإلغاء كل شيء فوراً
            order_manager.panic_cancel_all()

            # 4. Halt Engine Strategy
            # نرسل أمراً للمحرك لإيقاف الاستراتيجيات (ولليس فقط إلغاء الأوامر)
            if bridge.is_connected:
                bridge.send_command("HALT_TRADING", {"reason": reason})
            else:
                logger_sink.log_system_event(
                    "SecurityManager", "WARNING", 
                    "⚠️ Panic Triggered while Offline! Local locks applied only."
                )

            # 5. Notify UI
            self.panic_mode_activated.emit(time.time(), reason)

    def disengage_panic(self, pin_code: str) -> bool:
        """
        إلغاء وضع الطوارئ.
        يتطلب PIN Code لمنع الإلغاء بالخطأ أو من قبل شخص غير مصرح له.
        """
        with QMutexLocker(self._lock):
            if pin_code != self._master_pin:
                logger_sink.log_system_event("SecurityManager", "WARNING", "⛔ Failed Panic Reset attempt: Invalid PIN")
                return False

            logger_sink.log_system_event("SecurityManager", "SUCCESS", "✅ Panic Mode Disengaged. System Returning to Normal.")
            
            # إعادة الحالة للطبيعي
            state_store.set_risk_level("NORMAL")
            
            # إبلاغ المحرك بإمكانية استئناف العمل (إذا أردنا ذلك)
            if bridge.is_connected:
                bridge.send_command("RESUME_TRADING", {})

            self.panic_mode_deactivated.emit(time.time(), "Admin")
            return True

    # =========================================================================
    # 2. Session Locking (قفل الواجهة)
    # =========================================================================
    def lock_interface(self):
        """قفل الواجهة لمنع الضغط على الأزرار"""
        if not self._is_interface_locked:
            self._is_interface_locked = True
            self.session_lock_changed.emit(True, "User Locked")
            logger_sink.log_system_event("SecurityManager", "INFO", "🔒 Interface Locked.")

    def unlock_interface(self, pin_code: str) -> bool:
        """فك قفل الواجهة"""
        if pin_code == self._master_pin:
            self._is_interface_locked = False
            self.session_lock_changed.emit(False, "Admin Unlocked")
            logger_sink.log_system_event("SecurityManager", "INFO", "🔓 Interface Unlocked.")
            return True
        else:
            return False

    def is_locked(self) -> bool:
        """هل الواجهة مقفلة الآن؟"""
        return self._is_interface_locked

    # =========================================================================
    # 3. Access Control (التحقق من الصلاحيات)
    # =========================================================================
    def validate_action(self, action_type: str) -> bool:
        """
        يجب استدعاء هذه الدالة قبل أي إجراء حساس (مثل إرسال أمر شراء).
        """
        # 1. Check Lock State
        if self._is_interface_locked:
            logger_sink.log_system_event("SecurityManager", "WARNING", f"⛔ Action '{action_type}' blocked: Interface is Locked.")
            return False

        # 2. Check Panic State
        if state_store.get_value("risk_level") == "PANIC":
             # نسمح فقط بإجراءات معينة في وضع الذعر (مثل الإلغاء)
             if action_type not in ["CANCEL_ALL", "DISENGAGE_PANIC", "EXIT_APP"]:
                 logger_sink.log_system_event("SecurityManager", "WARNING", f"⛔ Action '{action_type}' blocked: System in PANIC mode.")
                 return False

        return True

    def rotate_master_pin(self, old_pin: str, new_pin: str) -> bool:
        """تغيير الرمز السري (Forensic Event)"""
        if old_pin == self._master_pin and len(new_pin) >= 4:
            self._master_pin = new_pin
            logger_sink.log_system_event("SecurityManager", "WARNING", "🔐 Master PIN changed successfully.")
            return True
        return False

# Global Accessor
security_manager = AlphaSecurityManager.get_instance()