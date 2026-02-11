import logging
from typing import Dict, Any, Optional, List, Tuple
import json

# استيراد القالب الأم الذي يحتوي على جدار الحماية (Firewall) وسياسات الاتصال
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Groq LPU
logger = logging.getLogger("Alpha.Drivers.GroqLPU")

class GroqLPUDriver(BaseConnector):
    """
    الذراع التنفيذي للذكاء الاصطناعي فائق السرعة (Groq LPU).
    
    المهام الجنائية:
    1. توفير تحليل مالي لحظي باستخدام نماذج Llama3.
    2. معالجة النصوص وحماية النظام من تجاوز سقف الـ 8192 توكن.
    3. كبح الهلوسة (Zero-Hallucination Policy) في التقارير المالية.
    4. العمل كبديل (Fallback) قوي إذا فشل نموذج Gemini في اتخاذ القرار.
    """

    # الحد الأقصى التقريبي لعدد الأحرف المسموح إرساله لمنع خطأ 413 (Payload Too Large)
    # (8192 توكن تساوي تقريباً 30,000 حرف باللغة الإنجليزية)
    MAX_PAYLOAD_CHARS = 28000 

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات من ملف JSON الخاص به
        super().__init__("groq")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: Groq API Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        بناء الرابط.
        Groq يستخدم واجهة متوافقة مع OpenAI.
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "https://api.groq.com/openai/v1")
        
        endpoints = {
            "chat_completions": "/chat/completions",
            "models": "/models"
        }
        
        path = endpoints.get(endpoint_key, "/chat/completions")
        return f"{base_url}{path}"

    def get_default_params(self) -> Dict[str, Any]:
        """
        Groq يتطلب إرسال البيانات كـ JSON Body، لذا نترك الـ Query Params فارغة.
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        حقن مفتاح الوصول في الترويسة (Header) بصيغة Bearer Token.
        وتحديد طريقة الاتصال كـ POST.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # حقن المصادقة القياسية المشفرة
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        
        # واجهة المحادثة تتطلب إرسال POST دائماً
        return url, "POST", final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[str]:
        """
        [تجاوز جنائي - Extraction Override]
        هذه الدالة ترسل الطلب وتستخرج "النص الفعلي" من هيكل JSON المعقد.
        أي فشل هنا يعيد None، مما يعني "النظام أعمى ولا يوجد بيانات افتراضية".
        """
        # 1. الإرسال عبر جدار الحماية في القالب الأم
        result = super().fetch(endpoint_key, **params)
        
        # 2. الفحص الجنائي لنتيجة الرد
        if not result or not isinstance(result, dict):
            return None

        # 3. استخراج المحتوى (Content) من الرد
        try:
            choices = result.get("choices", [])
            if not choices:
                logger.error("🛑 Groq API Error: No 'choices' returned in response.")
                return None
                
            content = choices[0].get("message", {}).get("content")
            
            if not content:
                logger.error("🛑 Groq API Error: Empty content received.")
                return None
                
            return content.strip()

        except Exception as e:
            logger.error(f"🛑 Groq JSON Parsing Error: {str(e)}")
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_error("GROQ_PARSE_ERROR", "Failed to extract AI content", str(e))
            return None

    # =========================================================================
    # أذرع التحليل الذكي (Intelligence Arms)
    # =========================================================================

    def _trim_payload(self, text: str) -> str:
        """
        [قاطع التيار - Circuit Breaker]
        حماية النظام من الانهيار إذا كان النص أطول من قدرة استيعاب Groq (8192 توكن).
        يقوم بقص النص من المنتصف ويحتفظ بأهم الأجزاء (البداية والنهاية).
        """
        if len(text) <= self.MAX_PAYLOAD_CHARS:
            return text
            
        logger.warning(f"⚠️ Payload too large ({len(text)} chars). Trimming to prevent Groq API crash.")
        
        half_limit = (self.MAX_PAYLOAD_CHARS // 2) - 500
        # نحتفظ بالبداية والنهاية ونضع علامة في المنتصف
        trimmed_text = text[:half_limit] + "\n\n... [SYSTEM TRUNCATED MIDDLE CONTENT DUE TO MEMORY LIMITS] ...\n\n" + text[-half_limit:]
        return trimmed_text

    def generate_financial_report(self, system_prompt: str, market_data: str) -> Optional[str]:
        """
        إنشاء تقرير مالي معقد واتخاذ قرارات مصيرية.
        يستخدم النموذج الأذكى والأثقل (Llama 3 70B).
        """
        # حماية النص من تجاوز الحد المسموح
        safe_data = self._trim_payload(market_data)

        # تجهيز هيكل المحادثة القياسي (OpenAI/Groq Format)
        payload = {
            "model": "llama3-70b-8192", # النموذج المخصص للمهام الثقيلة والقرارات
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a strict financial AI. Base your answers ONLY on the provided data. Do not guess, do not hallucinate. If data is insufficient, state: 'INSUFFICIENT_DATA'.\n{system_prompt}"
                },
                {
                    "role": "user",
                    "content": safe_data
                }
            ],
            "temperature": 0.1, # حرارة شبه صفرية لمنع التزييف والهلوسة
            "max_tokens": 4000,
            "top_p": 0.9
        }
        
        logger.info("🧠 Requesting Deep Financial Analysis via Groq (llama3-70b)")
        return self.fetch("chat_completions", **payload)

    def quick_data_extraction(self, text_to_parse: str, extraction_goal: str) -> Optional[str]:
        """
        استخراج سريع للبيانات (مثال: قراءة خبر واستخراج اسم السهم منه).
        يستخدم النموذج الأسرع والأخف (Llama 3 8B).
        """
        safe_text = self._trim_payload(text_to_parse)

        payload = {
            "model": "llama3-8b-8192", # النموذج المخصص للسرعة والمهام البسيطة
            "messages": [
                {
                    "role": "system",
                    "content": f"Extract the following information exactly as requested. No extra words, no pleasantries.\nGoal: {extraction_goal}"
                },
                {
                    "role": "user",
                    "content": safe_text
                }
            ],
            "temperature": 0.0, # صفر تماماً للاستخراج الحرفي (Exact Match)
            "max_tokens": 500
        }
        
        logger.info("⚡ Requesting Quick Data Extraction via Groq (llama3-8b)")
        return self.fetch("chat_completions", **payload)