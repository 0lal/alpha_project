import logging
import threading
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

# استيراد المكونات الأساسية للتكامل
# نستخدم LoggerSink بدلاً من print للحفاظ على السجل الجنائي
from ui.core.logger_sink import logger_sink

class AlphaStateStore(QObject):
    """
    The Single Source of Truth (SSOT).
    
    الوظيفة:
    مخزن مركزي تفاعلي (Reactive) يحتفظ بحالة النظام الحالية.
    عندما تتغير أي قيمة هنا، يتم إشعار المكونات المشتركة فوراً.
    
    الميزات الجنائية:
    1. Thread-Safe: محمي بـ Mutex لمنع تضارب الكتابة من خيوط متعددة.
    2. Audit Trail: يحتفظ بسجل لآخر التغييرات لتتبع من غير ماذا ومتى.
    3. Distinct Updates: لا يطلق إشارة إذا كانت القيمة الجديدة تطابق القديمة (منع الضجيج).
    """

    # =========================================================================
    # Signals (الأعصاب الناقلة للتغيير)
    # =========================================================================
    
    # عندما يتغير وضع النظام (Live, Paper, Backtest)
    mode_changed = pyqtSignal(str) 
    
    # عندما يتغير مستوى المخاطر (Normal, Elevated, Critical)
    risk_level_changed = pyqtSignal(str)
    
    # عندما تتغير حالة خدمة معينة (مثل Brain, Execution, DataFeed)
    service_status_changed = pyqtSignal(str, str) # service_name, status
    
    # إشارة عامة لتغير أي بيانات (للمراقبة العامة)
    state_updated = pyqtSignal(str, object) # key, new_value

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaStateStore._instance is not None:
            raise Exception("StateStore is a Singleton!")
        
        # --- The State Data (الحالة الراهنة) ---
        self._state = {
            "system_mode": "IDLE",       # IDLE, LIVE, PAPER, BACKTEST
            "risk_level": "NORMAL",      # NORMAL, ELEVATED, CRITICAL, PANIC
            "connection_global": False,  # هل نحن متصلون بالكامل؟
            "active_strategy": "None",   # اسم الاستراتيجية الحالية
            "account_balance": 0.0,      # الرصيد الحالي
            "pnl_session": 0.0,          # الربح/الخسارة في هذه الجلسة
            "open_positions": 0,         # عدد الصفقات المفتوحة
            "services": {}               # حالة كل خدمة فرعية
        }

        # --- Forensic Audit Trail (سجل التدقيق) ---
        # نحتفظ بآخر 100 تغيير للحالة للتشخيص
        self._history = deque(maxlen=100)
        
        logger_sink.log_system_event("StateStore", "INFO", "🧠 Reactive Memory Initialized.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaStateStore()
        return cls._instance

    # =========================================================================
    # Setters (طرق التحديث الذكية)
    # =========================================================================

    def set_mode(self, new_mode: str):
        """تغيير وضع التشغيل (تداول حقيقي، محاكاة، إلخ)"""
        new_mode = new_mode.upper()
        if self._update_state("system_mode", new_mode):
            self.mode_changed.emit(new_mode)
            # تغيير الوضع حدث جلل، يجب تسجيله بوضوح
            logger_sink.log_system_event("StateStore", "WARNING", f"🔄 System Mode switched to: {new_mode}")

    def set_risk_level(self, level: str):
        """
        تغيير مستوى المخاطر.
        هذا هو التغيير الأخطر، ويجب أن تتفاعل الواجهة معه فوراً (تغيير الألوان).
        """
        level = level.upper()
        if self._update_state("risk_level", level):
            self.risk_level_changed.emit(level)
            
            if level in ["CRITICAL", "PANIC"]:
                logger_sink.log_system_event("StateStore", "CRITICAL", f"☢️ RISK LEVEL ESCALATED: {level}")

    def update_service_status(self, service_name: str, status: str):
        """تحديث حالة خدمة فرعية (مثل: Brain is Ready)"""
        with QMutexLocker(self._lock):
            current_services = self._state["services"]
            if current_services.get(service_name) != status:
                current_services[service_name] = status
                self.service_status_changed.emit(service_name, status)
                self._record_history(f"service_{service_name}", status)

    def update_financials(self, balance: float, pnl: float, positions: int):
        """تحديث البيانات المالية (تأتي عادة من Bridge بتردد عالي)"""
        # نستخدم تحديثاً صامتاً نسبياً لعدم إغراق السجلات، لكن نطلق الإشارة للواجهة
        changed = False
        with QMutexLocker(self._lock):
            if self._state["account_balance"] != balance:
                self._state["account_balance"] = balance
                changed = True
            if self._state["pnl_session"] != pnl:
                self._state["pnl_session"] = pnl
                changed = True
            self._state["open_positions"] = positions
        
        if changed:
            # نطلق إشارة عامة للمكونات المالية
            self.state_updated.emit("financials", {
                "balance": balance, "pnl": pnl, "positions": positions
            })

    # =========================================================================
    # Getters (طرق القراءة الآمنة)
    # =========================================================================

    def get_value(self, key: str, default: Any = None) -> Any:
        """قراءة قيمة من الحالة بأمان"""
        with QMutexLocker(self._lock):
            return self._state.get(key, default)

    def get_all_services(self) -> Dict[str, str]:
        """نسخة من حالة الخدمات"""
        with QMutexLocker(self._lock):
            return self._state["services"].copy()

    def get_history(self) -> List[Dict]:
        """استرجاع السجل الجنائي للتغييرات"""
        with QMutexLocker(self._lock):
            return list(self._history)

    # =========================================================================
    # Internal Logic (المنطق الداخلي)
    # =========================================================================

    def _update_state(self, key: str, value: Any) -> bool:
        """
        دالة داخلية لتحديث الحالة وفحص ما إذا كانت القيمة قد تغيرت فعلاً.
        تعيد True إذا حدث تغيير، و False إذا كانت القيمة هي نفسها.
        """
        with QMutexLocker(self._lock):
            if self._state.get(key) == value:
                return False  # لا داعي لإزعاج النظام، القيمة لم تتغير
            
            self._state[key] = value
            self._record_history(key, value)
            return True

    def _record_history(self, key: str, value: Any):
        """تسجيل التغيير في سجل التدقيق الداخلي"""
        # ملاحظة: الـ Lock مأخوذ بالفعل من الدالة المستدعية، لا داعي لطلبه مرة أخرى
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "key": key,
            "value": str(value),
            "thread": threading.current_thread().name
        }
        self._history.append(entry)

# Global Accessor
state_store = AlphaStateStore.get_instance()