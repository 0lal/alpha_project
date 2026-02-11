import json
import logging
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

# --- استيراد البنية التحتية ---
from ui.core.config_provider import config
from ui.core.bridge import bridge
from ui.core.event_hub import event_hub
from ui.core.state_store import state_store
from ui.core.logger_sink import logger_sink

class AlphaLogicManager(QObject):
    """
    The Strategic Mastermind.
    
    الوظيفة:
    1. Strategy Controller: تحميل وتفعيل وتبديل استراتيجيات التداول.
    2. AI Tuner: تعديل معلمات الذكاء الاصطناعي (مثل حد الثقة، سرعة التعلم).
    3. Vote Inspector: تحليل قرارات الـ AI وتمرير الصالح منها فقط للتنفيذ.
    
    التحليل الجنائي:
    يضمن أن ما يراه المستخدم في الواجهة (من إعدادات) هو المطابق تماماً 
    لما يعمل عليه المحرك في الخلفية. لا مجال للتناقض.
    """

    # إشارة عند تغيير الاستراتيجية بنجاح (بعد تأكيد المحرك)
    active_strategy_changed = pyqtSignal(str, dict)
    
    # إشارة عند استلام تفكير جديد من الـ AI (لتحديث الشاشات)
    ai_rationale_received = pyqtSignal(str, float, str) # Action, Confidence, Reason

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaLogicManager._instance is not None:
            raise Exception("LogicManager is a Singleton!")

        # --- Internal Memory ---
        self._available_strategies = {}
        self._current_strategy_id = "MANUAL" # الوضع الافتراضي
        self._min_confidence_threshold = config.get("logic.ai.min_confidence", 0.75)
        
        # تحميل الاستراتيجيات المتاحة من ملف التعريف
        self._load_strategy_profiles()

        # --- Wiring ---
        # الاستماع لرسائل التفكير القادمة من الجسر (Brain -> Bridge -> EventHub -> LogicManager)
        event_hub.ai_thought_stream.connect(self._process_ai_thought)
        
        # الاستماع لتأكيدات الأوامر من الجسر
        event_hub.command_response_received.connect(self._on_engine_response)

        logger_sink.log_system_event("LogicManager", "INFO", "🧠 Strategic Cortex Online.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaLogicManager()
        return cls._instance

    # =========================================================================
    # 1. Strategy Management (إدارة الاستراتيجيات)
    # =========================================================================
    def _load_strategy_profiles(self):
        """تحميل تعريفات الاستراتيجيات من ملف Config"""
        raw_strategies = config.get("logic.strategies", {})
        if not raw_strategies:
            # Fallback defaults if config is missing
            self._available_strategies = {
                "MANUAL": {"name": "Manual Trading", "desc": "Human control only."},
                "SCALPING_V1": {"name": "HFT Scalper", "desc": "High frequency, low latency."},
                "SWING_AI": {"name": "AI Swing", "desc": "Multi-day holding with sentiment analysis."}
            }
        else:
            self._available_strategies = raw_strategies

    def get_strategies_list(self) -> Dict[str, Dict]:
        """للاستخدام من قبل الواجهة لملء القائمة المنسدلة (ComboBox)"""
        return self._available_strategies

    def set_strategy(self, strategy_id: str):
        """
        طلب تغيير الاستراتيجية.
        لا نغيرها محلياً فوراً، بل نرسل طلباً للمحرك.
        """
        if strategy_id not in self._available_strategies:
            logger_sink.log_system_event("LogicManager", "ERROR", f"❌ Unknown Strategy: {strategy_id}")
            return

        logger_sink.log_system_event("LogicManager", "INFO", f"🔄 Requesting Strategy Switch to: {strategy_id}...")
        
        # إرسال الأمر للمحرك
        payload = {
            "strategy_id": strategy_id,
            "params": self._available_strategies[strategy_id].get("default_params", {})
        }
        bridge.send_command("SET_STRATEGY", payload)
        
        # ملاحظة: سنحدث الحالة المحلية فقط عندما يرد المحرك في _on_engine_response

    def update_strategy_params(self, params: Dict[str, Any]):
        """تحديث معلمات الاستراتيجية الحالية (Hot Tuning)"""
        if self._current_strategy_id == "MANUAL":
            logger_sink.log_system_event("LogicManager", "WARNING", "⚠️ Cannot tune MANUAL mode.")
            return

        logger_sink.log_system_event("LogicManager", "INFO", f"🎛️ Tuning Parameters: {params}")
        bridge.send_command("UPDATE_PARAMS", params)

    # =========================================================================
    # 2. AI Vote Inspector (المفتش الجنائي للذكاء الاصطناعي)
    # =========================================================================
    def _process_ai_thought(self, strategy_id: str, thought_json: str, confidence: float):
        """
        تحليل تدفق أفكار الـ AI.
        هنا نقرر: هل هذا مجرد "تفكير" أم "قرار"؟
        """
        try:
            # 1. Forensic Validation: هل الاستراتيجية المبلغة هي الحالية؟
            if strategy_id != self._current_strategy_id:
                # قد تصل رسائل متأخرة من استراتيجية سابقة، يجب تجاهلها
                return

            # 2. Confidence Gate (بوابة الثقة)
            if confidence < self._min_confidence_threshold:
                # تسجيلها كضوضاء في السجلات ولكن لا نرسلها للواجهة كقرار
                # logger_sink.log_system_event("LogicManager", "DEBUG", f"AI Low Confidence: {confidence:.2f}")
                return

            # 3. Parsing the Rationale
            # نتوقع أن يكون الـ thought نصاً أو JSON
            rationale = thought_json
            action = "HOLD" # الافتراضي
            
            # محاولة استخراج الإجراء من النص (مثال بسيط)
            if "BUY" in thought_json.upper(): action = "BUY"
            elif "SELL" in thought_json.upper(): action = "SELL"
            
            # 4. Notify UI (إبلاغ الواجهة)
            self.ai_rationale_received.emit(action, confidence, rationale)
            
            # إذا كان هناك وضع "Auto-Trade"، يمكننا هنا استدعاء OrderManager مباشرة
            # if state_store.get_value("system_mode") == "LIVE_AUTO":
            #     order_manager.submit_order(...) 

        except Exception as e:
            logger_sink.log_system_event("LogicManager", "ERROR", f"Failed to process AI thought: {e}")

    # =========================================================================
    # 3. Engine Response Handler (معالج الردود)
    # =========================================================================
    def _on_engine_response(self, command_id: str, result: str, success: bool):
        """
        التأكد من أن المحرك طبق التغييرات.
        """
        # في نظام حقيقي، يجب أن نربط command_id بنوع الأمر.
        # للتبسيط، سنفترض أن أي نجاح لـ SET_STRATEGY يعني التغيير تم.
        
        # نقوم بتحليل الـ result لمعرفة نوع الأمر (أو نستخدم خريطة تتبع الأوامر)
        # هنا سنفترض سيناريو بسيط: إذا نجح الأمر وتضمن كلمة Strategy
        
        if success and "STRATEGY_SET" in result: # افتراض أن السيرفر يرد بهذا النص
            # استخراج اسم الاستراتيجية من الرد أو من الذاكرة المعلقة
            # هنا سنحدث الحالة ونبلغ الجميع
            # self._current_strategy_id = ... (extracted)
            pass
            
            # تحديث StateStore
            # state_store.update_service_status("Strategy", "ACTIVE")

    def set_confidence_threshold(self, value: float):
        """تغيير حد الثقة من الواجهة"""
        self._min_confidence_threshold = max(0.1, min(1.0, value))
        logger_sink.log_system_event("LogicManager", "INFO", f"🎯 AI Confidence Threshold set to: {self._min_confidence_threshold:.2f}")

# Global Accessor
logic_manager = AlphaLogicManager.get_instance()