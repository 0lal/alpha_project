import logging
from typing import Dict, Any, Optional, List, Tuple
import json

# استيراد القالب الأم الذي يطبق سياسات الأمان والحدود
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Google Gemini
logger = logging.getLogger("Alpha.Drivers.GoogleGemini")

class GeminiDriver(BaseConnector):
    """
    الذراع التنفيذي للذكاء الاصطناعي من جوجل (Gemini).
    
    المهام الجنائية:
    1. توفير تحليل مالي عميق باستخدام نماذج Pro و Flash.
    2. تطبيق "مضاد الرقابة" لضمان قبول المصطلحات المالية القاسية.
    3. الهبوط الآمن (Failover): إذا كان Pro مشغولاً (2 RPM)، يتم التحويل إلى Flash فوراً.
    4. استخراج النصوص من هيكل JSON المعقد جداً الخاص بجوجل.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات من google_gemini_keys.json
        super().__init__("google")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: Google Gemini API Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        [تجاوز إجباري] بناء الرابط.
        جوجل تتطلب وضع اسم النموذج بداخل الرابط نفسه.
        """
        # الرابط الأساسي: https://generativelanguage.googleapis.com/v1beta/models
        base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        # هنا endpoint_key سيكون اسم النموذج (مثل: gemini-1.5-pro أو gemini-1.5-flash)
        return f"{base_url}/{endpoint_key}:generateContent"

    def get_default_params(self) -> Dict[str, str]:
        """
        [تجاوز إجباري]
        جوجل تتطلب وضع مفتاح الـ API في الرابط (Query Parameters) وليس في الترويسة.
        """
        return {"key": self.api_key}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        دمج إعدادات الأمان (Safety Settings) لمنع جوجل من حظر المصطلحات المالية.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        headers["Content-Type"] = "application/json"
        
        # 1. استخراج إعدادات الأمان من ملف التكوين (google_gemini_keys.json)
        safety_config = self.config.get("safety_settings", {})
        
        # 2. بناء هيكل الأمان القياسي لجوجل
        safety_settings_payload = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": safety_config.get("HARM_CATEGORY_HARASSMENT", "BLOCK_ONLY_HIGH")},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": safety_config.get("HARM_CATEGORY_HATE_SPEECH", "BLOCK_ONLY_HIGH")},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": safety_config.get("HARM_CATEGORY_SEXUALLY_EXPLICIT", "BLOCK_ONLY_HIGH")},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": safety_config.get("HARM_CATEGORY_DANGEROUS_CONTENT", "BLOCK_ONLY_HIGH")}
        ]

        # 3. حقن الإعدادات بداخل جسم الطلب (Payload)
        final_params["safetySettings"] = safety_settings_payload

        # جوجل تستخدم POST دائماً
        return url, "POST", final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[str]:
        """
        [تجاوز جنائي وهبوط آمن - Auto-Failover Override]
        يرسل الطلب، يستخرج النص، وإذا اصطدم بحد الـ 2 RPM الخاص بنسخة Pro، يحول لـ Flash.
        """
        # 1. إرسال الطلب عبر جدار الحماية في القالب الأم
        result = super().fetch(endpoint_key, **params)
        
        # 2. الهبوط الآمن (Failover Strategy)
        # إذا عاد None، فهذا يعني أن القالب الأم اكتشف خطأ (مثل 429 Too Many Requests)
        if not result and endpoint_key == "gemini-1.5-pro":
            logger.warning("⚠️ Gemini 1.5 Pro failed or hit rate limit (2 RPM). Instantly falling back to Gemini 1.5 Flash.")
            
            # توثيق الحدث الجنائي
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_decision("GEMINI_FAILOVER", "PRO_LIMIT_REACHED", "Switched to FLASH", confidence=1.0)
                
            # إعادة المحاولة فوراً باستخدام Flash (الذي يمتلك 15 RPM)
            return super().fetch("gemini-1.5-flash", **params)
            
        # 3. إذا فشل Flash أيضاً، أو فشل الطلب لأي سبب آخر، نتوقف هنا
        if not result or not isinstance(result, dict):
            return None

        # 4. استخراج المحتوى (Content) من هيكل جوجل المعقد
        try:
            candidates = result.get("candidates", [])
            if not candidates:
                # هذا يحدث غالباً إذا تم حظر الطلب بسبب سياسات الأمان رغم محاولاتنا
                prompt_feedback = result.get("promptFeedback", {})
                logger.error(f"🛑 Gemini API Blocked the request. Feedback: {prompt_feedback}")
                return None
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.error("🛑 Gemini API Error: Empty parts received.")
                return None
                
            # إرجاع النص الصافي
            return parts[0].get("text", "").strip()

        except Exception as e:
            logger.error(f"🛑 Gemini JSON Parsing Error: {str(e)}")
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_error("GEMINI_PARSE_ERROR", "Failed to extract AI content", str(e))
            return None

    # =========================================================================
    # أذرع التحليل الذكي (Intelligence Arms)
    # =========================================================================

    def analyze_complex_scenario(self, system_prompt: str, scenario_data: str) -> Optional[str]:
        """
        تحليل مالي عميق ومعقد (Deep Reasoning).
        يستخدم نموذج `gemini-1.5-pro` القوي جداً (ولكن البطيء والمقيد).
        """
        # تجهيز هيكل المحادثة الخاص بجوجل
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        # ندمج التعليمات الصارمة مع البيانات لمنع الهلوسة
                        {"text": f"SYSTEM INSTRUCTION: You are a strict financial forensic AI. Base your answers ONLY on facts. No hallucinations.\n\nRULES:\n{system_prompt}\n\nDATA:\n{scenario_data}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2, # حرارة منخفضة جداً للصرامة المالية
                "topP": 0.8,
                "maxOutputTokens": 4096
            }
        }
        
        logger.info("🧠 Requesting Deep Financial Reasoning via Gemini 1.5 Pro")
        return self.fetch("gemini-1.5-pro", **payload)

    def process_large_document(self, system_prompt: str, document_text: str) -> Optional[str]:
        """
        معالجة نصوص ضخمة (مثل تقرير أرباح من 50 صفحة).
        يستخدم نموذج `gemini-1.5-flash` لأنه يمتلك نافذة سياق ضخمة وسريع جداً.
        """
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"INSTRUCTION: {system_prompt}\n\nDOCUMENT:\n{document_text}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1, # استخراج حرفي ودقيق
                "maxOutputTokens": 8192
            }
        }
        
        logger.info("⚡ Requesting High-Speed Document Processing via Gemini 1.5 Flash")
        return self.fetch("gemini-1.5-flash", **payload)