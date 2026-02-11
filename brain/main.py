# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - BRAIN ORCHESTRATOR (THE EXECUTIVE)
====================================================
Path: alpha_project/brain/main.py
Role: "المدير التنفيذي" - لا يقوم بالتفكير بنفسه، بل يدير دورة العمل بين العقول ومصادر البيانات.
Status: RE-ENGINEERED (Compatible with Dynamic Loader)

Forensic Features:
  1. **Lifecycle Management**: يضمن أن دورة التحليل (جمع -> تفكير -> قرار) تتم بترتيب زمني صارم.
  2. **Dependency Verification**: يرفض العمل إذا لم يجد "محلل سوق" و "مجمع بيانات" مسجلين في النظام.
  3. **No-Mock Policy**: إذا فشل جزء من الدورة، يوقف الدورة بالكامل ويرفع تقرير خطأ حقيقي.
  4. **Registry Integration**: لا ينشئ كائنات جديدة، بل يسحب الكائنات الحية من السجل المركزي.

Author: Alpha Architect (AI)
"""

import logging
import time
import threading
from typing import Dict, List, Optional

# استيراد النواة والقوانين
from alpha_project.core.registry import registry, register_component
from alpha_project.core.interfaces import ISovereignComponent, ComponentStatus, IReasoningUnit, IDataCollector

logger = logging.getLogger("Alpha.Brain.Orchestrator")

@register_component(name="brain.orchestrator", category="system", is_critical=True)
class BrainOrchestrator(ISovereignComponent):
    """
    المايسترو الذي يربط الرؤية (Data) بالتفكير (Brain).
    هذا الكلاس هو المسؤول عن تشغيل "دورات السوق" (Market Cycles).
    """

    def __init__(self):
        self._status = ComponentStatus.STARTING
        self._active_agents: List[IReasoningUnit] = []
        self._active_collectors: List[IDataCollector] = []
        self._cycle_thread = None
        self._keep_running = False
        
        # إعدادات الدورة (تأتي من Config لاحقاً)
        self.cycle_interval_seconds = 60 

    # =========================================================================
    # 1. System Contract Implementation
    # =========================================================================

    @property
    def name(self) -> str:
        return "brain.orchestrator"

    def initialize(self, config: Dict) -> bool:
        """
        مرحلة التجميع. البحث عن الفريق في السجل.
        """
        logger.info("🎼 Orchestrator initializing. Assembling the team...")
        
        # محاولة العثور على المكونات التي حملها الـ Loader مسبقاً
        # ملاحظة: قد لا تكون كل المكونات جاهزة فوراً، لذا الفحص الحقيقي يتم عند التشغيل
        self._status = ComponentStatus.HEALTHY
        return True

    def shutdown(self) -> None:
        """إيقاف الدورات"""
        self._keep_running = False
        if self._cycle_thread:
            self._cycle_thread.join(timeout=2)
        self._status = ComponentStatus.STOPPED
        logger.info("🎼 Orchestrator stopped.")

    def health_check(self) -> ComponentStatus:
        """
        فحص صحة الفريق بالكامل.
        إذا كان أي عضو في الفريق مفقوداً أو معطلاً، فالأوركسترا في خطر.
        """
        # إعادة مسح السجل للتأكد من وجود الأعضاء
        brains = registry.get_by_category("brain")
        data = registry.get_by_category("data")
        
        if not brains or not data:
            return ComponentStatus.FAILED
            
        return self._status

    # =========================================================================
    # 2. Market Cycle Management (إدارة العمليات)
    # =========================================================================

    def start_autonomous_mode(self):
        """
        تشغيل الوضع المستقل (Autonomous Mode).
        يقوم بتشغيل خيط خلفي ينفذ التحليل دورياً.
        """
        if self._keep_running:
            logger.warning("⚠️ Autonomous mode already running.")
            return

        logger.info("🚀 Starting Autonomous Market Analysis Cycles...")
        self._keep_running = True
        self._cycle_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._cycle_thread.start()

    def _run_loop(self):
        """الحلقة الرئيسية للتداول الآلي"""
        while self._keep_running:
            try:
                self.execute_market_cycle()
            except Exception as e:
                logger.critical(f"💥 Critical Failure in Market Cycle: {e}")
                # لا نوقف الحلقة، بل ننتظر ونحاول مجدداً (Resilience)
            
            time.sleep(self.cycle_interval_seconds)

    def execute_market_cycle(self):
        """
        تنفيذ دورة سوق واحدة:
        1. جمع البيانات (من المصدر الحقيقي).
        2. التحليل (بواسطة العقل الحقيقي).
        3. القرار (بدون تنفيذ وهمي).
        """
        logger.info("🔄 --- New Market Cycle Started ---")
        
        # 1. مرحلة التجميع (Collection Phase)
        # -----------------------------------
        # نطلب أفضل مجمع بيانات متاح
        collector_map = registry.get_by_category("data")
        if not collector_map:
            logger.error("❌ No Data Collectors found. Aborting cycle.")
            return # توقف حقيقي، لا بيانات وهمية

        # نفترض أننا نستخدم أول مجمع متاح (يمكن تحسين المنطق لاحقاً)
        # في بيئة حقيقية قد نحدد 'binance_collector' بالاسم
        collector = list(collector_map.values())[0]
        
        # جلب بيانات حقيقية
        market_data = collector.fetch_snapshot("BTC/USDT")
        
        # التحقق من صحة البيانات (Forensic Check)
        if not market_data or "error" in market_data:
            logger.error(f"❌ Data fetch failed from {collector.name}. Cycle aborted.")
            return

        logger.info(f"📊 Market Data Received: BTC Price = {market_data.get('price', 'N/A')}")

        # 2. مرحلة التفكير (Reasoning Phase)
        # ----------------------------------
        brain_map = registry.get_by_category("brain")
        if not brain_map:
            logger.error("❌ No Brains found. Aborting cycle.")
            return

        # نختار أفضل عقل (يمكن استخدام Router هنا، لكن للتوضيح نستخدم المباشر)
        primary_brain = list(brain_map.values())[0]
        
        analysis_prompt = f"Analyze this market data for scalping opportunity: {market_data}"
        
        logger.info(f"🧠 Consultng {primary_brain.name}...")
        decision = primary_brain.think(analysis_prompt)
        
        # 3. مرحلة التنفيذ (Execution Phase)
        # ----------------------------------
        # حالياً نقوم بالطباعة فقط، مستقبلاً سنرسل لمنفذ الأوامر
        if "⚠️" in decision:
            logger.warning(f"⚠️ Brain was unsure or errored: {decision}")
        else:
            logger.info(f"💡 Strategy Signal: {decision[:100]}...")

        logger.info("✅ Cycle Complete.")