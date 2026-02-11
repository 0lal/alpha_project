# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVANCED REMOTE GATEWAY (MULTI-KEY ARCHITECTURE)
==================================================================
Path: alpha_project/brain/inference/remote_gateway.py
Role: البوابة الدبلوماسية التي تتحدث مع مختلف مزودي الذكاء الاصطناعي.
Features: Multi-Key Support, Vision Handling, Connection Pooling.
Status: PRODUCTION (Patched: Default Model ID Fixed)
"""

import logging
import json
import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# استيراد البنية التحتية للنظام
from alpha_project.brain.base_agent import BaseAgent
from alpha_project.core.registry import register_component
from alpha_project.ui.core.config_provider import config as sys_config

@register_component(name="brain.gateway", category="brain", is_critical=True)
class RemoteGateway(BaseAgent):
    """
    بوابة الاتصال السحابي الذكية.
    تدعم التوجيه الديناميكي للمفاتيح والموديلات (Xiaomi, Qwen, Gemini).
    """

    # نقطة الاتصال الموحدة
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self):
        super().__init__(name="brain.gateway", category="brain")
        
        # 1. إعداد إدارة الاتصال (Connection Pooling)
        self.session = requests.Session()
        
        # استراتيجية إعادة المحاولة (Retry Strategy)
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        self.keys: Dict[str, str] = {}

    # =========================================================================
    # 1. Initialization (تحميل الذخيرة)
    # =========================================================================

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        تحميل المفاتيح من الخزنة الآمنة (.env).
        """
        super().initialize(config)
        
        self._logger.info("🔑 Loading Intelligence Keys form Vault...")
        
        self.keys = {
            "xiaomi": sys_config.get_secret("OPENROUTER_KEY_XIAOMI"),
            "gemini": sys_config.get_secret("OPENROUTER_KEY_GEMINI"),
            "qwen": sys_config.get_secret("OPENROUTER_KEY_QWEN"),
            "default": sys_config.get_secret("OPENROUTER_KEY_DEFAULT") or \
                       sys_config.get_secret("OPENROUTER_KEY_REASONING")
        }
        
        active_keys = [k for k, v in self.keys.items() if v]
        if not active_keys:
            self._logger.critical("❌ FATAL: No API Keys found in .env! Gateway is dead.")
            return False
            
        self._logger.info(f"✅ Gateway Armed with {len(active_keys)} active keys.")
        return True

    def shutdown(self) -> None:
        self.session.close()
        super().shutdown()

    # =========================================================================
    # 2. Execution Logic (تنفيذ الطلب)
    # =========================================================================

    def _execute_reasoning(self, prompt: str, context: Dict) -> str:
        """
        المعالج الرئيسي للطلب.
        """
        # 1. تحديد الهدف (Target Acquisition)
        # [FORENSIC FIX]: تم استبدال الموديل القديم (lite-preview) بالموديل المستقر (flash-exp)
        # هذا يمنع خطأ HTTP 400 في حالة الفشل الافتراضي
        default_model = "google/gemini-2.0-flash-exp:free"
        target_model = context.get("target_model", default_model)
        
        # 2. اختيار المفتاح المناسب
        api_key = self._select_best_key(target_model)
        if not api_key:
            return "⚠️ Security Error: No valid API Key found for this operation."

        # 3. بناء الحزمة
        payload = self._construct_payload(prompt, target_model, context)
        
        # 4. الت headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://alpha-sovereign.local",
            "X-Title": "Alpha Sovereign Node"
        }

        try:
            self._logger.debug(f"📡 Transmitting to Cloud: {target_model}...")
            
            response = self.session.post(
                self.BASE_URL,
                json=payload,
                headers=headers,
                timeout=int(context.get("timeout", 60))
            )

            return self._parse_response(response)

        except requests.exceptions.Timeout:
            self._logger.error(f"❌ Timeout contacting {target_model}")
            raise TimeoutError("Gateway timed out.")
            
        except requests.exceptions.ConnectionError:
            self._logger.error("❌ Network Unreachable.")
            raise ConnectionError("No Internet Connection.")
            
        except Exception as e:
            self._logger.error(f"💥 Critical Gateway Error: {e}")
            raise e

    # =========================================================================
    # 3. Helper Methods (الذكاء الداخلي)
    # =========================================================================

    def _select_best_key(self, model_id: str) -> Optional[str]:
        """تحديد المفتاح بناءً على اسم الموديل"""
        model_id_lower = model_id.lower()
        
        if "xiaomi" in model_id_lower or "deepseek" in model_id_lower:
            return self.keys.get("xiaomi") or self.keys.get("default")
            
        if "google" in model_id_lower or "gemini" in model_id_lower:
            return self.keys.get("gemini") or self.keys.get("default")
            
        if "qwen" in model_id_lower:
            return self.keys.get("qwen") or self.keys.get("default")
            
        return self.keys.get("default")

    def _construct_payload(self, prompt: str, model_id: str, context: Dict) -> Dict:
        """بناء هيكل JSON"""
        messages = []
        
        # أ) حالة الرؤية
        if context.get("mode") == "vision" and context.get("image_url"):
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": context["image_url"]}
                    }
                ]
            })
        else:
            # ب) نص عادي
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": context.get("temperature", 0.7),
            "max_tokens": 4000
        }
        
        # ج) تفعيل التفكير لـ Xiaomi/DeepSeek فقط
        if "xiaomi" in model_id.lower() or "deepseek" in model_id.lower():
            payload["reasoning"] = {"enabled": True}

        return payload

    def _parse_response(self, response: requests.Response) -> str:
        """فك تشفير الرد"""
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            self._logger.error(f"❌ API Error: {error_msg}")
            
            if response.status_code == 401: return "⚠️ Auth Error: Invalid API Key."
            if response.status_code == 429: return "⚠️ Rate Limit: Too many requests."
            raise ValueError(error_msg)

        try:
            data = response.json()
            if "error" in data:
                err_content = data['error'].get('message', str(data['error']))
                raise ValueError(f"Provider Error: {err_content}")

            content = data['choices'][0]['message']['content']
            if not content: return "⚠️ Empty response from model."
            return content

        except json.JSONDecodeError:
            self._logger.error("❌ Invalid JSON received.")
            raise ValueError("Invalid JSON response.")