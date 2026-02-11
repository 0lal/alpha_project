import logging
from typing import List, Dict, Optional, Any

# استيراد المحاسب للتحقق من الرصيد المتبقي
try:
    from core.usage_tracker import usage_tracker
except ImportError:
    usage_tracker = None

# إعداد السجل
logger = logging.getLogger("Alpha.Core.CostOptimizer")

class ResourceEconomist:
    """
    الخبير الاقتصادي للموارد (Resource Economist).
    
    الهدف الجنائي:
    1. ترتيب المزودين من "الأرخص" إلى "الأغلى" بناءً على ندرة الموارد.
    2. منع استخدام الموارد الثمينة (مثل Gemini Pro) في المهام التافهة (مثل Ping).
    3. التحويل الديناميكي: إذا كان المزود الرخيص مشغولاً، هل يستحق الأمر دفع تكلفة أعلى؟
    """

    def __init__(self):
        """
        تهيئة مصفوفة الندرة. كلما زاد الرقم، زادت "تكلفة" استخدام هذا المزود.
        """
        # نقاط الندرة (Scarcity Score) - كلما قل الرقم كان أفضل
        self.scarcity_matrix = {
            # --- الذكاء الاصطناعي ---
            "groq": 10,                 # رخيص وسريع (14k طلب/يوم)
            "gemini-1.5-flash": 20,     # اقتصادي (15 طلب/دقيقة)
            "gemini-1.5-pro": 1000,     # مكلف جداً ونادر (2 طلب/دقيقة فقط!) - للطوارئ
            "open_manus": 50,           # متوسط
            
            # --- البيانات المالية ---
            "alpha_vantage": 50,        # محدود (500/يوم)
            "twelve_data": 40,          # أفضل قليلاً (800/يوم)
            "yahoo_finance": 30,        # متوفر عبر RapidAPI
            
            # --- الأخبار ---
            "cryptopanic": 500,         # نادر جداً (100 طلب/شهر فقط!)
            "searxng": 5                # مجاني ومفتوح (الأرخص على الإطلاق)
        }

    def select_best_provider(self, candidates: List[str], task_complexity: str = "LOW") -> Optional[str]:
        """
        اختيار المزود الأمثل للمهمة.
        
        المعاملات:
        - candidates: قائمة المزودين المتاحين (مثال: ['groq', 'gemini-1.5-pro']).
        - task_complexity: تعقيد المهمة ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
        
        الإرجاع:
        - اسم المزود الفائز، أو None إذا فشل الجميع.
        """
        if not candidates:
            return None

        # 1. فلترة المفلسين (Filter Out Exhausted Providers)
        viable_candidates = []
        for provider in candidates:
            if self._is_provider_usable(provider):
                viable_candidates.append(provider)

        if not viable_candidates:
            logger.warning("⚠️ All candidates are exhausted or blocked!")
            return None

        # 2. الترتيب حسب التكلفة (Sort by Scarcity)
        # نرتبهم من الأرخص (رقم صغير) إلى الأغلى (رقم كبير)
        viable_candidates.sort(key=lambda p: self.scarcity_matrix.get(self._get_base_name(p), 100))

        # 3. منطق الترقية الذكي (Smart Upgrade Logic)
        # إذا كانت المهمة صعبة جداً، لا تستخدم "الأرخص" لأنه قد يكون غبياً.
        # بل استخدم "أرخص واحد ذكي".
        
        best_choice = viable_candidates[0] # الافتراضي هو الأرخص

        if task_complexity == "CRITICAL" or task_complexity == "HIGH":
            # في المهام الصعبة، نبحث عن الأقوياء فقط حتى لو كانوا أغلى
            # مثال: تحليل انهيار السوق يحتاج Gemini Pro وليس Groq 8b
            for candidate in viable_candidates:
                if self._is_high_intelligence(candidate):
                    best_choice = candidate
                    break
        
        # حماية إضافية: لا تستخدم Gemini Pro أبداً لمهام بسيطة
        if task_complexity == "LOW" and "gemini-1.5-pro" in best_choice:
            # حاول إيجاد بديل أرخص
            for candidate in viable_candidates:
                if "gemini-1.5-flash" in candidate or "groq" in candidate:
                    best_choice = candidate
                    break

        return best_choice

    def _is_provider_usable(self, provider: str) -> bool:
        """
        سؤال المحاسب: هل تبقى رصيد لهذا المزود؟
        """
        if not usage_tracker:
            return True # افتراض التوفر إذا غاب المحاسب
            
        # تفكيك الاسم (مثال: groq-llama3 -> groq)
        base_name = self._get_base_name(provider)
        
        status, _, _ = usage_tracker.check_quota_status(base_name)
        
        # نرفض فقط المحظورين تماماً (BLOCKED)
        # نقبل (WARNING) و (CRITICAL) لأننا قد نحتاجهم في الطوارئ
        return status != "BLOCKED"

    def _get_base_name(self, full_name: str) -> str:
        """
        استخراج الاسم الأساسي للمزود من اسم الموديل.
        مثال: 'groq-llama3-70b' -> 'groq'
        """
        if "groq" in full_name: return "groq"
        if "gemini" in full_name: return "google" # المفتاح مخزن باسم google
        if "alpha" in full_name: return "alpha_vantage"
        if "twelve" in full_name: return "twelve_data"
        if "crypto" in full_name: return "cryptopanic"
        return full_name

    def _is_high_intelligence(self, provider: str) -> bool:
        """
        هل هذا المزود يعتبر "خبيراً"؟
        """
        smart_models = ["gemini-1.5-pro", "llama3-70b", "gpt-4"]
        return any(m in provider for m in smart_models)

# نسخة مفردة (Singleton)
cost_optimizer = ResourceEconomist()