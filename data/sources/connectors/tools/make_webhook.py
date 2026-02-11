import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union

# استيراد القالب الأم الذي يطبق سياسات الأمان، المحاسبة، والتدقيق الجنائي
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي لروابط الأتمتة
logger = logging.getLogger("Alpha.Drivers.MakeWebhook")

class MakeWebhookDriver(BaseConnector):
    """
    الذراع التنفيذي للربط الخارجي والأتمتة (Make.com Integrator).
    
    المهام الجنائية:
    1. إرسال إشارات التداول والبيانات المالية المعالجة إلى سيناريوهات Make.com لتنفيذها.
    2. معالجة البيانات المعقدة (Decimal/Datetime) قبل إرسالها لتجنب انهيار التشفير.
    3. التحكم في السيناريوهات عبر الـ API الرسمي (تشغيل/إيقاف).
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (make_webhook_keys.json)
        super().__init__("make")
        
        # استخراج المفتاح من ملفات التكوين الآمنة (يستخدم لـ Make API وليس للـ Custom Webhooks)
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        # الرابط الأساسي لخدمات الـ API الخاصة بهم
        self.api_base_url = self.config.get("connection_policy", {}).get("base_url", "https://eu1.make.com/api/v2")

    def build_url(self, endpoint_key: str) -> str:
        """
        [محرك التوجيه الذكي]
        هل هذا رابط Webhook مباشر أم طلب لـ Make API؟
        """
        # إذا كان المدخل رابطاً كاملاً (يبدأ بـ http)، فهو Custom Webhook
        if endpoint_key.startswith("http://") or endpoint_key.startswith("https://"):
            return endpoint_key
            
        # إذا لم يكن رابطاً، ندمجه مع الرابط الأساسي للـ API
        path = endpoint_key if endpoint_key.startswith("/") else f"/{endpoint_key}"
        return f"{self.api_base_url}{path}"

    def get_default_params(self) -> Dict[str, Any]:
        """
        لا يوجد معاملات افتراضية في الرابط للـ Webhooks لضمان النظافة.
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني]
        تحديد طريقة الاتصال (POST دائماً لإرسال البيانات) وتجهيز الترويسات.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # إجبار نوع المحتوى ليكون JSON
        headers["Content-Type"] = "application/json"
        
        # إذا كان الطلب موجهاً لـ Make API (وليس Webhook عادي)، نحقن مفتاح المصادقة
        if url.startswith(self.api_base_url) and self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
            
        # Webhooks تتطلب دائماً إرسال POST
        return url, "POST", final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[Any]:
        """
        [تجاوز جنائي - Serialization Override]
        تنظيف حمولة البيانات (Payload) من أي كائنات غير قابلة للتشفير مثل Decimal قبل إرسالها للقالب الأم.
        """
        # 1. تنظيف البيانات
        safe_params = self._sanitize_payload(params)
        
        # 2. الإرسال عبر القالب الأم للتدقيق والمحاسبة
        logger.info(f"🚀 Dispatching payload to Make.com: [{endpoint_key}]")
        result = super().fetch(endpoint_key, **safe_params)
        
        # 3. بروتوكول "أنا أعمى": إذا فشل الاتصال نعيد None ولا نفترض النجاح
        if result is None:
            logger.error(f"🛑 Make.com Webhook Failed. Payload was NOT delivered.")
            return None
            
        # Make.com عادة يرد بـ "Accepted" أو قاموس JSON للـ Webhook
        return result

    def _sanitize_payload(self, payload: Any) -> Any:
        """
        [درع التشفير المالي]
        مكتبة requests لا تفهم Decimal أو Datetime. هذه الدالة تحولها لنصوص بأمان.
        تستخدم الاستدعاء الذاتي (Recursion) لتنظيف القواميس والقوائم المتداخلة.
        """
        if isinstance(payload, dict):
            return {k: self._sanitize_payload(v) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self._sanitize_payload(item) for item in payload]
        elif isinstance(payload, Decimal):
            # تحويل السعر المالي إلى Float أو String.
            # Float أفضل للمنصات الخارجية لكي تتعامل معها كأرقام.
            return float(payload)
        elif isinstance(payload, datetime):
            # توحيد التوقيت لـ ISO 8601
            return payload.isoformat()
        else:
            return payload

    # =========================================================================
    # أذرع الأتمتة المالية (Financial Automation Arms)
    # =========================================================================

    def send_trading_signal(self, webhook_url: str, signal_data: Dict[str, Any]) -> bool:
        """
        إرسال إشارة تداول أو تنبيه طوارئ إلى سيناريو Make.com محدد.
        
        المعاملات:
        - webhook_url: الرابط الفريد المستخرج من منصة Make (Custom Webhook).
        - signal_data: البيانات (مثال: السهم، السعر، الاتجاه).
        
        الإرجاع: True إذا نجح التسليم، False إذا فشل.
        """
        # الحماية الجنائية: التأكد من وجود رابط حقيقي
        if not webhook_url or "make.com" not in webhook_url:
            logger.error("🛑 Blocked signal dispatch: Invalid or missing Webhook URL.")
            return False

        logger.info(f"📨 Transmitting Trading Signal via Webhook...")
        
        # نمرر الرابط كـ endpoint_key لكي يتعرف عليه الموجه الذكي (build_url)
        response = self.fetch(webhook_url, **signal_data)
        
        # إذا لم يعُد بـ None، فالتسليم نجح
        if response is not None:
            logger.info("✅ Signal delivered and acknowledged by Make.com.")
            return True
            
        return False

    def toggle_scenario(self, scenario_id: int, active: bool) -> bool:
        """
        [أداة تحكم API] إيقاف أو تشغيل سيناريو عن بُعد.
        مفيدة لإيقاف التداول الآلي فوراً عند اكتشاف انهيار السوق (Flash Crash).
        """
        if not self.api_key:
            logger.error("🛑 Make API Key missing. Cannot toggle scenarios.")
            return False
            
        endpoint = f"scenarios/{scenario_id}"
        
        # في Make API, لتفعيل/إيقاف السيناريو نرسل {"is_active": True/False}
        payload = {"is_active": active}
        
        logger.warning(f"⚙️ Toggling Scenario {scenario_id} to Active={active}...")
        
        response = self.fetch(endpoint, **payload)
        
        return response is not None