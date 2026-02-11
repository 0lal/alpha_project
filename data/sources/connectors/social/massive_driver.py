import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان والتدقيق الجنائي
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Massive
logger = logging.getLogger("Alpha.Drivers.Massive")

class MassiveDriver(BaseConnector):
    """
    الذراع التنفيذي للبيانات الاجتماعية الضخمة (Massive Social Aggregator).
    
    المهام الجنائية:
    1. الاتصال بمزود البيانات Massive لجلب التحليلات البديلة (Alternative Data).
    2. العمل كمحرك ديناميكي (Dynamic Engine) يقرأ المسارات من ملف التكوين لمنع الهلوسة البرمجية.
    3. تطبيق العزل المالي التام: إذا كانت إعدادات المزود مفقودة، يعلن النظام "العمى" بأمان.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (massive_keys.json)
        super().__init__("massive")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: Massive API Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        [محرك التوجيه الديناميكي]
        بما أننا لا نملك توثيقاً ثابتاً، النظام يبحث عن الرابط والمسار داخل ملف JSON بصرامة.
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "")
        
        if not base_url:
            logger.error("🛑 Massive Driver Error: 'base_url' is not defined in the configuration file.")
            # إرجاع مسار فارغ سيؤدي إلى فشل آمن (Safe Fail) في القالب الأم
            return ""

        # خريطة الروابط مسحوبة بالكامل من ملف التكوين (لا يوجد تخمين هنا)
        endpoints_map = self.config.get("endpoints_map", {})
        
        # محاولة العثور على المسار (Path) الخاص بالعملية
        endpoint_config = endpoints_map.get(endpoint_key, {})
        
        if isinstance(endpoint_config, dict):
            path = endpoint_config.get("path", f"/{endpoint_key}")
        elif isinstance(endpoint_config, str):
            path = endpoint_config
        else:
            path = f"/{endpoint_key}"

        # تنظيف الروابط لضمان عدم وجود شرطات مزدوجة (//)
        clean_base = base_url.rstrip("/")
        clean_path = path.lstrip("/")
        
        return f"{clean_base}/{clean_path}"

    def get_default_params(self) -> Dict[str, str]:
        """
        قراءة المعاملات الافتراضية (مثل طريقة تمرير المفتاح) من التكوين.
        """
        auth_type = self.config.get("credentials", {}).get("auth_type", "query_param")
        param_name = self.config.get("credentials", {}).get("param_name", "api_key")
        
        # إذا كان المزود يطلب المفتاح في الرابط
        if auth_type == "query_param" and self.api_key:
            return {param_name: self.api_key}
            
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني]
        التعامل مع حقن المفتاح في الترويسة (Headers) إذا كان المزود يشترط ذلك.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        auth_type = self.config.get("credentials", {}).get("auth_type", "query_param")
        
        # إذا كان المزود يشترط تمرير المفتاح كـ Bearer Token أو Custom Header
        if auth_type == "bearer_token" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif auth_type == "custom_header" and self.api_key:
            header_name = self.config.get("credentials", {}).get("header_name", "X-Api-Key")
            headers[header_name] = self.api_key
            
        # تحديد طريقة الاتصال من خريطة التكوين (الافتراضي هو GET)
        endpoint_config = self.config.get("endpoints_map", {}).get(endpoint_key, {})
        if isinstance(endpoint_config, dict):
            method = endpoint_config.get("method", "GET").upper()

        return url, method, final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[Any]:
        """
        [تجاوز جنائي - Validation Override]
        منع إرسال أي طلب إذا كانت الإعدادات الأساسية مفقودة تماماً، للحفاظ على استقرار الشبكة.
        """
        if not self.config.get("connection_policy", {}).get("base_url"):
            logger.error(f"🛑 Attempted to fetch '{endpoint_key}' via Massive, but no base_url exists. Aborting.")
            return None
            
        return super().fetch(endpoint_key, **params)

    # =========================================================================
    # أذرع جلب البيانات (Dynamic Arms)
    # =========================================================================

    def fetch_dynamic_social_data(self, endpoint_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        دالة شاملة وآمنة لاستدعاء أي خدمة من خدمات Massive بناءً على اسمها في ملف التكوين.
        
        المعاملات:
        - endpoint_name: اسم الخدمة (مثال: 'social_sentiment', 'trending_coins').
        - kwargs: أي معاملات إضافية يتطلبها المزود (مثال: symbol="BTC", limit=100).
        """
        # الحماية الجنائية: التأكد من أن الاسم المدخل نصي وصالح
        if not endpoint_name or not isinstance(endpoint_name, str):
            logger.error("🛑 Blocked Massive API request: Invalid endpoint_name.")
            return None

        logger.info(f"🌐 Routing dynamic request to Massive API: [{endpoint_name}]")
        
        # الإرسال عبر القالب الأم للتدقيق والفلترة
        result = self.fetch(endpoint_name, **kwargs)
        
        if result is None:
            return None
            
        return result