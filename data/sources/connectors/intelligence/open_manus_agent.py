import logging
import json
from typing import Dict, Any, Optional, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان والحدود
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بعميل OpenManus
logger = logging.getLogger("Alpha.Drivers.OpenManus")

class OpenManusAgentDriver(BaseConnector):
    """
    الذراع التنفيذي للعميل المستقل (OpenManus Autonomous Agent).
    
    المهام الجنائية:
    1. تنفيذ مهام بحث مالي معقدة ومتعددة الخطوات (Multi-step Reasoning).
    2. تجاوز مهلة الاتصال الافتراضية للتعامل مع بطء عمليات البحث الحي (Live Browsing).
    3. فرض قيود صارمة (Guardrails) لمنع العميل من الدخول في حلقات بحث لا نهائية.
    """

    def __init__(self):
        """
        تهيئة العميل.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (إذا وجدت في json، أو استخدام الافتراضي)
        super().__init__("open_manus")
        
        # استخراج المفتاح (قد يكون رمزاً داخلياً لحماية السيرفر المحلي الخاص بك)
        self.internal_token = self.config.get("credentials", {}).get("api_key", "internal_secure_token")

    def build_url(self, endpoint_key: str) -> str:
        """
        [تجاوز إجباري] بناء الرابط.
        بما أن OpenManus يعمل كخدمة مصغرة (Microservice) داخل نظامك، الرابط سيكون محلياً أو خاصاً.
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "http://localhost:8000")
        
        # مسارات واجهة العميل (Agent API)
        endpoints = {
            "run_task": "/api/v1/agent/run",
            "status": "/api/v1/agent/status"
        }
        
        path = endpoints.get(endpoint_key, "/api/v1/agent/run")
        return f"{base_url}{path}"

    def get_default_params(self) -> Dict[str, Any]:
        """
        العميل يستقبل البيانات كـ JSON، نترك الـ Query Params فارغة.
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        حقن رمز المصادقة الداخلي وتحديد طريقة الاتصال.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # حماية الاتصال الداخلي
        headers["Authorization"] = f"Bearer {self.internal_token}"
        headers["Content-Type"] = "application/json"
        
        # واجهة العميل تتطلب إرسال POST لبدء المهمة
        return url, "POST", final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[str]:
        """
        [تجاوز المهلة الجنائية - Timeout Override]
        بما أننا نتعامل مع عميل يبحث في الويب، يجب أن نكسر قاعدة الـ 10 ثواني للقالب الأم.
        """
        request_id = params.get("task_id", "AGENT_REQ_001")
        
        if not self._check_permissions(request_id):
            return None

        try:
            url, method, final_params, headers = self._prepare_request_details(endpoint_key, params)
            
            # 1. إعطاء مهلة استثنائية (5 دقائق) للعميل المستقل
            agent_timeout = self.config.get("connection_policy", {}).get("timeout_seconds", 300)
            
            logger.info(f"🕵️‍♂️ Deploying OpenManus Agent for task... (Timeout: {agent_timeout}s)")
            
            response = self.session.request(
                method=method,
                url=url,
                json=final_params,
                headers=headers,
                timeout=agent_timeout
            )

            # 2. معالجة أخطاء السيرفر المحلي
            response.raise_for_status()
            data = response.json()

            # 3. استخراج المحتوى الفعلي
            # الافتراض المالي لهيكل الرد من OpenManus API
            status = data.get("status", "unknown")
            
            if status in ["failed", "error"]:
                logger.error(f"🛑 OpenManus Agent Failed: {data.get('error', 'Unknown Error')}")
                return None
                
            result = data.get("result")
            if not result:
                logger.error("🛑 OpenManus Agent returned empty result.")
                return None
                
            return str(result).strip()

        except Exception as e:
            self._handle_generic_error(e, request_id)
            return None

    # =========================================================================
    # أذرع البحث المعقد (Complex Reasoning Arms)
    # =========================================================================

    def execute_deep_research(self, target_company: str, specific_query: str) -> Optional[str]:
        """
        [أداة الخبراء] إطلاق العميل للبحث المفتوح عن معلومات غير متوفرة في APIs.
        مثال: "ابحث في موقع الشركة الرسمي عن آخر إعلان لعدد المشتركين".
        """
        # السياج المالي (Financial Guardrail): تقييد العميل ومنعه من الهلوسة أو البحث اللانهائي
        strict_instruction = (
            f"TARGET: {target_company}\n"
            f"QUERY: {specific_query}\n\n"
            "RULES OF ENGAGEMENT:\n"
            "1. You are a financial auditor. Seek ONLY factual data.\n"
            "2. Limit your search to official sites, SEC filings, or top-tier financial news.\n"
            "3. If you cannot find the EXACT answer within 3 search steps, STOP IMMEDIATELY and return 'DATA_NOT_FOUND'.\n"
            "4. DO NOT guess. DO NOT hallucinate numbers."
        )

        payload = {
            "task": strict_instruction,
            "max_steps": 5  # إجبار العميل برمجياً على التوقف بعد 5 خطوات مهما حدث
        }
        
        return self.fetch("run_task", **payload)

    def cross_validate_news(self, headline: str, source: str) -> Optional[str]:
        """
        التحقق الجنائي من الأخبار.
        إرسال العميل للتأكد من خبر عاجل (هل هو حقيقي أم إشاعة؟) قبل التداول بناءً عليه.
        """
        task = (
            f"A news piece claims: '{headline}' from source '{source}'.\n"
            "Verify this claim immediately using alternative independent sources.\n"
            "Return ONLY one of these three verdicts: [CONFIRMED], [FALSE], or [UNVERIFIED], followed by a 1-sentence explanation."
        )

        payload = {
            "task": task,
            "max_steps": 3
        }
        
        logger.info(f"⚖️ Sending OpenManus to cross-validate news: {headline[:30]}...")
        return self.fetch("run_task", **payload)