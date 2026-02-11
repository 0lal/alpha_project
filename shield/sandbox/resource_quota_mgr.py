# DoS Protection

# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - RESOURCE QUOTA MANAGER (DoS PROTECTION)
=================================================================
Component: shield/sandbox/resource_quota_mgr.py
Core Responsibility: المراقبة النشطة واحتواء استهلاك الموارد (Stability Pillar).
Design Pattern: Watchdog / Circuit Breaker
Forensic Impact: يسجل "لحظة الموت" للحاوية وسبب الإغلاق (OOM, CPU Hog)، مما يبرئ النظام من تهمة الفشل العشوائي.
=================================================================
"""

import threading
import time
import logging
import docker
from dataclasses import dataclass
from typing import Dict, Optional, Callable

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.quota")

@dataclass
class QuotaLimits:
    max_cpu_percent: float = 80.0    # الحد الأقصى للمعالج (80% من النواة المخصصة)
    max_memory_mb: int = 512         # الحد الأقصى للذاكرة بالميجابايت
    max_pids: int = 50               # الحد الأقصى للعمليات (لمنع Fork Bombs)
    violation_tolerance: int = 5     # عدد المرات المسموح فيها بتجاوز الحد قبل القتل (Grace Period)

class ResourceQuotaManager:
    def __init__(self, docker_client: docker.DockerClient):
        self.client = docker_client
        self.monitored_containers: Dict[str, QuotaLimits] = {}
        self.violations: Dict[str, int] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # دالة استدعاء عند القتل (Callback) - لإبلاغ الدماغ
        self.on_kill_callback: Optional[Callable[[str, str], None]] = None

    def register_container(self, container_id: str, limits: QuotaLimits):
        """بدء مراقبة حاوية جديدة"""
        with self._lock:
            self.monitored_containers[container_id] = limits
            self.violations[container_id] = 0
            logger.info(f"QUOTA_MGR: Monitoring started for {container_id[:12]}")

    def unregister_container(self, container_id: str):
        """إيقاف مراقبة حاوية"""
        with self._lock:
            if container_id in self.monitored_containers:
                del self.monitored_containers[container_id]
            if container_id in self.violations:
                del self.violations[container_id]

    def start_watchdog(self, interval: float = 2.0):
        """تشغيل كلب الحراسة في خيط خلفي"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.thread.start()
        logger.info("QUOTA_MGR: Watchdog thread started.")

    def stop_watchdog(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor_loop(self, interval: float):
        """الحلقة الرئيسية للمراقبة"""
        while self.running:
            start_time = time.time()
            
            # نأخذ نسخة لتجنب مشاكل التزامن أثناء التعديل
            with self._lock:
                target_ids = list(self.monitored_containers.keys())

            for cid in target_ids:
                self._check_container(cid)

            # الحفاظ على توقيت ثابت للدورة
            elapsed = time.time() - start_time
            sleep_time = max(0.1, interval - elapsed)
            time.sleep(sleep_time)

    def _check_container(self, container_id: str):
        """فحص حاوية واحدة"""
        try:
            limits = self.monitored_containers.get(container_id)
            if not limits: return

            container = self.client.containers.get(container_id)
            
            # الحصول على الإحصائيات (بدون Stream لأخذ لقطة لحظية)
            stats = container.stats(stream=False)
            
            # 1. حساب استهلاك المعالج
            cpu_percent = self._calculate_cpu_percent(stats)
            
            # 2. حساب استهلاك الذاكرة
            mem_usage_mb = stats['memory_stats'].get('usage', 0) / (1024 * 1024)
            
            # 3. التحقق من الحدود
            is_violation = False
            violation_reason = ""

            if cpu_percent > limits.max_cpu_percent:
                is_violation = True
                violation_reason = f"CPU Limit Exceeded ({cpu_percent:.2f}% > {limits.max_cpu_percent}%)"
            
            elif mem_usage_mb > limits.max_memory_mb:
                is_violation = True
                violation_reason = f"Memory Limit Exceeded ({mem_usage_mb:.2f}MB > {limits.max_memory_mb}MB)"

            # التعامل مع المخالفات
            if is_violation:
                self.violations[container_id] += 1
                logger.warning(f"QUOTA_WARN: [{container_id[:12]}] {violation_reason} | Strike {self.violations[container_id]}/{limits.violation_tolerance}")
                
                if self.violations[container_id] >= limits.violation_tolerance:
                    self._terminate_offender(container, violation_reason)
            else:
                # تقليل المخالفات تدريجياً (Decay) إذا عاد السلوك طبيعياً
                if self.violations[container_id] > 0:
                    self.violations[container_id] -= 1

        except docker.errors.NotFound:
            # الحاوية ماتت أو اختفت، نتوقف عن مراقبتها
            self.unregister_container(container_id)
        except Exception as e:
            logger.error(f"QUOTA_ERR: Failed to check {container_id[:12]}: {e}")

    def _terminate_offender(self, container, reason: str):
        """تنفيذ حكم الإعدام (Kill Switch)"""
        try:
            logger.critical(f"QUOTA_KILL: Terminating {container.short_id} due to: {reason}")
            container.kill()
            
            # إزالة من المراقبة
            self.unregister_container(container.id)
            
            # إبلاغ النظام
            if self.on_kill_callback:
                self.on_kill_callback(container.id, reason)
                
        except Exception as e:
            logger.error(f"QUOTA_ERR: Failed to kill container {container.short_id}: {e}")

    def _calculate_cpu_percent(self, stats) -> float:
        """
        حساب نسبة المعالج بدقة بناءً على معادلات Docker الرسمية.
        Docker stats returns raw counters, we need to calculate deltas.
        """
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                        stats['precpu_stats']['cpu_usage']['total_usage']
            
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                           stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0 and cpu_delta > 0:
                # عدد الأنوية المتاحة للحاوية
                online_cpus = stats['cpu_stats'].get('online_cpus', 1) or len(stats['cpu_stats']['cpu_usage']['percpu_usage'])
                return (cpu_delta / system_delta) * online_cpus * 100.0
            return 0.0
        except KeyError:
            return 0.0