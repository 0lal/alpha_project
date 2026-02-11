# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - CENTRAL BRIDGE ADAPTER (THE SWITCHBOARD)
==========================================================
Path: alpha_project/core/bridge.py
Role: "محول العمليات" - عزل الواجهة عن التعقيدات الخلفية وتوجيه الأوامر بذكاء.
Pattern: Facade + Adapter Pattern

Forensic Features:
  1. **Dynamic Resolution**: لا يستورد أي ملفات ذكاء. يطلبها من السجل (Registry) وقت التشغيل.
  2. **Failover Routing**: إذا فشل المكون الأساسي، يبحث عن البديل تلقائياً.
  3. **Traffic Logging**: يسجل كل "عبور" للبيانات مع طابع زمني ومعرف تتبع (Trace ID).
  4. **Error Sanitization**: يمنع وصول الأخطاء البرمجية (Tracebacks) للمستخدم، ويحولها لرسائل ودية.

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any, List

# استيراد النواة (نحتاج فقط السجل والدستور)
from alpha_project.core.registry import registry
from alpha_project.core.interfaces import IReasoningUnit, IDataCollector, ComponentStatus

logger = logging.getLogger("Alpha.Core.Bridge")

class CentralBridge:
    """
    الجسر المركزي (The Bridge).
    الواجهة الرسومية (UI) يجب أن تتحدث *فقط* مع هذا الكلاس.
    """

    def __init__(self):
        self._logger = logger
        # لا نقوم بتهيئة أي شيء هنا، نعتمد على السجل الديناميكي
        self._logger.info("🌉 Central Bridge Online. Waiting for traffic.")

    # =========================================================================
    # 1. Intelligence Routing (توجيه عمليات التفكير)
    # =========================================================================
    
    def ask_brain(self, user_prompt: str, context: Optional[Dict] = None) -> str:
        """
        واجهة الطلب من العقل.
        تقوم بالبحث عن أي عقل متاح (سحابي أو محلي) وتمرير الطلب له.
        """
        trace_id = str(uuid.uuid4())[:8]
        self._logger.info(f"[{trace_id}] 📨 Bridge received prompt: {user_prompt[:30]}...")

        # 1. البحث في السجل عن أي خدمة تصنيفها 'brain'
        # [Strategy]: نطلب كل العقول، ونختار الأفضل صحياً
        brain_services = registry.get_by_category("brain")
        
        if not brain_services:
            self._logger.critical(f"[{trace_id}] ❌ NO BRAINS FOUND in Registry!")
            return "⚠️ **System Critical**: No Intelligence Unit is currently loaded. Please run diagnostics."

        # 2. اختيار العميل المناسب (Selection Logic)
        # الأولوية: العميل الذي حالته HEALTHY
        selected_brain: Optional[IReasoningUnit] = None
        
        for name, brain in brain_services.items():
            if isinstance(brain, IReasoningUnit):
                if brain.health_check() == ComponentStatus.HEALTHY:
                    selected_brain = brain
                    break
                elif brain.health_check() == ComponentStatus.DEGRADED:
                    # نقبل المتدهور كبديل مؤقت
                    selected_brain = brain

        if not selected_brain:
            # إذا لم نجد أي عقل سليم، نأخذ أي واحد موجود (محاولة يائسة)
            selected_brain = list(brain_services.values())[0]
            self._logger.warning(f"[{trace_id}] ⚠️ Using fallback brain (Status Unknown): {selected_brain.name}")
        else:
            self._logger.info(f"[{trace_id}] 🧠 Routed to: {selected_brain.name}")

        # 3. التنفيذ الآمن (Safe Execution)
        try:
            response = selected_brain.think(user_prompt, context)
            self._logger.info(f"[{trace_id}] ✅ Response received from brain.")
            return response
        except Exception as e:
            self._logger.error(f"[{trace_id}] 💥 Bridge Error: {e}")
            return f"⚠️ **Bridge Failure**: Unable to communicate with {selected_brain.name}."

    # =========================================================================
    # 2. Data Routing (توجيه طلبات البيانات)
    # =========================================================================

    def get_market_snapshot(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        طلب بيانات السوق. يبحث عن أي Data Collector متاح.
        """
        collectors = registry.get_by_category("data")
        
        if not collectors:
            return {"error": "No data collectors loaded"}

        # البحث عن مجمع متخصص في السوق (Market)
        # هذا يتطلب أن يكون لدينا خاصية 'source_type' في المجمع (التي أضفناها في BaseCollector)
        for name, collector in collectors.items():
            if isinstance(collector, IDataCollector):
                # هنا يمكننا إضافة منطق لاختيار المصدر الأسرع
                try:
                    data = collector.fetch_snapshot(symbol)
                    if data:
                        return data
                except Exception as e:
                    self._logger.warning(f"Collector {name} failed: {e}")
                    continue # جرب التالي
        
        return {"error": "All collectors failed to retrieve data"}

    # =========================================================================
    # 3. System Control (التحكم في النظام)
    # =========================================================================

    def get_system_status(self) -> str:
        """
        تقرير سريع للواجهة عن حالة النظام.
        يعيد نصاً جاهزاً للعرض.
        """
        services = registry.list_services()
        total = len(services)
        healthy = sum(1 for s in services if self._is_service_healthy(s['name']))
        
        status_msg = f"🟢 **System Online**\n"
        status_msg += f"• Active Modules: {healthy}/{total}\n"
        status_msg += f"• Brains Linked: {len(registry.get_by_category('brain'))}\n"
        status_msg += f"• Sensors Linked: {len(registry.get_by_category('data'))}"
        
        return status_msg

    def _is_service_healthy(self, name: str) -> bool:
        """فحص داخلي سريع"""
        svc = registry.get(name)
        if svc and hasattr(svc, 'health_check'):
            return svc.health_check() == ComponentStatus.HEALTHY
        return True # نفترض الصحة إذا لم يكن هناك فحص

# =============================================================================
# Global Bridge Instance (Singleton Facade)
# =============================================================================
# هذا المتغير هو ما ستستورده الواجهة: from alpha_project.core.bridge import bridge

bridge = CentralBridge()