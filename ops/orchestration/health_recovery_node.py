# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - SELF-HEALING RECOVERY NODE
===================================================
Component Name: ops/orchestration/health_recovery_node.py
Core Responsibility: استبدال أو إصلاح المكونات التالفة في الذاكرة الحية (Pillar: Stability).
Creation Date: 2026-02-03
Version: 1.0.0 (Phoenix Protocol)
Author: Chief System Architect

Forensic Note:
هذا المكون يطبق نمط "Circuit Breaker".
- إذا فشل مكون 5 مرات متتالية، يتم "قطع الدائرة" (Open Circuit) لمنع النظام من تضييع الموارد في محاولة إصلاح شيء ميت.
- يتم تسجيل كل عملية "شفاء" كحدث جنائي لمعرفة أي الأجزاء في النظام هي الأضعف.
"""

import time
import logging
import threading
import traceback
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# إعداد السجلات
logger = logging.getLogger("AlphaHealer")

class CircuitState(Enum):
    CLOSED = "CLOSED"   # كل شيء يعمل (الدائرة مغلقة وتوصل التيار)
    OPEN = "OPEN"       # توقف عن المحاولة (الدائرة مفتوحة لحماية النظام)
    HALF_OPEN = "HALF"  # محاولة حذرة للعودة

@dataclass
class ComponentHealth:
    """السجل الطبي للمكون."""
    name: str
    failure_count: int = 0
    last_failure_time: float = 0.0
    state: CircuitState = CircuitState.CLOSED
    recovery_strategy: Optional[Callable] = None # الدالة التي تصلح المكون
    max_retries: int = 5
    reset_timeout: int = 60 # ثانية

class HealthRecoveryNode:
    """
    عقدة الاستشفاء.
    تحتفظ بـ "سجل طبي" لكل مكون حيوي، وتتدخل عند اللزوم.
    """

    def __init__(self):
        self._registry: Dict[str, ComponentHealth] = {}
        self._lock = threading.Lock()

    def register_component(self, name: str, recovery_func: Callable, max_retries: int = 5):
        """
        تسجيل مكون للمراقبة وتحديد كيفية إصلاحه.
        :param recovery_func: دالة تقوم بإعادة تهيئة المكون (مثلاً: db.connect())
        """
        with self._lock:
            self._registry[name] = ComponentHealth(
                name=name,
                recovery_strategy=recovery_func,
                max_retries=max_retries
            )
        logger.info(f"Recovery Procedure Registered for: {name}")

    def report_failure(self, name: str, error: Exception) -> bool:
        """
        الإبلاغ عن فشل مكون وطلب التدخل الفوري.
        :return: True إذا نجح الإصلاح، False إذا فشل أو الدائرة مفتوحة.
        """
        with self._lock:
            if name not in self._registry:
                logger.error(f"Unregistered component failed: {name}. Cannot heal.")
                return False
            
            record = self._registry[name]
            current_time = time.time()

            # منطق قاطع الدائرة (Circuit Breaker Logic)
            if record.state == CircuitState.OPEN:
                # هل مرت فترة التبريد (Cooldown)؟
                if current_time - record.last_failure_time > record.reset_timeout:
                    logger.info(f"Circuit Breaker for {name} is HALF-OPEN. Attempting recovery...")
                    record.state = CircuitState.HALF_OPEN
                else:
                    logger.warning(f"Circuit Breaker for {name} is OPEN. Recovery skipped.")
                    return False

            # تحديث السجلات
            record.failure_count += 1
            record.last_failure_time = current_time
            
            logger.warning(f"HEALING INITIATED: {name} (Failures: {record.failure_count}/{record.max_retries}) | Error: {error}")

            # محاولة الإصلاح
            if record.failure_count > record.max_retries and record.state != CircuitState.HALF_OPEN:
                logger.critical(f"MAX RETRIES EXCEEDED for {name}. Opening Circuit Breaker.")
                record.state = CircuitState.OPEN
                return False

            return self._execute_recovery(record)

    def _execute_recovery(self, record: ComponentHealth) -> bool:
        """
        تنفيذ استراتيجية الإصلاح في بيئة آمنة.
        """
        try:
            if not record.recovery_strategy:
                return False
                
            # تنفيذ دالة الإصلاح
            logger.info(f"Applying surgical fix to {record.name}...")
            record.recovery_strategy()
            
            # إذا نجحنا، نصفر العدادات
            logger.info(f"SUCCESS: {record.name} has been recovered.")
            record.failure_count = 0
            record.state = CircuitState.CLOSED
            return True
            
        except Exception as e:
            logger.error(f"RECOVERY FAILED for {record.name}: {e}")
            # في حالة فشل الإصلاح نفسه، نزيد العداد ونبقي الدائرة مفتوحة إذا لزم الأمر
            return False

    def get_system_health_status(self) -> Dict[str, str]:
        """تقرير الحالة لجميع المكونات (للوحة القيادة)."""
        with self._lock:
            return {
                name: rec.state.value 
                for name, rec in self._registry.items()
            }

# --- Unit Test ---
if __name__ == "__main__":
    healer = HealthRecoveryNode()
    
    # 1. محاكاة مكون (اتصال قاعدة بيانات)
    class DatabaseConnector:
        def __init__(self):
            self.connected = False
        
        def connect(self):
            print("DB: Connecting...")
            # محاكاة فشل عشوائي
            if time.time() % 2 > 1.5: 
                raise ConnectionError("Network Unreachable")
            self.connected = True
            print("DB: Connected!")

    db = DatabaseConnector()

    # 2. تسجيل استراتيجية الإصلاح
    # الاستراتيجية هي ببساطة محاولة الاتصال مرة أخرى
    healer.register_component("PostgreSQL", db.connect, max_retries=3)

    print("--- Simulating Failures ---")
    
    # 3. محاكاة سلسلة من الفشل
    for i in range(5):
        try:
            print(f"\n[Attempt {i+1}] Using DB...")
            if not db.connected:
                raise TimeoutError("DB Connection Lost")
        except Exception as e:
            # هنا يتدخل المعالج
            success = healer.report_failure("PostgreSQL", e)
            if not success:
                print(">>> System: Could not recover DB. Waiting...")
                time.sleep(1)
            else:
                # إذا نجح الإصلاح، نتظاهر بأن الاتصال انقطع مرة أخرى للتجربة
                db.connected = False 

    print("\n--- Final Health Status ---")
    print(healer.get_system_health_status())