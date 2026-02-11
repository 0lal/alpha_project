import time
import requests
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- استيراد أجهزة الدولة (State Machinery) ---
try:
    from inventory.key_loader import key_loader
    from audit.logger_service import audit_logger
    from core.rate_limiter import rate_limiter
    from core.usage_tracker import usage_tracker
    from validators.integrity_check import integrity_checker
    from validators.data_normalizer import normalizer
except ImportError:
    # وضع الطوارئ: السماح بالعمل (مع تحذير) إذا كانت المكونات ناقصة أثناء الاختبار
    logging.warning("⚠️ CRITICAL: Running BaseConnector in Standalone Mode (Missing Core Systems)")
    key_loader = None
    audit_logger = None
    rate_limiter = None
    usage_tracker = None
    integrity_checker = None
    normalizer = None

# إعداد السجل
logger = logging.getLogger("Alpha.Connectors.Base")

class BaseConnector(ABC):
    """
    الموصل الأساسي (The Prime Connector).
    
    الهدف الجنائي:
    هذا القالب يفرض "سيادة القانون" على جميع الموصلات الفرعية.
    لا يمكن لأي درايفر (Driver) أن يكسر القواعد التالية:
    1. لا اتصال بدون إذن مالي (Quota Check).
    2. لا اتصال بدون إذن مروري (Rate Limit Check).
    3. لا بيانات تدخل النظام بدون تفتيش (Validation).
    4. لا بيانات تخرج للواجهة بدون ترجمة (Normalization).
    """

    def __init__(self, provider_name: str):
        """
        تهيئة الموصل وتحميل تكوينه الخاص.
        :param provider_name: اسم المزود كما هو معرف في ملفات JSON (مثال: 'alpha_vantage').
        """
        self.provider_name = provider_name.lower()
        self.config = self._load_config()
        
        # إعداد جلسة اتصال قوية (Persistent Session)
        self.session = self._create_secure_session()

    def fetch(self, endpoint_key: str, **params) -> Optional[Union[List, Dict]]:
        """
        [القالب الموحد] تنفيذ الطلب الكامل من الألف إلى الياء.
        هذه الدالة هي "خط الإنتاج" الذي لا يجوز تجاوزه.
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # 1. التفتيش الأمني والمالي (Pre-Flight Checks)
        if not self._check_permissions(request_id):
            return None

        try:
            # 2. التجهيز للاتصال (Prepare Request)
            url, method, final_params, headers = self._prepare_request_details(endpoint_key, params)
            
            # 3. التنفيذ الفعلي (Execute - The Dangerous Part)
            response = self.session.request(
                method=method,
                url=url,
                params=final_params if method == 'GET' else None,
                json=final_params if method != 'GET' else None,
                headers=headers,
                timeout=self.config.get("connection_policy", {}).get("timeout_seconds", 10)
            )

            latency = (time.time() - start_time) * 1000  # ms

            # 4. تسجيل الدليل الخام (Forensic Evidence)
            if audit_logger:
                # نحفظ الرد الخام فقط إذا كان هناك خطأ أو للتدقيق العشوائي
                # لكي لا نملأ القرص الصلب، نسجل الردود الناجحة بنسبة 10% فقط أو عند الطلب
                audit_logger.log_raw_payload(self.provider_name, endpoint_key, self._safe_json(response), latency)

            # 5. معالجة أخطاء HTTP
            response.raise_for_status()
            data = response.json()

            # 6. التفتيش على المحتوى (Content Inspection)
            if integrity_checker:
                is_valid = integrity_checker.validate_market_data(data, self.provider_name)
                if not is_valid:
                    # البيانات فاسدة - تم رفض الدخول
                    return None

            # 7. الخصم المالي (Charge Quota)
            # نخصم 1 نقطة نجاح. يمكن تعديل التكلفة حسب نوع الطلب.
            if usage_tracker:
                usage_tracker.increment_usage(self.provider_name)

            # 8. الترجمة والتوحيد (Normalization)
            if normalizer:
                # نطلب من المترجم تحويل البيانات لصيغة Alpha
                # ملاحظة: نمرر رمز العملة إذا وجد في المعاملات
                symbol = params.get('symbol', 'UNKNOWN')
                return normalizer.normalize_market_data(data, self.provider_name, symbol)

            return data # في حال غياب المترجم، نعيد البيانات الخام (غير مستحسن)

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e, request_id)
            return None
        except Exception as e:
            self._handle_generic_error(e, request_id)
            return None

    @abstractmethod
    def build_url(self, endpoint_key: str) -> str:
        """
        يجب على الابن تنفيذها: كيف نبني الرابط؟
        """
        pass

    @abstractmethod
    def get_default_params(self) -> Dict:
        """
        يجب على الابن تنفيذها: هل هناك مفاتيح API تضاف تلقائياً؟
        """
        pass

    def _load_config(self) -> Dict:
        """
        تحميل الإعدادات من KeyLoader.
        """
        if key_loader:
            cfg = key_loader.get_config(self.provider_name)
            if not cfg:
                logger.error(f"❌ Configuration not found for {self.provider_name}")
                return {}
            return cfg
        return {}

    def _check_permissions(self, req_id: str) -> bool:
        """
        هل يسمح النظام لهذا الطلب بالمرور؟
        """
        # أ. فحص الحصة الشهرية
        if usage_tracker:
            status, _, msg = usage_tracker.check_quota_status(self.provider_name)
            if status == "BLOCKED":
                logger.warning(f"⛔ Request {req_id} BLOCKED by Quota Manager: {msg}")
                return False

        # ب. فحص سرعة المرور (Rate Limit)
        if rate_limiter:
            allowed, reason = rate_limiter.check_eligibility(self.provider_name)
            if not allowed:
                logger.warning(f"⛔ Request {req_id} BLOCKED by Traffic Controller: {reason}")
                # تفعيل عقوبة إذا تطلب الأمر
                if reason == "RPS_LIMIT_EXCEEDED":
                    rate_limiter.report_violation(self.provider_name, 429)
                return False

        return True

    def _create_secure_session(self) -> requests.Session:
        """
        إنشاء اتصال محصن مع إعادة المحاولة التلقائية.
        """
        session = requests.Session()
        
        # سياسة إعادة المحاولة: 3 مرات، مع انتظار متزايد (0.5s, 1s, 2s)
        # نغطي أخطاء السيرفر (500, 502, 503, 504)
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> tuple:
        """
        تجميع أجزاء الطلب (URL, Params, Headers).
        """
        url = self.build_url(endpoint_key)
        
        # دمج المعاملات الافتراضية (مثل API Key) مع معاملات الطلب
        default_params = self.get_default_params()
        final_params = {**default_params, **params}
        
        # جلب الهيدرز (مثل User-Agent لمنع الحظر)
        headers = {
            "User-Agent": "AlphaSovereign/1.0 (Financial_Forensics_Unit)",
            "Accept": "application/json"
        }
        
        # تحديد الطريقة (GET افتراضياً، يمكن تعديلها في الابن)
        method = "GET" 
        
        return url, method, final_params, headers

    def _handle_http_error(self, error: requests.exceptions.HTTPError, req_id: str):
        """
        التعامل الجنائي مع أخطاء الشبكة.
        """
        status_code = error.response.status_code
        logger.error(f"❌ HTTP Error {status_code} for {self.provider_name} [ID:{req_id}]: {error}")
        
        if audit_logger:
            audit_logger.log_error(
                f"CONNECTOR_{self.provider_name.upper()}",
                f"HTTP {status_code} failure",
                str(error)
            )

        # إذا كان الخطأ 429 (Too Many Requests)، نبلغ شرطي المرور فوراً
        if status_code == 429 and rate_limiter:
            rate_limiter.report_violation(self.provider_name, 429)

    def _handle_generic_error(self, error: Exception, req_id: str):
        """
        التعامل مع الأخطاء غير المتوقعة (Bugs).
        """
        logger.critical(f"🔥 CRITICAL DRIVER FAILURE {self.provider_name} [ID:{req_id}]: {error}")
        if audit_logger:
            audit_logger.log_error(
                f"CONNECTOR_{self.provider_name.upper()}",
                "Unhandled Exception",
                str(error)
            )

    def _safe_json(self, response: requests.Response) -> Union[Dict, str]:
        """
        محاولة قراءة JSON بأمان دون التسبب في خطأ جديد.
        """
        try:
            return response.json()
        except ValueError:
            return response.text[:200]  # أول 200 حرف فقط كدليل