import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان والتدقيق الجنائي
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي لبوابة RapidAPI
logger = logging.getLogger("Alpha.Drivers.RapidAPIGateway")

class RapidAPIGateway(BaseConnector):
    """
    بوابة العبور الموحدة لخدمات RapidAPI (Multi-Provider Gateway).
    
    المهام الجنائية:
    1. إدارة الاتصال بآلاف الواجهات البرمجية (APIs) المستضافة على منصة RapidAPI.
    2. حقن الترويسات المزدوجة (Key & Host) ديناميكياً لتجنب اختلاط الطلبات.
    3. العزل المالي: منع إرسال الطلبات إذا كان الـ Host غير معروف لتجنب رسوم الـ Overage.
    """

    def __init__(self):
        """
        تهيئة البوابة المركزية.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (rapidapi_keys.json)
        super().__init__("rapidapi")
        
        # استخراج المفتاح الموحد من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: RapidAPI Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        [محرك التوجيه الديناميكي]
        بناء الرابط بناءً على الخدمة المطلوبة (Host).
        RapidAPI لا يمتلك Base URL ثابتاً، بل يتغير حسب الـ Host.
        """
        # جلب خريطة العمليات من ملف التكوين
        endpoints_map = self.config.get("endpoints_map", {})
        endpoint_config = endpoints_map.get(endpoint_key, {})
        
        # الحماية الجنائية: إذا كانت الخدمة غير مسجلة، نرفض الاتصال فوراً
        if not endpoint_config or not isinstance(endpoint_config, dict):
            logger.error(f"🛑 RapidAPI Gateway Error: Endpoint '{endpoint_key}' is not mapped in config.")
            return "" # إرجاع نص فارغ سيؤدي إلى فشل آمن في القالب الأم

        rapidapi_host = endpoint_config.get("host")
        path = endpoint_config.get("path", "")
        
        if not rapidapi_host:
            logger.error(f"🛑 RapidAPI Gateway Error: No 'host' defined for endpoint '{endpoint_key}'.")
            return ""

        # بناء الرابط الفعلي: https://{host}{path}
        clean_host = rapidapi_host.rstrip("/")
        clean_path = path.lstrip("/")
        return f"https://{clean_host}/{clean_path}"

    def get_default_params(self) -> Dict[str, str]:
        """
        الترويسات يتم حقنها في دالة _prepare_request_details بدلاً من الرابط (Params) للأمان.
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        حقن الترويسات المزدوجة (Dual-Header Injection) المعقدة الخاصة بـ RapidAPI.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # استخراج الـ Host المخصص لهذه الخدمة من ملف التكوين
        endpoints_map = self.config.get("endpoints_map", {})
        endpoint_config = endpoints_map.get(endpoint_key, {})
        rapidapi_host = endpoint_config.get("host", "")
        
        # حقن مفاتيح العبور الآمنة
        headers["X-RapidAPI-Key"] = self.api_key
        headers["X-RapidAPI-Host"] = rapidapi_host
        
        # تحديد طريقة الاتصال (GET/POST) بناءً على التكوين، الافتراضي هو GET
        method = endpoint_config.get("method", "GET").upper()
        
        return url, method, final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[Any]:
        """
        [تجاوز جنائي - Validation Override]
        منع إرسال أي طلب إذا كان بناء الرابط قد فشل (لتجنب إرسال طلب لـ https:///path).
        """
        # اختبار وهمي مبدئي لمعرفة ما إذا كان الرابط سيبنى بشكل صحيح
        test_url = self.build_url(endpoint_key)
        if not test_url:
            logger.error(f"🛑 Attempted to fetch '{endpoint_key}' via RapidAPI, but routing failed. Aborting.")
            return None
            
        # إرسال الطلب عبر القالب الأم لضمان المرور على المحاسب والتدقيق الجنائي
        result = super().fetch(endpoint_key, **params)
        
        if result is None:
            return None
            
        return result

    # =========================================================================
    # أذرع التوجيه المالي (Financial Routing Arms)
    # =========================================================================

    def execute_service(self, service_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        دالة شاملة لاستدعاء أي خدمة مسجلة داخل بوابة RapidAPI.
        
        المعاملات:
        - service_name: اسم الخدمة المعرف في ملف JSON (مثال: 'yahoo_finance_summary').
        - kwargs: أي معاملات إضافية (Query Parameters) تتطلبها تلك الخدمة تحديداً.
        
        أمثلة للـ kwargs:
        - لـ Yahoo Finance: symbol="AAPL", region="US"
        - لـ Twinword Sentiment: text="Market is crashing!"
        """
        # الحماية الجنائية: التأكد من أن اسم الخدمة صالح
        if not service_name or not isinstance(service_name, str):
            logger.error("🛑 Blocked RapidAPI request: Invalid service_name.")
            return None

        logger.info(f"🌉 Routing request through RapidAPI Gateway to service: [{service_name}]")
        
        # الإرسال للتدقيق والتنفيذ
        return self.fetch(service_name, **kwargs)