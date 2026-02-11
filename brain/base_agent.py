# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - BASE INTELLIGENCE AGENT (THE DNA)
===================================================
Path: alpha_project/brain/base_agent.py
Role: "القالب الأم" - يوفر البنية التحتية المشتركة لجميع وحدات الذكاء.
Inherits: IReasoningUnit (The Contract)

Forensic Features:
  1. **Automatic Audit Trail**: تسجيل كل عملية تفكير (Input/Output/Latency) تلقائياً.
  2. **Error Containment Shield**: درع برمجي يمنع أخطاء العميل من إيقاف النظام.
  3. **Performance Metrics**: قياس زمن الاستجابة لكل عميل لتحديد "الحلقات الأضعف".
  4. **Context Management**: إدارة ذاكرة قصيرة المدى مدمجة.

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import logging
import time
import uuid
import traceback
from abc import abstractmethod
from typing import Dict, Any, Optional, List

# استيراد القوانين والنواة
from alpha_project.core.interfaces import IReasoningUnit, ComponentStatus
from alpha_project.core.registry import registry

class BaseAgent(IReasoningUnit):
    """
    العميل الأساسي (Base Agent).
    يجب على أي عميل ذكاء (Risk, Sentiment, Strategy) أن يرث من هذا الكلاس.
    
    يوفر: Logging, Error Handling, Config Management, Health Checks.
    """

    def __init__(self, name: str, category: str = "brain"):
        self._name = name
        self._category = category
        self._id = str(uuid.uuid4())[:8] # بصمة فريدة للنسخة
        self._logger = logging.getLogger(f"Alpha.Brain.{name}")
        
        # الحالة الداخلية
        self._status = ComponentStatus.STARTING
        self._config: Dict[str, Any] = {}
        self._memory: List[Dict] = [] # ذاكرة قصيرة المدى (Short-term context)
        
        self._logger.info(f"🧬 Agent Born: {self.name} (ID: {self._id})")

    # =========================================================================
    # 1. Implementation of ISovereignComponent (تنفيذ العقد الأساسي)
    # =========================================================================
    
    @property
    def name(self) -> str:
        return self._name

    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        مرحلة التجهيز. تقوم بتحميل الإعدادات والتحقق منها.
        يمكن للكلاس الابن (Subclass) عمل Override لإضافة منطق خاص.
        """
        self._logger.info(f"⚙️ Initializing {self.name}...")
        self._config = config
        
        try:
            # استدعاء دالة تحقق خاصة (يحددها الابن)
            if self._validate_config(config):
                self._status = ComponentStatus.HEALTHY
                self._logger.info(f"✅ {self.name} is Operational.")
                return True
            else:
                self._status = ComponentStatus.FAILED
                self._logger.error(f"❌ {self.name} Config Validation Failed.")
                return False
        except Exception as e:
            self._logger.critical(f"💥 Initialization Crash: {e}")
            self._status = ComponentStatus.FAILED
            return False

    def shutdown(self) -> None:
        """تنظيف الموارد قبل الإغلاق"""
        self._status = ComponentStatus.STOPPED
        self._logger.info(f"💤 {self.name} shutting down...")
        # يمكن إضافة حفظ الذاكرة هنا مستقبلاً

    def health_check(self) -> ComponentStatus:
        """فحص النبض"""
        return self._status

    # =========================================================================
    # 2. The Core Thinking Logic (محرك التفكير الآمن)
    # =========================================================================

    def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        الغلاف الآمن لعملية التفكير (The Safe Wrapper).
        لا تقم بتعديل هذه الدالة في الكلاسات الفرعية.
        عدل `_execute_reasoning` بدلاً منها.
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())[:6] # لتتبع الطلب في السجلات
        
        # 1. التدقيق الجنائي للمدخلات
        self._logger.debug(f"[{correlation_id}] 🤔 Thinking about: {prompt[:50]}...")
        
        try:
            # تحديث السياق المؤقت
            current_context = context or {}
            
            # 2. استدعاء المنطق الفعلي (الذي يكتبه المبرمج)
            response = self._execute_reasoning(prompt, current_context)
            
            # 3. حساب الأداء
            latency = round(time.time() - start_time, 3)
            
            # 4. التدقيق الجنائي للمخرجات
            self._logger.info(f"[{correlation_id}] 💡 Insight Generated in {latency}s")
            
            # تحديث الحالة إذا كانت متدهورة
            if self._status == ComponentStatus.DEGRADED:
                self._status = ComponentStatus.HEALTHY
                
            return response

        except Exception as e:
            # 5. احتواء الكارثة (Disaster Containment)
            self._status = ComponentStatus.DEGRADED
            error_msg = f"Error in {self.name}: {str(e)}"
            self._logger.error(f"[{correlation_id}] 🚨 THINKING FAILURE: {error_msg}")
            self._logger.debug(traceback.format_exc())
            
            # إعادة رد آمن (Fallback) بدلاً من تحطيم الواجهة
            return self._get_fallback_response(prompt, error_msg)

    async def think_async(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        النسخة غير المتزامنة (للمستقبل وللواجهات الحديثة).
        افتراضياً، تستدعي النسخة المتزامنة ما لم يقم الابن بتعديلها.
        """
        # في المستقبل: يمكن استخدام ThreadPoolExecutor هنا
        return self.think(prompt, context)

    # =========================================================================
    # 3. Abstract Methods (ما يجب على الابن كتابته)
    # =========================================================================

    @abstractmethod
    def _execute_reasoning(self, prompt: str, context: Dict) -> str:
        """
        ⚠️ المنطقة المحرمة: يجب تنفيذ هذا الكود في الكلاس الفرعي.
        هنا تضع منطق الذكاء الفعلي (استدعاء API، تحليل بيانات، الخ).
        """
        pass

    # =========================================================================
    # 4. Helper Methods (أدوات مساعدة)
    # =========================================================================

    def _validate_config(self, config: Dict) -> bool:
        """
        دالة اختيارية للتحقق من الإعدادات.
        Override this if you need specific keys.
        """
        return True

    def _get_fallback_response(self, prompt: str, error_msg: str) -> str:
        """
        الرد الاحتياطي في حالة الفشل.
        """
        return f"⚠️ **Analysis Failed**: The agent `{self.name}` encountered an internal error.\n`{error_msg}`"

    def _update_memory(self, user_input: str, agent_output: str):
        """تحديث الذاكرة الداخلية"""
        self._memory.append({"user": user_input, "agent": agent_output})
        # الاحتفاظ بآخر 10 تفاعلات فقط لتوفير الذاكرة
        if len(self._memory) > 10:
            self._memory.pop(0)