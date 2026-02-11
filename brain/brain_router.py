# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - INTELLIGENT BRAIN ROUTER (THE ORCHESTRATOR)
=============================================================
Path: alpha_project/brain/brain_router.py
Role: العقل المدبر. يوزع المهام بذكاء ويدير حالات الفشل تلقائياً.
Status: PRODUCTION (Smart Routing Only - No Manual Hacks)
"""

import logging
import uuid
import time
from typing import Optional, Dict, List, Any

# استيراد البنية التحتية
from alpha_project.core.registry import registry
from alpha_project.ui.core.config_provider import config as sys_config

logger = logging.getLogger("Alpha.Brain.Router")

class BrainRouter:
    """
    العقل المدبر.
    لا يفكر بنفسه، ولكنه يقرر 'من' يجب أن يفكر بناءً على التخصص.
    """

    def __init__(self):
        # تحميل استراتيجية التوجيه (الذكية دائماً)
        self.strategy = "smart"
        logger.info(f"🧠 BrainRouter initialized. Strategy: {self.strategy.upper()}")

    def route_request(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        نقطة الدخول الرئيسية لتوجيه الطلبات.
        """
        context = context or {}
        # 1. إنشاء هوية جنائية للطلب (Forensic ID) وتوقيت البدء
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # ---------------------------------------------------------
        # المرحلة 1: تحليل النية (Intelligence Phase)
        # ---------------------------------------------------------
        # بدلاً من الإجبار اليدوي، النظام يحلل الطلب ليعرف ماذا يحتاج
        task_type = self._classify_intent(prompt, context)
        logger.info(f"[{request_id}] 📡 Incoming Request. Classified as: {task_type.upper()}")

        # ---------------------------------------------------------
        # المرحلة 2: اختيار المرشحين (Selection Phase)
        # ---------------------------------------------------------
        # جلب قائمة الخبراء من ملف الدستور (system_manifest.yaml)
        candidates = self._get_candidates(task_type)
        
        if not candidates:
            logger.warning(f"[{request_id}] ⚠️ No candidates found for {task_type}. Fallback to General.")
            candidates = self._get_candidates("general")

        # ---------------------------------------------------------
        # المرحلة 3: حلقة التنفيذ والتعافي (Execution & Failover Loop)
        # ---------------------------------------------------------
        last_error = ""

        for idx, candidate in enumerate(candidates):
            provider = candidate.get("provider") # local | openrouter
            model_id = candidate.get("id")       # اسم الموديل المحدد
            
            # تحويل المزود إلى اسم العميل البرمجي (Mapping)
            agent_name = self._map_provider_to_agent(provider)
            
            logger.info(f"[{request_id}] 👉 Attempt {idx+1}/{len(candidates)}: Routing to {agent_name} ({model_id})")

            try:
                # أ) التحقق من وجود العميل (Health Check)
                agent = registry.get(agent_name)
                if not agent:
                    logger.warning(f"[{request_id}] ⚠️ Agent '{agent_name}' not loaded/found. Skipping.")
                    continue

                # ب) تجهيز سياق التنفيذ (Context Injection)
                execution_context = context.copy()
                execution_context["target_model"] = model_id
                execution_context["mode"] = task_type
                execution_context["request_id"] = request_id

                # ج) التنفيذ الفعلي (The Thinking Process)
                response = agent.think(prompt, execution_context)

                # د) التحقق من جودة الرد (Quality Assurance)
                if self._validate_response(response):
                    duration = round(time.time() - start_time, 2)
                    logger.info(f"[{request_id}] ✅ Success via {agent_name} in {duration}s.")
                    return response
                else:
                    raise ValueError(f"Empty or invalid response from {agent_name}")

            except Exception as e:
                # هـ) تسجيل الفشل والمحاولة مع التالي (Failover)
                logger.error(f"[{request_id}] ❌ Failure on {model_id}: {str(e)}")
                last_error = str(e)
                continue

        # ---------------------------------------------------------
        # المرحلة 4: الإفلاس التام (Total Failure)
        # ---------------------------------------------------------
        logger.critical(f"[{request_id}] 💀 ALL SYSTEMS FAILED. Last error: {last_error}")
        return f"⚠️ **System Critical**: Unable to process request. All intelligence units failed.\nError: {last_error}"

    # =========================================================================
    # Internal Logic (The Brain Cells)
    # =========================================================================

    def _classify_intent(self, prompt: str, context: Dict) -> str:
        """
        تحليل ذكي لنوع المهمة بناءً على الكلمات المفتاحية والمحتوى.
        """
        p_lower = prompt.lower()

        # 1. الرؤية (Vision)
        if context.get("image_url") or "image" in context:
            return "vision"

        # 2. المالية (Financial) - يتطلب تفكير مالي
        if any(w in p_lower for w in ["price", "chart", "btc", "eth", "analysis", "buy", "sell"]):
            return "reasoning"

        # 3. البرمجة (Coding)
        code_keywords = ["code", "python", "function", "bug", "error", "html", "script", "terminal"]
        if any(w in p_lower for w in code_keywords):
            return "coding"

        # 4. التفكير العميق (Reasoning)
        reasoning_keywords = ["why", "explain", "plan", "logic", "strategy", "solve", "compare"]
        if any(w in p_lower for w in reasoning_keywords):
            return "reasoning"

        # 5. الافتراضي (General)
        return "general"

    def _get_candidates(self, task_type: str) -> List[Dict]:
        """قراءة قائمة الخبراء من ملف YAML."""
        candidates = sys_config.get(f"brain.specialties.{task_type}")
        if not candidates:
            return sys_config.get("brain.specialties.general", [])
        return candidates

    def _map_provider_to_agent(self, provider: str) -> str:
        """تحويل اسم المزود إلى اسم العميل."""
        if provider == "local":
            return "brain.local"
        elif provider == "openrouter":
            return "brain.gateway"
        elif provider == "market":
            return "brain.agents.market"
        else:
            return "brain.gateway"

    def _validate_response(self, response: str) -> bool:
        """التأكد من صحة الرد."""
        if not response or not isinstance(response, str):
            return False
        if response.startswith("⚠️ System Error") or response.startswith("⚠️ Security Error"):
            return False
        return True

# Singleton Instance
brain_router = BrainRouter()