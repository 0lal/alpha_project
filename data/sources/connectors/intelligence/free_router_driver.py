import logging
from typing import Optional, Dict, Any, List

# استيراد الأذرع التنفيذية (Drivers) للذكاء الاصطناعي التي تم بناؤها مسبقاً
try:
    from connectors.intelligence.groq_lpu_driver import GroqLPUDriver
    from connectors.intelligence.gemini_driver import GeminiDriver
    # استيراد مدير التكلفة لمعرفة من المتاح والأرخص
    from core.cost_optimizer import cost_optimizer
    from audit.logger_service import audit_logger
except ImportError:
    # حماية من انهيار الاستيراد أثناء الاختبار المنفصل
    logging.critical("🔥 FATAL: Missing Core Components for Free Router!")
    GroqLPUDriver = None
    GeminiDriver = None
    cost_optimizer = None
    audit_logger = None

# إعداد السجل الجنائي للموجه
logger = logging.getLogger("Alpha.Drivers.FreeRouter")

class FreeIntelligenceRouter:
    """
    موجه الذكاء الاصطناعي المجاني (The Free Tier Intelligence Router).
    
    المهام الجنائية:
    1. موازنة الحمل (Load Balancing) بين مزودي الذكاء الاصطناعي لضمان بقاء النظام يعمل 24/7.
    2. تطبيق التوجيه المبني على التكلفة (Cost-Aware Routing) والسرعة.
    3. تطبيق بروتوكول "أنا أعمى" في حال استنفاد كل الموارد (لا تزييف للردود).
    """

    def __init__(self):
        """
        تهيئة الموجه وتجهيز الأذرع المتاحة.
        """
        # تهيئة الدرايفرات (تأخير التهيئة لتجنب أخطاء بدء التشغيل إذا كان أحدهم معطلاً)
        self.groq_driver = GroqLPUDriver() if GroqLPUDriver else None
        self.gemini_driver = GeminiDriver() if GeminiDriver else None
        
        # قائمة المزودين المتاحين تحت تصرف الموجه
        self.available_providers = ["groq", "gemini-1.5-flash"]

    def route_query(self, system_prompt: str, context_data: str, task_type: str = "GENERAL") -> Optional[str]:
        """
        [مركز القيادة] توجيه الطلب لأفضل نموذج متاح حالياً.
        
        المعاملات:
        - system_prompt: التعليمات الصارمة للنموذج (القوانين).
        - context_data: البيانات المالية الخام التي سيتم تحليلها.
        - task_type: نوع المهمة ('QUICK_EXTRACT', 'DEEP_REASONING', 'LARGE_DOCUMENT').
        
        الإرجاع:
        - النص النهائي من الذكاء الاصطناعي، أو None إذا كان النظام "أعمى".
        """
        # 1. تحليل حجم البيانات (Payload Analysis)
        # Groq ينهار إذا تجاوز النص 30,000 حرف. Gemini يستوعب حتى مليون توكن.
        data_length = len(context_data)
        
        if data_length > 25000:
            logger.info("📐 Massive Payload Detected. Forcing route to Gemini Flash (High Context Window).")
            # إذا كان النص ضخماً جداً، الخيار الوحيد الآمن هو Gemini
            preferred_route = "gemini-1.5-flash"
        elif task_type == "QUICK_EXTRACT":
            # الاستخراج السريع يحتاج سرعة LPU من Groq
            preferred_route = "groq"
        else:
            # 2. سؤال الخبير الاقتصادي (Cost Optimizer) عن أفضل خيار متاح حالياً
            if cost_optimizer:
                # نرسل له القائمة وهو يختار بناءً على الرصيد والندرة
                preferred_route = cost_optimizer.select_best_provider(self.available_providers, complexity="LOW")
            else:
                preferred_route = "groq" # الافتراضي هو Groq لسرعته

        # 3. التنفيذ مع الهبوط الآمن (Execution with Failover)
        if not preferred_route:
            return self._declare_blindness("ALL_PROVIDERS_EXHAUSTED", "No viable providers selected by Cost Optimizer.")

        logger.info(f"🚦 Routing AI task ({task_type}) to -> {preferred_route.upper()}")

        result = None
        
        # المحاولة الأولى (Primary Route)
        if "groq" in preferred_route and self.groq_driver:
            result = self.groq_driver.generate_financial_report(system_prompt, context_data)
            
            # إذا فشل Groq لأي سبب (Rate Limit, Server Down)، نحول للبديل
            if not result and self.gemini_driver:
                logger.warning("⚠️ Groq Failed! Initiating immediate failover to Gemini Flash.")
                result = self.gemini_driver.process_large_document(system_prompt, context_data)
                
        elif "gemini" in preferred_route and self.gemini_driver:
            result = self.gemini_driver.process_large_document(system_prompt, context_data)
            
            # إذا فشل Gemini، نحول لـ Groq
            if not result and self.groq_driver:
                logger.warning("⚠️ Gemini Failed! Initiating immediate failover to Groq.")
                result = self.groq_driver.generate_financial_report(system_prompt, context_data)

        # 4. النتيجة النهائية
        if result:
            return result
        else:
            # المحاولة الأولى والثانية فشلتا. يجب تطبيق بروتوكول "أنا أعمى".
            return self._declare_blindness("TOTAL_INTELLIGENCE_FAILURE", "Both Primary and Failover LLMs returned None.")

    def _declare_blindness(self, error_code: str, details: str) -> None:
        """
        [البروتوكول الجنائي المالي]
        في حالة الفشل التام، النظام يرفض اختراع بيانات أو إعطاء استنتاج عشوائي.
        يعلن "العمى" صراحة ليتم إيقاف التداول أو التدخل اليدوي.
        """
        logger.critical(f"🛑 [I AM BLIND] SYSTEM INTELLIGENCE OFFLINE. Code: {error_code} | Details: {details}")
        
        if audit_logger:
            audit_logger.log_error("FREE_ROUTER_BLINDNESS", error_code, details)
            
        # إرجاع None يعلم الأنظمة الأعلى (Trading Engine) بالتوقف الفوري وعدم اتخاذ أي صفقة
        return None

# نسخة مفردة (Singleton) للاستخدام المباشر
free_router = FreeIntelligenceRouter()