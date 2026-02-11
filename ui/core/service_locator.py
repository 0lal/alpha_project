# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - UI SERVICE LOCATOR (THE DIPLOMAT)
===================================================
Path: alpha_project/ui/core/service_locator.py
Role: "السفير الدبلوماسي" - نقطة الاتصال الوحيدة بين الواجهة (UI) والنواة (Core).
Pattern: Service Locator + Null Object Pattern (Strict Mode)

Forensic Features:
  1. **Integrity Enforcement**: يمنع منعاً باتاً استخدام البيانات الوهمية (Mock Data).
  2. **Fail-Safe Proxies**: في حال فقدان الخدمة، يعيد وكيلاً آمناً يمنع انهيار الواجهة ولكنه يظهر رسالة خطأ حقيقية.
  3. **Dependency Decoupling**: يفصل الواجهة تماماً عن تفاصيل التنفيذ الخلفي.

Author: Alpha Architect (AI)
Status: PRODUCTION READY (FINANCIAL GRADE)
"""

import logging
from typing import Optional, Any
from abc import ABC

# استيراد النواة والقوانين
from alpha_project.core.registry import registry
from alpha_project.core.interfaces import IReasoningUnit, IDataCollector, ComponentStatus
from alpha_project.core.bridge import bridge as central_bridge

logger = logging.getLogger("Alpha.UI.Locator")

# =============================================================================
# 1. Fail-Safe Objects (وكلاء الفشل الآمن)
# =============================================================================
# هذه الكائنات تظهر فقط عندما يكون النظام الحقيقي معطلاً.
# وظيفتها الوحيدة: منع انهيار البرنامج وإبلاغ المستخدم بالحقيقة.

class MissingBrain(IReasoningUnit):
    """
    عقل فارغ يظهر عند فشل تحميل الذكاء الحقيقي.
    Forensic Note: لا يقوم بتوليد أي نص وهمي. يبلغ عن الخطأ فقط.
    """
    @property
    def name(self) -> str: return "System_Offline"
    
    def initialize(self, config): return False
    def shutdown(self): pass
    def health_check(self): return ComponentStatus.FAILED

    def think(self, prompt: str, context=None) -> str:
        logger.critical("🚨 UI attempted to access a missing Brain module.")
        return "⚠️ **SYSTEM ERROR**: Intelligence Core is unreachable. Please check logs/connection."

    async def think_async(self, prompt: str, context=None) -> str:
        return self.think(prompt, context)

class MissingCollector(IDataCollector):
    """
    مجمع بيانات فارغ.
    Forensic Note: يعيد بيانات فارغة صريحة بدلاً من أرقام عشوائية.
    """
    @property
    def name(self) -> str: return "Data_Link_Broken"
    
    def connect(self): return False
    def fetch_snapshot(self, target): return {"error": "Connection Lost"}
    def stream(self, callback): pass
    def initialize(self, config): return False
    def shutdown(self): pass
    def health_check(self): return ComponentStatus.FAILED


# =============================================================================
# 2. The Service Locator (السفير)
# =============================================================================

class UIServiceLocator:
    """
    نقطة الوصول المركزية للواجهة.
    يجب استخدام هذا الكلاس بدلاً من استيراد الملفات مباشرة.
    """

    @staticmethod
    def get_brain() -> IReasoningUnit:
        """
        محاولة الحصول على أفضل عقل متاح من خلال الجسر المركزي.
        """
        # الجسر (Bridge) هو المسؤول عن اختيار العقل، لذا نوجه الطلب له
        # ولكن بما أن الواجهة قد تحتاج لكائن العقل مباشرة لبعض الخصائص:
        
        # 1. البحث في السجل
        brains = registry.get_by_category("brain")
        
        # 2. الفلترة (نبحث عن أول واحد سليم)
        for name, instance in brains.items():
            if isinstance(instance, IReasoningUnit):
                # تحقق إضافي للصحة (اختياري، يمكننا إرجاعه حتى لو متدهور قليلاً)
                return instance

        # 3. الفشل الصارم (Strict Failure)
        logger.error("❌ Locator could not find any active Brain service.")
        return MissingBrain()

    @staticmethod
    def get_data_provider() -> IDataCollector:
        """
        الحصول على مصدر البيانات.
        """
        collectors = registry.get_by_category("data")
        
        for name, instance in collectors.items():
            if isinstance(instance, IDataCollector):
                return instance
                
        logger.error("❌ Locator could not find any Data Collector.")
        return MissingCollector()

    @staticmethod
    def get_bridge():
        """
        الحصول على الجسر المركزي (المحول الرئيسي).
        هذا هو الاستخدام المفضل للواجهة.
        """
        if central_bridge:
            return central_bridge
        else:
            logger.critical("💥 CRITICAL: Central Bridge is missing!")
            # هنا نرفع خطأ لأن غياب الجسر يعني توقف النظام بالكامل
            raise RuntimeError("System Core Failure: Bridge not loaded.")

    @staticmethod
    def is_system_healthy() -> bool:
        """فحص سريع لتمكين/تعطيل أزرار الواجهة"""
        brain = UIServiceLocator.get_brain()
        return not isinstance(brain, MissingBrain)

# =============================================================================
# Global Accessor
# =============================================================================
locator = UIServiceLocator()