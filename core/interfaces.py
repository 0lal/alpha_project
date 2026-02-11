# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - SYSTEM INTERFACES (THE CONSTITUTION)
======================================================
Path: alpha_project/core/interfaces.py
Role: "عقود العمل الصارمة" - تعريف الهيكل الإلزامي لكل مكون في النظام.
Type: Abstract Base Classes (ABC) / Type Definitions

Forensic Features:
  1. **Strict Enforcement**: يمنع تشغيل أي كلاس لا يلتزم بالمعايير (يمنع Crashes وقت التشغيل).
  2. **Lifecycle Management**: يفرض وجود دوال البدء (Initialize) والإنهاء (Shutdown) لمنع تسريب الذاكرة.
  3. **Type Safety**: استخدام Type Hints لضمان تدفق البيانات بشكل صحيح بين الوحدات.
  4. **Health Protocols**: يفرض وجود آلية للفحص الذاتي لكل وحدة.

Author: Alpha Architect (AI)
Status: CORE DEFINITION (Do Not Modify without Consensus)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import enum

# =============================================================================
# 1. Universal Constants & Types (الثوابت العالمية)
# =============================================================================

class ComponentStatus(enum.Enum):
    """حالات المكونات للنظام التشخيصي"""
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # يعمل ولكن ببطء أو أخطاء
    FAILED = "failed"
    STOPPED = "stopped"

# =============================================================================
# 2. Base Contract (العقد الموحد لجميع الكائنات)
# =============================================================================

class ISovereignComponent(ABC):
    """
    العقد الأب (Root Interface).
    أي شيء يريد أن يعيش داخل Alpha Sovereign يجب أن يرث من هذا الكلاس.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """اسم المكون الفريد (للسجل)"""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        مرحلة التجهيز (Booting).
        يجب أن تجهز اتصالاتك وتحمل ملفاتك هنا.
        Return: True إذا نجح، False إذا فشل.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        مرحلة التنظيف (Cleanup).
        يجب إغلاق أي ملفات أو اتصالات مفتوحة هنا.
        جنائي: هذا يمنع 'Zombie Processes'.
        """
        pass

    @abstractmethod
    def health_check(self) -> ComponentStatus:
        """
        الفحص الذاتي (Diagnostic Pulse).
        النظام سيسألك دورياً: 'هل أنت بخير؟'
        """
        pass

# =============================================================================
# 3. Brain Interfaces (عقود الذكاء والعقل)
# =============================================================================

class IReasoningUnit(ISovereignComponent):
    """
    عقد وحدات التفكير (Brain Agents).
    يجب أن تكون قادرة على استقبال مدخلات ومعالجة 'تفكير'.
    """

    @abstractmethod
    def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        الوظيفة الجوهرية: التفكير والاستنتاج.
        Args:
            prompt: السؤال أو البيانات المدخلة.
            context: سياق إضافي (ذاكرة، أسعار سابقة).
        """
        pass

    @abstractmethod
    async def think_async(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        التفكير المتزامن (لعدم تجميد الواجهة).
        مستقبلي: لدعم DeepSeek R1 والنماذج البطيئة.
        """
        pass

# =============================================================================
# 4. Data Interfaces (عقود جمع المعلومات)
# =============================================================================

class IDataCollector(ISovereignComponent):
    """
    عقد جامعي البيانات (Data Connectors).
    سواء كانت Binance, Twitter, News API.
    """

    @abstractmethod
    def connect(self) -> bool:
        """فتح خط الاتصال بالمصدر"""
        pass

    @abstractmethod
    def fetch_snapshot(self, target: str) -> Dict[str, Any]:
        """
        جلب صورة لحظية للبيانات.
        مثال: سعر البيتكوين الآن.
        """
        pass

    @abstractmethod
    def stream(self, callback: Any) -> None:
        """
        فتح صنبور البيانات المستمر (WebSockets).
        جنائي: يجب أن يتعامل مع انقطاع النت وإعادة الاتصال ذاتياً.
        """
        pass

# =============================================================================
# 5. Execution Interfaces (عقود التنفيذ والاستراتيجية)
# =============================================================================

class IStrategy(ISovereignComponent):
    """
    عقد الاستراتيجيات (The Executors).
    تأخذ بيانات -> تخرج قرارات.
    """

    @abstractmethod
    def on_tick(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        يتم استدعاؤها مع كل تحديث للسعر.
        Return: قرار (Buy/Sell) أو None.
        """
        pass

    @abstractmethod
    def get_confidence_score(self) -> float:
        """
        مستوى الثقة في الوضع الحالي (0.0 - 1.0).
        يستخدمه 'Weighted Voter' لاتخاذ القرار النهائي.
        """
        pass

# =============================================================================
# 6. UI/Service Bridge (عقد التواصل مع الواجهة)
# =============================================================================

class IServiceLocator(ABC):
    """
    عقد موفر الخدمات.
    الواجهة ستستخدم هذا فقط ولن تعرف شيئاً عما يدور في الخلفية.
    """
    
    @abstractmethod
    def get_brain(self) -> IReasoningUnit:
        """أعطني العقل المفكر الحالي"""
        pass

    @abstractmethod
    def get_market_data(self) -> IDataCollector:
        """أعطني مصدر البيانات الحالي"""
        pass