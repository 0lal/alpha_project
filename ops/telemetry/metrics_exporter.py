# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - METRICS EXPORTER
=========================================
Component Name: ops/telemetry/metrics_exporter.py
Core Responsibility: تصدير بيانات الأداء والإحصائيات الحيوية للواجهة (Pillar: Explainability).
Creation Date: 2026-02-03
Version: 1.0.0 (Telemetry Bridge Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون هو المسؤول عن "الشفافية اللحظية".
في التحقيقات، إذا ادعى المشغل أن النظام كان "مجمداً"، نراجع مخرجات هذا المصدر.
إذا توقف المصدر عن إرسال "Heartbeat" لمدة 5 ثوانٍ، فهذا يعني موت العملية (Process Death).
"""

import json
import time
import logging
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

# إعداد السجلات
logger = logging.getLogger("AlphaExporter")

@dataclass
class SystemSnapshot:
    """
    اللقطة الكاملة لحالة النظام في لحظة معينة.
    يتم إرسال هذا الكائن (بصيغة JSON) إلى Flutter لرسم الشاشة.
    """
    timestamp: float
    session_id: str
    
    # المؤشرات الحيوية
    hardware: Dict[str, Any] = field(default_factory=dict) # CPU, RAM, Temp
    network: Dict[str, Any] = field(default_factory=dict)  # Latency, Jitter
    
    # مؤشرات الأداء المالي
    portfolio: Dict[str, Any] = field(default_factory=dict) # Balance, PnL
    active_strategies: int = 0
    orders_per_second: float = 0.0
    
    # الحالة العامة
    system_status: str = "IDLE" # BOOTING, ACTIVE, DEFENSE_MODE, HALTED

class MetricsExporter:
    """
    فئة المصدر (Exporter).
    تعمل بنمط (Publisher) حيث تجمع البيانات من عدة مصادر وتنشرها عبر قناة موحدة.
    """

    def __init__(self, session_id: str = "SESSION_001"):
        self.session_id = session_id
        self._lock = threading.Lock()
        
        # مخزن مؤقت للمقاييس الحالية
        self._current_metrics: Dict[str, Any] = {
            "hardware": {},
            "network": {},
            "portfolio": {},
            "status": "BOOTING"
        }
        
        # عداد الطلبات لحساب TPS (Transactions Per Second)
        self._transaction_counter = 0
        self._last_tps_check = time.time()

    def update_metric(self, category: str, data: Dict[str, Any]):
        """
        تحديث فئة معينة من المقاييس (Thread-Safe).
        يتم استدعاؤها بواسطة hardware_svc أو network_probe.
        """
        with self._lock:
            if category in self._current_metrics:
                # دمج البيانات الجديدة مع القديمة
                self._current_metrics[category].update(data)
            else:
                self._current_metrics[category] = data

    def increment_transaction_count(self):
        """زيادة عداد الصفقات لحساب السرعة."""
        with self._lock:
            self._transaction_counter += 1

    def _calculate_tps(self) -> float:
        """حساب عدد الصفقات في الثانية وتصفير العداد."""
        now = time.time()
        with self._lock:
            elapsed = now - self._last_tps_check
            if elapsed == 0: return 0.0
            
            tps = self._transaction_counter / elapsed
            # إعادة تعيين العداد للفترة القادمة
            self._transaction_counter = 0
            self._last_tps_check = now
            return round(tps, 2)

    def generate_snapshot_json(self) -> str:
        """
        توليد الحزمة النهائية (JSON Payload) لإرسالها إلى Flutter.
        """
        try:
            # تجهيز اللقطة
            snapshot = SystemSnapshot(
                timestamp=time.time(),
                session_id=self.session_id,
                hardware=self._current_metrics.get("hardware", {}),
                network=self._current_metrics.get("network", {}),
                portfolio=self._current_metrics.get("portfolio", {}),
                active_strategies=self._current_metrics.get("portfolio", {}).get("active_count", 0),
                orders_per_second=self._calculate_tps(),
                system_status=self._current_metrics.get("status", "UNKNOWN")
            )
            
            # تحويل إلى JSON
            return json.dumps(asdict(snapshot))
            
        except Exception as e:
            logger.error(f"Failed to generate metrics snapshot: {e}")
            return "{}"

    def export_heartbeat(self) -> Dict[str, Any]:
        """
        نبضة حياة خفيفة جداً (Ping) للتأكد من أن النظام حي.
        """
        return {
            "type": "HEARTBEAT",
            "time": time.time(),
            "status": self._current_metrics.get("status", "UNKNOWN")
        }

# --- Unit Test ---
if __name__ == "__main__":
    exporter = MetricsExporter("TEST_SESSION_X")
    
    # 1. محاكاة وصول بيانات من الهاردوير
    exporter.update_metric("hardware", {"cpu": 15.4, "ram": 40.2, "temp": 55})
    
    # 2. محاكاة بيانات شبكة
    exporter.update_metric("network", {"binance_latency": 45, "status": "EXCELLENT"})
    
    # 3. محاكاة تنفيذ صفقات
    for _ in range(50):
        exporter.increment_transaction_count()
        
    time.sleep(0.5) # مرور نصف ثانية
    
    # 4. التصدير
    print("--- Metrics Snapshot (JSON for UI) ---")
    json_output = exporter.generate_snapshot_json()
    print(json_output)