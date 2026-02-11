import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان، المحاسبة، والتدقيق الجنائي
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Santiment
logger = logging.getLogger("Alpha.Drivers.Santiment")

class SantimentDriver(BaseConnector):
    """
    الذراع التنفيذي للبيانات الاجتماعية ونشاط المطورين (Santiment GraphQL API).
    
    المهام الجنائية:
    1. جلب بيانات "حجم التفاعل الاجتماعي" (Social Volume) ومشاعر السوق.
    2. العمل كمحرك استعلامات GraphQL آمن للبيانات المالية المعقدة.
    3. تطبيق نظام المصادقة المخصص (Apikey) لمنع الحظر.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (مثال: santiment_key.json)
        super().__init__("santiment")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: Santiment API Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        [تجاوز إجباري - GraphQL Override]
        في GraphQL، يوجد نقطة وصول (Endpoint) واحدة فقط لكل شيء.
        """
        return self.config.get("connection_policy", {}).get("base_url", "https://api.santiment.net/graphql")

    def get_default_params(self) -> Dict[str, Any]:
        """
        لا نرسل معاملات افتراضية في الرابط، بل نرسل الاستعلامات داخل جسم الطلب (Body).
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        حقن مفتاح الوصول في الترويسة وتغيير نوع الطلب إلى POST الإلزامي لـ GraphQL.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # صيغة المصادقة الخاصة بـ Santiment (ليست Bearer)
        headers["Authorization"] = f"Apikey {self.api_key}"
        headers["Content-Type"] = "application/graphql" # يمكن استخدام application/json أيضاً
        
        # GraphQL يتطلب POST دائماً لنقل استعلامات ضخمة
        return url, "POST", final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[Dict[str, Any]]:
        """
        [تجاوز جنائي]
        إرسال استعلام الـ GraphQL وفحص الردود بحثاً عن أخطاء داخلية (Errors) 
        حتى لو كان كود HTTP هو 200 (نجاح وهمي).
        """
        result = super().fetch(endpoint_key, **params)
        
        # فحص بروتوكول "أنا أعمى": هل انقطع الاتصال؟
        if not result or not isinstance(result, dict):
            return None

        # الفحص الجنائي لردود GraphQL: الأخطاء تكون مخفية داخل مفتاح 'errors'
        if "errors" in result:
            error_details = result["errors"][0].get("message", "Unknown GraphQL Error")
            logger.error(f"🛑 Santiment GraphQL Error: {error_details}")
            
            # توثيق الجريمة في السجلات
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_error("SANTIMENT_GQL_ERROR", "Data Provider Error", error_details)
            
            return None
            
        # إرجاع البيانات الصافية من داخل مفتاح 'data'
        return result.get("data")

    # =========================================================================
    # أذرع التحليل الاجتماعي (Social & On-Chain Arms)
    # =========================================================================

    def get_social_volume(self, asset_slug: str, from_date: str, to_date: str, interval: str = "1d") -> Optional[List[Dict[str, Any]]]:
        """
        جلب حجم التفاعل الاجتماعي (Social Volume) لعملة معينة لمعرفة "الضجة" (Hype).
        
        المعاملات:
        - asset_slug: الاسم الكامل للعملة (مثال: 'bitcoin', 'ethereum'). لا تستخدم 'BTC'.
        - from_date: تاريخ البداية (ISO format: '2023-01-01T00:00:00Z').
        - to_date: تاريخ النهاية.
        - interval: الإطار الزمني (1d, 1h).
        """
        # الحماية الجنائية ضد الرموز الخاطئة (Tickers vs Slugs)
        if asset_slug == asset_slug.upper() and len(asset_slug) <= 4:
            logger.warning(f"⚠️ Santiment Warning: You passed '{asset_slug}'. Santiment requires slugs (e.g., 'bitcoin' not 'BTC'). Request may fail.")

        # بناء الاستعلام (GraphQL Query) المخصص مالياً
        gql_query = f"""
        {{
          getMetric(metric: "social_volume_total") {{
            timeseriesData(
              slug: "{asset_slug}"
              from: "{from_date}"
              to: "{to_date}"
              interval: "{interval}"
            ) {{
              datetime
              value
            }}
          }}
        }}
        """
        
        # تغليف الاستعلام في مفتاح 'query' كما يتطلب سيرفر GraphQL
        params = {"query": gql_query}
        
        logger.info(f"🗣️ Fetching Santiment Social Volume for slug: {asset_slug}")
        response_data = self.fetch("social_volume", **params)
        
        if response_data:
            # استخراج السلسلة الزمنية من الهيكل المتداخل
            try:
                return response_data["getMetric"]["timeseriesData"]
            except KeyError:
                return None
                
        return None

    def get_development_activity(self, asset_slug: str, from_date: str, to_date: str, interval: str = "1d") -> Optional[List[Dict[str, Any]]]:
        """
        جلب نشاط المطورين (Dev Activity).
        استراتيجية مالية: العملات التي لا يوجد بها تطوير هي "عملات ميتة" (Scam/Dead).
        """
        gql_query = f"""
        {{
          getMetric(metric: "dev_activity") {{
            timeseriesData(
              slug: "{asset_slug}"
              from: "{from_date}"
              to: "{to_date}"
              interval: "{interval}"
            ) {{
              datetime
              value
            }}
          }}
        }}
        """
        
        params = {"query": gql_query}
        
        logger.info(f"👨‍💻 Fetching Santiment Dev Activity for slug: {asset_slug}")
        response_data = self.fetch("dev_activity", **params)
        
        if response_data:
            try:
                return response_data["getMetric"]["timeseriesData"]
            except KeyError:
                return None
                
        return None