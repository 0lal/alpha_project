# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - AGENT CHAOS INJECTOR
=================================================================
Component: sim_lab/chaos/agent_chaos.py
Core Responsibility: تخريب المكونات الداخلية واختبار مناعة النظام (Stability Pillar).
Design Pattern: Chaos Monkey / Fault Injection
Forensic Impact: يولد "مسرح جريمة" مصطنع للتأكد من أن أدوات التحقيق الجنائي (Incident Report) تعمل بدقة.
=================================================================
"""

import random
import time
import logging
import threading
from enum import Enum
from typing import List, Dict, Callable

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.chaos.agent")

class ChaosType(Enum):
    CRASH_PROCESS = "CRASH"       # قتل العملية فوراً
    FREEZE_THREAD = "FREEZE"      # تجميد التنفيذ (Deadlock Simulation)
    MEMORY_LEAK = "MEM_LEAK"      # استهلاك ذاكرة تدريجي
    DATA_POISON = "POISON"        # إرجاع قيم خاطئة
    CPU_SPIKE = "CPU_BURN"        # استهلاك 100% من المعالج

class AgentChaos:
    def __init__(self, target_agents: List[str]):
        """
        target_agents: قائمة بأسماء الوكلاء أو المكونات المستهدفة (IDs)
        """
        self.targets = target_agents
        self.is_active = True
        self.chaos_history = []

    def unleash_hell(self, intensity: float = 0.1):
        """
        إطلاق الفوضى العشوائية.
        intensity: احتمالية حدوث كارثة في كل دورة (0.0 - 1.0)
        """
        if not self.is_active: return

        if random.random() < intensity:
            target = random.choice(self.targets)
            chaos_type = random.choice(list(ChaosType))
            
            logger.warning(f"CHAOS_AGENT: Targeting {target} with {chaos_type.name}...")
            self._execute_chaos(target, chaos_type)

    def _execute_chaos(self, target_id: str, chaos_type: ChaosType):
        """تنفيذ التخريب الفعلي"""
        try:
            if chaos_type == ChaosType.CRASH_PROCESS:
                # محاكاة: في الواقع سنقوم بـ docker.kill(target_id)
                logger.critical(f"CHAOS_ACTION: {target_id} process TERMINATED (Simulated SIGKILL).")
                # self._kill_container(target_id) 

            elif chaos_type == ChaosType.FREEZE_THREAD:
                # محاكاة: الوكيل يتوقف عن الاستجابة لـ Heartbeat
                logger.error(f"CHAOS_ACTION: {target_id} is FROZEN (Simulating Deadlock).")
                # block_thread(target_id)

            elif chaos_type == ChaosType.DATA_POISON:
                # محاكاة: الوكيل يرسل سعراً يساوي -999
                logger.warning(f"CHAOS_ACTION: {target_id} injected POISONED DATA into the stream.")
                # inject_bad_data(target_id)

            elif chaos_type == ChaosType.MEMORY_LEAK:
                logger.warning(f"CHAOS_ACTION: {target_id} consuming abnormal RAM (Leak Simulation).")
            
            # تسجيل الحدث للتحقق لاحقاً هل اكتشفه النظام أم لا
            self.chaos_history.append({
                "timestamp": time.time(),
                "target": target_id,
                "type": chaos_type.name
            })

        except Exception as e:
            logger.error(f"CHAOS_ERR: Failed to execute chaos: {e}")

    # =========================================================
    # أدوات مساعدة لمحاكاة الأعطال برمجياً (للاستخدام داخل الوكلاء)
    # =========================================================
    
    @staticmethod
    def simulate_cpu_spike(duration_sec: float = 5.0):
        """حرق دورات المعالج لمحاكاة حمل ثقيل"""
        logger.info(f"CHAOS: Burning CPU for {duration_sec}s...")
        end_time = time.time() + duration_sec
        while time.time() < end_time:
            _ = 999999 * 999999 # عملية حسابية ثقيلة

    @staticmethod
    def simulate_memory_leak(mb_size: int = 100):
        """تخصيص ذاكرة وعدم تحريرها"""
        logger.info(f"CHAOS: Leaking {mb_size}MB of RAM...")
        # إنشاء مصفوفة ضخمة وعدم حذفها
        leak = bytearray(mb_size * 1024 * 1024) 
        return leak # إرجاعها للمتصل لكي لا يجمعها الـ Garbage Collector

# =================================================================
# اختبار المحاكاة (Self-Test)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    targets = ["StrategyAgent_BTC", "RiskManager", "ExecutionAlgo"]
    chaos_engine = AgentChaos(targets)

    print("--- STARTING CHAOS SIMULATION ---")
    
    # حلقة تجريبية
    for i in range(5):
        print(f"\n[Tick {i+1}] Normal Operation...")
        time.sleep(1)
        
        # محاولة حقن الفوضى باحتمالية 50%
        chaos_engine.unleash_hell(intensity=0.5)

    print("\n--- CHAOS REPORT ---")
    for event in chaos_engine.chaos_history:
        print(f"Time: {event['timestamp']:.2f} | Target: {event['target']} | Event: {event['type']}")
    
    print("\nNOTE: In a real run, 'SelfHealingLogic' should have detected and fixed these events.")