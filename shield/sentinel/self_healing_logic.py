# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVANCED SELF-HEALING LOGIC
=================================================================
Component: shield/sentinel/self_healing_logic.py
Core Responsibility: اتخاذ قرارات تكتيكية لإصلاح أو عزل المكونات المعطوبة (Stability Pillar).
Design Pattern: Strategy Pattern / Circuit Breaker
Forensic Impact: يوفر سجلاً دقيقاً للإجراءات التصحيحية، مما يسمح بمعرفة ما إذا كان النظام قد أصلح نفسه أم أن المشكلة تفاقمت.
=================================================================
"""

import docker
import logging
import time
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.healing")

class HealingStrategy(Enum):
    IGNORE = "IGNORE"               # تجاهل (خطأ عابر)
    RESTART_GRACEFUL = "RESTART_GRACEFUL" # طلب توقف مهذب ثم بدء
    RESTART_FORCE = "RESTART_FORCE"       # قتل فوري ثم بدء (للأنظمة العالقة)
    ISOLATE_NETWORK = "ISOLATE_NETWORK"   # قطع الشبكة (للاشتباه الأمني)
    TERMINATE = "TERMINATE"               # إيقاف نهائي (للفشل المتكرر)

@dataclass
class IncidentHistory:
    """سجل الحوادث لكل حاوية لمنع التكرار اللانهائي"""
    timestamps: List[float] = field(default_factory=list)
    last_action: Optional[HealingStrategy] = None

class SelfHealingLogic:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"HEALING_INIT_ERR: Could not connect to Docker: {e}")
            self.client = None

        # الذاكرة التاريخية للأعطال
        self.incident_ledger: Dict[str, IncidentHistory] = {}
        
        # الإعدادات
        self.FLAP_THRESHOLD = 5       # 5 أعطال
        self.FLAP_WINDOW_SEC = 60     # في الدقيقة الواحدة يعتبر Flapping
        self.ISOLATION_ZONE = "alpha_quarantine_net" # شبكة معزولة

    def resolve_anomaly(self, container_id: str, anomaly_type: str) -> bool:
        """
        نقطة الدخول الرئيسية: استلم المشكلة، قرر الحل، نفذه.
        """
        if not self.client:
            return False

        container_short = container_id[:12]
        logger.info(f"HEALING: Analyzing anomaly '{anomaly_type}' for {container_short}...")

        # 1. التحقق من تاريخ المريض (Anti-Flapping Check)
        if self._is_flapping(container_id):
            logger.critical(f"HEALING_ABORT: Container {container_short} is FLAPPING (restarting too fast). Escalating to TERMINATE.")
            return self._execute_strategy(container_id, HealingStrategy.TERMINATE)

        # 2. اختيار الاستراتيجية المناسبة
        strategy = self._decide_strategy(anomaly_type)
        
        if strategy == HealingStrategy.IGNORE:
            logger.info(f"HEALING: Decided to IGNORE {anomaly_type} for now.")
            return True

        # 3. تنفيذ العلاج
        return self._execute_strategy(container_id, strategy)

    def _decide_strategy(self, anomaly_type: str) -> HealingStrategy:
        """جدول القرارات (Decision Matrix)"""
        if anomaly_type == "UNRESPONSIVE" or anomaly_type == "DEADLOCK":
            return HealingStrategy.RESTART_FORCE
        
        elif anomaly_type == "HIGH_MEMORY" or anomaly_type == "SLOW_RESPONSE":
            return HealingStrategy.RESTART_GRACEFUL
        
        elif anomaly_type == "SUSPICIOUS_NETWORK" or anomaly_type == "UNAUTHORIZED_ACCESS":
            # في الحالات الأمنية، لا نعيد التشغيل (لأن ذلك يمسح الأدلة من الذاكرة)
            # بل نعزل الحاوية فوراً
            return HealingStrategy.ISOLATE_NETWORK
        
        elif anomaly_type == "CRASH_LOOP":
            return HealingStrategy.TERMINATE

        return HealingStrategy.IGNORE

    def _execute_strategy(self, container_id: str, strategy: HealingStrategy) -> bool:
        """تنفيذ العملية الجراحية"""
        try:
            container = self.client.containers.get(container_id)
            container_name = container.name

            logger.warning(f"HEALING_EXEC: Executing {strategy.value} on {container_name} ({container_id[:12]})...")

            if strategy == HealingStrategy.RESTART_GRACEFUL:
                container.restart(timeout=10) # 10 ثواني للإغلاق المهذب
            
            elif strategy == HealingStrategy.RESTART_FORCE:
                container.kill()
                container.start()
            
            elif strategy == HealingStrategy.ISOLATE_NETWORK:
                # فصل عن جميع الشبكات
                for net_name in container.attrs['NetworkSettings']['Networks']:
                    self.client.networks.list(names=[net_name])[0].disconnect(container)
                logger.critical(f"HEALING_SEC: {container_name} has been ISOLATED from the network.")
                # يمكن هنا نقلها لشبكة الحجر الصحي إذا كانت موجودة
            
            elif strategy == HealingStrategy.TERMINATE:
                container.stop()
                # لا نحذفها (remove) لنسمح بالتحليل الجنائي لاحقاً
                logger.critical(f"HEALING_FINAL: {container_name} has been TERMINATED.")

            # تسجيل الحدث في السجل
            self._record_incident(container_id, strategy)
            return True

        except docker.errors.NotFound:
            logger.error(f"HEALING_ERR: Container {container_id} vanished before healing.")
            return False
        except Exception as e:
            logger.error(f"HEALING_ERR: Failed to execute {strategy}: {e}")
            return False

    def _record_incident(self, container_id: str, strategy: HealingStrategy):
        """تحديث السجل الطبي"""
        now = time.time()
        if container_id not in self.incident_ledger:
            self.incident_ledger[container_id] = IncidentHistory()
        
        history = self.incident_ledger[container_id]
        history.timestamps.append(now)
        history.last_action = strategy
        
        # تنظيف السجلات القديمة (أكثر من ساعة)
        history.timestamps = [t for t in history.timestamps if now - t < 3600]

    def _is_flapping(self, container_id: str) -> bool:
        """
        هل تحاول الحاوية الموت والإحياء بشكل متكرر؟
        (Definition of Insanity Check)
        """
        if container_id not in self.incident_ledger:
            return False
        
        history = self.incident_ledger[container_id]
        now = time.time()
        
        # نعد الحوادث في النافذة الزمنية المحددة (مثلاً آخر دقيقة)
        recent_incidents = [t for t in history.timestamps if now - t < self.FLAP_WINDOW_SEC]
        
        if len(recent_incidents) >= self.FLAP_THRESHOLD:
            return True
        
        return False

# =================================================================
# مثال للمحاكاة (Simulation)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # محاكاة منطق الشفاء
    healer = SelfHealingLogic()
    
    # محاكاة ID وهمي (لن يعمل مع Docker الحقيقي إلا إذا كان الـ ID صحيحاً)
    fake_id = "a1b2c3d4e5f6"
    
    print("--- SCENARIO 1: Memory Leak ---")
    healer.resolve_anomaly(fake_id, "HIGH_MEMORY")
    
    print("\n--- SCENARIO 2: Malware Detection ---")
    healer.resolve_anomaly(fake_id, "SUSPICIOUS_NETWORK")
    
    print("\n--- SCENARIO 3: Flapping Service ---")
    # نسجل 5 حوادث سريعة يدوياً
    for _ in range(5):
        healer._record_incident(fake_id, HealingStrategy.RESTART_FORCE)
    
    # المحاولة السادسة يجب أن تؤدي للإغلاق النهائي
    healer.resolve_anomaly(fake_id, "UNRESPONSIVE")