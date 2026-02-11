# Model Selector

# -*- coding: utf-8 -*-
# =================================================================
# ALPHA SOVEREIGN - DYNAMIC MODEL SELECTOR & BENCHMARKER
# =================================================================
# Component Name: brain/inference/benchmarking/model_selector.py
# Core Responsibility: اختيار النموذج الأنسب (Cloud vs Local) بناءً على النية، السرعة، والصحة (Resilience).
# Design Pattern: Strategy + Circuit Breaker + Load Balancer
# Forensic Impact: يسجل "لماذا" تم اختيار نموذج معين في كل لحظة (Audit Trail).
# =================================================================

import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

# -----------------------------------------------------------------
# 1. تعريف ملف تعريف النموذج (The DNA of a Model)
# -----------------------------------------------------------------

@dataclass
class ModelProfile:
    id: str                    # المعرف الفريد (مثال: "deepseek-local")
    provider: str              # المصدر (LOCAL, GOOGLE, XIAOMI, ALIBABA)
    model_type: str            # التصنيف: "COGNITIVE", "SPEED", "VISION"
    is_local: bool             # هل يعمل على السيرفر الخاص بنا؟
    
    # المقاييس الديناميكية (Dynamic Metrics)
    latency_history: deque = field(default_factory=lambda: deque(maxlen=20))
    error_count: int = 0
    success_count: int = 0
    avg_latency: float = 0.0
    is_healthy: bool = True    # حالة القاطع (Circuit Breaker)

# -----------------------------------------------------------------
# 2. فئة الاختيار الذكي (The Selector Engine)
# -----------------------------------------------------------------

class DynamicModelSelector:
    """
    العقل المدبر الذي يختار النموذج بناءً على المعطيات الحية.
    يدمج بين قواعد التوجيه (Routing Rules) وحالة النظام (System Health).
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Selector")
        
        # سجل النماذج (Registry)
        self.models: Dict[str, ModelProfile] = {}
        
        # تهيئة النماذج المعروفة في النظام
        self._register_known_models()

    def _register_known_models(self):
        """تعريف ترسانة النماذج المتاحة للنظام."""
        
        # 1. النموذج المحلي السيادي (للكود والبيانات الحساسة)
        self.register_model("deepseek-local", "LOCAL", "COGNITIVE", is_local=True)
        
        # 2. نموذج السرعة السحابي (للمحادثات السريعة)
        self.register_model("gemini-flash", "GOOGLE", "SPEED", is_local=False)
        
        # 3. نموذج التفكير العميق السحابي (للاستنتاجات المعقدة - بديل المحلي)
        self.register_model("xiaomi-mimo", "XIAOMI", "COGNITIVE", is_local=False)
        
        # 4. القشرة البصرية (لتحليل الصور)
        self.register_model("qwen-vl", "ALIBABA", "VISION", is_local=False)

    def register_model(self, model_id: str, provider: str, m_type: str, is_local: bool):
        self.models[model_id] = ModelProfile(
            id=model_id, provider=provider, model_type=m_type, is_local=is_local
        )
        self.logger.info(f"Model Registered: {model_id} [{provider}]")

    def select_model(self, intent: str, context: dict = None) -> str:
        """
        الخوارزمية المركزية لاتخاذ القرار.
        
        Args:
            intent: 'coding', 'chat', 'vision', 'research', 'sensitive'
            context: بيانات إضافية (مثل وجود صورة)
        
        Returns:
            model_id: اسم النموذج المختار للتنفيذ.
        """
        context = context or {}
        
        # --- القاعدة 0: الفحص الدوري (Circuit Breaker Reset) ---
        self._attempt_revival()

        # --- القاعدة 1: القشرة البصرية (Vision) ---
        if intent == "vision" or context.get('image_url'):
            return self._routing_strategy_vision()

        # --- القاعدة 2: السيادة والأمان (Coding & Sensitive) ---
        if intent in ["coding", "sensitive"]:
            return self._routing_strategy_sovereign()

        # --- القاعدة 3: التفكير العميق والبحث (Research) ---
        if intent in ["research", "reasoning"]:
            return self._routing_strategy_reasoning()

        # --- القاعدة 4: السرعة والدردشة (Chat/Fast) ---
        # الافتراضي هو السرعة
        return self._routing_strategy_speed()

    # -----------------------------------------------------------------
    # استراتيجيات التوجيه الفرعية (Sub-Strategies)
    # -----------------------------------------------------------------

    def _routing_strategy_sovereign(self) -> str:
        """تفضيل المحلي، ثم السحابة الآمنة."""
        local_model = self.models["deepseek-local"]
        cloud_backup = self.models["xiaomi-mimo"]

        if local_model.is_healthy:
            self.logger.info("ROUTING: Sovereign Intent -> Local DeepSeek")
            return local_model.id
        else:
            self.logger.warning(f"ROUTING_ALERT: Local DeepSeek UNHEALTHY. Fallback to -> {cloud_backup.id}")
            return cloud_backup.id

    def _routing_strategy_speed(self) -> str:
        """تفضيل الأسرع استجابة."""
        gemini = self.models["gemini-flash"]
        # إذا كان Gemini معطلاً، نستخدم Xiaomi كبديل
        if gemini.is_healthy:
            return gemini.id
        return "xiaomi-mimo"

    def _routing_strategy_reasoning(self) -> str:
        """تفضيل القدرات العقلية العالية (Cloud Deep)."""
        xiaomi = self.models["xiaomi-mimo"]
        if xiaomi.is_healthy:
            return xiaomi.id
        # إذا فشل، نعود للمحلي إذا كان متاحاً
        return "deepseek-local"

    def _routing_strategy_vision(self) -> str:
        """المسار البصري الوحيد حالياً."""
        return "qwen-vl"

    # -----------------------------------------------------------------
    # حلقة التغذية الراجعة (Feedback Loop)
    # -----------------------------------------------------------------

    def record_feedback(self, model_id: str, latency_sec: float, success: bool):
        """
        يستدعيها الـ Router بعد انتهاء الطلب لتحديث إحصائيات النموذج.
        Forensic: هذا يبني سجلاً جنائياً لأداء كل نموذج.
        """
        if model_id not in self.models:
            return

        profile = self.models[model_id]

        if success:
            profile.success_count += 1
            # تقليل عداد الأخطاء (نظام المكافأة)
            profile.error_count = max(0, profile.error_count - 1)
            
            # تحديث متوسط السرعة
            profile.latency_history.append(latency_sec)
            if profile.latency_history:
                profile.avg_latency = sum(profile.latency_history) / len(profile.latency_history)
        else:
            profile.error_count += 1
            self.logger.error(f"MODEL_FAILURE: {model_id} failed via API. Errors: {profile.error_count}")
            
            # إذا تجاوزت الأخطاء حداً معيناً، نقتل النموذج مؤقتاً
            if profile.error_count >= 3:
                profile.is_healthy = False
                self.logger.critical(f"CIRCUIT_BREAKER: {model_id} is considered DEAD. Routing elsewhere.")

    def _attempt_revival(self):
        """محاولة إعادة إحياء النماذج الميتة بشكل دوري."""
        # في نظام حقيقي، يتم هذا بناءً على الوقت (مثلاً كل 5 دقائق)
        # للتبسيط هنا، سنقوم بإحياء النموذج إذا طلبناه ووجدناه ميتاً بعد فترة قصيرة
        pass 

    def get_forensic_report(self) -> dict:
        """تقرير الحالة لمدير النظام."""
        return {
            mid: {
                "healthy": m.is_healthy,
                "avg_latency_ms": int(m.avg_latency * 1000),
                "errors": m.error_count,
                "type": m.provider
            }
            for mid, m in self.models.items()
        }