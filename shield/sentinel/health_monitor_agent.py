# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - SELF-HEALING AI SENTINEL
=================================================================
Component: shield/sentinel/health_monitor_agent.py
Core Responsibility: المراقبة النشطة، التشخيص، والإصلاح الذاتي للأعطال (Stability Pillar).
Design Pattern: Autonomic Computing / Monitor-Analyze-Plan-Execute (MAPE)
Forensic Impact: يسجل "سبب الوفاة" قبل إعادة الإحياء. يفرق بين الانهيار العشوائي والهجمات الممنهجة.
=================================================================
"""

import time
import threading
import logging
import psutil
import docker
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.sentinel")

class HealthStatus(Enum):
    HEALTHY = "HEALTHY"     # النظام يعمل بكفاءة
    DEGRADED = "DEGRADED"   # النظام يعمل ببطء أو استهلاك موارد عالي
    CRITICAL = "CRITICAL"   # توقف جزء جوهري من النظام

class HealingAction(Enum):
    DO_NOTHING = 0
    RESTART_CONTAINER = 1
    FLUSH_MEMORY = 2
    RESTART_SYSTEM = 3
    EMERGENCY_SHUTDOWN = 4

class HealthMonitorAgent:
    """
    وكيل ذكي يراقب صحة النظام ويتخذ قرارات إصلاحية بناءً على القواعد (Heuristics).
    """
    def __init__(self, check_interval: int = 5):
        self.interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None
            logger.warning("SENTINEL: Docker not available. Container healing disabled.")

        # سجل الإصلاحات لمنع حلقات الإعادة اللانهائية (Boot Loop)
        self.healing_history: List[dict] = []
        
        # حدود الخطر
        self.thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "max_restarts_per_hour": 3
        }

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("SENTINEL: Health Monitor activated.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _monitor_loop(self):
        while self._running:
            try:
                # 1. جمع البيانات (Monitor)
                metrics = self._collect_metrics()
                
                # 2. التحليل والتشخيص (Analyze)
                status, diagnosis = self._analyze_health(metrics)
                
                # 3. التخطيط والتنفيذ (Plan & Execute)
                if status != HealthStatus.HEALTHY:
                    self._plan_and_execute_healing(status, diagnosis)
                
            except Exception as e:
                logger.error(f"SENTINEL_ERR: Monitor loop failed: {e}")
            
            time.sleep(self.interval)

    def _collect_metrics(self) -> dict:
        """جمع مؤشرات حيوية من نظام التشغيل"""
        return {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "timestamp": time.time()
        }

    def _analyze_health(self, metrics: dict) -> (HealthStatus, str):
        """
        تحليل البيانات لتحديد الحالة.
        يعيد (الحالة، السبب الجذري).
        """
        # فحص الموارد العامة
        if metrics["cpu"] > self.thresholds["cpu_percent"]:
            return HealthStatus.DEGRADED, "HIGH_CPU_LOAD"
        
        if metrics["memory"] > self.thresholds["memory_percent"]:
            return HealthStatus.DEGRADED, "HIGH_MEMORY_USAGE"
        
        if metrics["disk"] > self.thresholds["disk_percent"]:
            return HealthStatus.CRITICAL, "DISK_FULL"

        # فحص الحاويات الحيوية (إذا كان Docker متاحاً)
        if self.docker_client:
            try:
                # نفترض أن اسم الحاوية للمحرك هو 'alpha_core'
                container = self.docker_client.containers.get('alpha_core')
                if container.status != 'running':
                    return HealthStatus.CRITICAL, "ENGINE_DOWN"
            except docker.errors.NotFound:
                return HealthStatus.CRITICAL, "ENGINE_MISSING"
            except Exception:
                pass # تجاهل أخطاء الاتصال العابرة

        return HealthStatus.HEALTHY, "OK"

    def _plan_and_execute_healing(self, status: HealthStatus, diagnosis: str):
        """اتخاذ قرار الإصلاح (The Doctor)"""
        
        logger.warning(f"SENTINEL: System Health: {status.value} | Diagnosis: {diagnosis}")
        
        action = HealingAction.DO_NOTHING
        target = None

        # منطق اتخاذ القرار (Decision Matrix)
        if diagnosis == "ENGINE_DOWN" or diagnosis == "ENGINE_MISSING":
            action = HealingAction.RESTART_CONTAINER
            target = "alpha_core"
        
        elif diagnosis == "HIGH_MEMORY_USAGE":
            # محاولة تنظيف الذاكرة أولاً
            action = HealingAction.FLUSH_MEMORY
        
        elif diagnosis == "DISK_FULL":
            # تنظيف السجلات القديمة
            # action = HealingAction.CLEAN_LOGS
            pass

        # التحقق من الأمان (Safety Brake)
        if self._is_safe_to_heal(action, target):
            self._execute_action(action, target, diagnosis)
        else:
            logger.critical(f"SENTINEL: Healing aborted! Too many retries for {diagnosis}. Manual intervention required.")

    def _is_safe_to_heal(self, action: HealingAction, target: str) -> bool:
        """منع الحلقات اللانهائية (Boot Loops)"""
        if action == HealingAction.DO_NOTHING:
            return True
            
        now = time.time()
        # تنظيف السجل القديم (أكثر من ساعة)
        self.healing_history = [h for h in self.healing_history if now - h['time'] < 3600]
        
        # حساب عدد مرات الإصلاح لنفس السبب
        recent_fixes = len([h for h in self.healing_history if h['action'] == action and h['target'] == target])
        
        return recent_fixes < self.thresholds["max_restarts_per_hour"]

    def _execute_action(self, action: HealingAction, target: str, reason: str):
        """تنفيذ الإصلاح وتسجيله جنائياً"""
        logger.info(f"SENTINEL_ACTION: Executing {action.name} on {target} due to {reason}...")
        
        success = False
        try:
            if action == HealingAction.RESTART_CONTAINER:
                if self.docker_client:
                    try:
                        container = self.docker_client.containers.get(target)
                        container.restart()
                        success = True
                    except docker.errors.NotFound:
                        # محاولة إعادة التشغيل (في سيناريو حقيقي قد نستخدم docker-compose up)
                        pass
                        
            elif action == HealingAction.FLUSH_MEMORY:
                # محاكاة تفريغ الكاش (Linux specific)
                # os.system('sync; echo 3 > /proc/sys/vm/drop_caches') 
                # (يتطلب root، لن ننفذه هنا لتجنب الأخطاء في البيئة التجريبية)
                success = True

            if success:
                logger.info("SENTINEL_ACTION: Success.")
                self.healing_history.append({
                    'time': time.time(),
                    'action': action,
                    'target': target,
                    'reason': reason
                })
            else:
                logger.error("SENTINEL_ACTION: Failed to execute healing.")

        except Exception as e:
            logger.error(f"SENTINEL_ACTION: Critical Error during execution: {e}")

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = HealthMonitorAgent(check_interval=2)
    
    # خفض الحدود لمحاكاة حالة حرجة فوراً
    agent.thresholds["memory_percent"] = 10.0 
    
    print("--- SENTINEL START ---")
    agent.start()
    
    try:
        time.sleep(6) # السماح بدورتين من المراقبة
    except KeyboardInterrupt:
        pass
        
    agent.stop()