# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - AUTOMATED INCIDENT FORENSICS GENERATOR
=================================================================
Component: shield/forensics/incident_report_gen.py
Core Responsibility: تجميد مسرح الجريمة وتوليد تقرير جنائي شامل عند وقوع حادث (Explainability Pillar).
Design Pattern: Builder / Snapshot
Forensic Impact: يحول البيانات المتطايرة (Volatile Data) إلى أدلة دائمة. يوفر سياقاً (CPU, RAM, Net) وليس فقط رسالة خطأ.
=================================================================
"""

import json
import time
import uuid
import platform
import psutil
import logging
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.forensics")

@dataclass
class IncidentContext:
    """البيانات الأولية للحادث"""
    source_component: str
    incident_type: str      # e.g., "UNAUTHORIZED_ACCESS", "DMS_TRIGGER"
    severity: str           # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    related_container_id: Optional[str] = None

class IncidentReportGenerator:
    def __init__(self, reports_dir: str = "logs/forensics"):
        self.reports_dir = reports_dir
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)

    def generate_report(self, context: IncidentContext) -> str:
        """
        إنشاء تقرير جنائي كامل.
        يعيد مسار ملف التقرير.
        """
        incident_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        logger.info(f"FORENSICS: Generating report {incident_id} for {context.incident_type}...")

        # 1. التقاط حالة النظام (System Snapshot)
        # البيانات المتطايرة التي ستختفي بعد ثوانٍ
        system_snapshot = self._capture_system_state()

        # 2. بناء التقرير
        report_data = {
            "meta": {
                "report_id": incident_id,
                "timestamp": timestamp,
                "generated_by": "Alpha Shield Sentinel",
                "version": "1.0"
            },
            "incident": asdict(context),
            "environment": {
                "node": platform.node(),
                "os": platform.system(),
                "release": platform.release(),
                "uptime_sec": time.time() - psutil.boot_time()
            },
            "system_snapshot": system_snapshot,
            "integrity": {
                "hash_algorithm": "SHA-256",
                "signature": "" # سيتم ملؤه لاحقاً
            }
        }

        # 3. الحفظ والتوقيع
        return self._save_and_sign(incident_id, report_data)

    def _capture_system_state(self) -> Dict[str, Any]:
        """التقاط صورة حية للموارد والشبكة"""
        try:
            # استخدام الموارد
            cpu_load = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            
            # اتصالات الشبكة الحالية (فقط الـ Established للسرعة)
            net_connections = []
            try:
                for conn in psutil.net_connections(kind='inet'):
                    if conn.status == 'ESTABLISHED':
                        net_connections.append({
                            "laddr": f"{conn.laddr.ip}:{conn.laddr.port}",
                            "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                            "pid": conn.pid
                        })
            except Exception:
                net_connections = ["Permission Denied"]

            # العمليات الأعلى استهلاكاً (Top Processes)
            top_processes = []
            try:
                # ترتيب العمليات حسب استهلاك الذاكرة
                for proc in sorted(psutil.process_iter(['pid', 'name', 'memory_percent']), 
                                   key=lambda p: p.info['memory_percent'], 
                                   reverse=True)[:5]:
                    top_processes.append(proc.info)
            except Exception:
                pass

            return {
                "cpu_load_percent": cpu_load,
                "memory_used_percent": memory.percent,
                "available_ram_mb": memory.available / (1024 * 1024),
                "active_connections_count": len(net_connections),
                "suspicious_connections_sample": net_connections[:10], # أول 10 فقط للتسجيل
                "top_memory_processes": top_processes
            }
        except Exception as e:
            logger.error(f"FORENSICS_ERR: Snapshot failed: {e}")
            return {"error": str(e)}

    def _save_and_sign(self, incident_id: str, data: Dict[str, Any]) -> str:
        """حفظ التقرير وحساب البصمة الرقمية"""
        file_name = f"incident_{incident_id}_{data['incident']['incident_type']}.json"
        file_path = os.path.join(self.reports_dir, file_name)

        # 1. تحويل البيانات لنص لحساب الهاش
        raw_json = json.dumps(data, indent=4, sort_keys=True)
        
        # 2. حساب الهاش (Digital Fingerprint)
        # هذا يضمن عدم تعديل التقرير لاحقاً
        data_hash = hashlib.sha256(raw_json.encode()).hexdigest()
        data['integrity']['signature'] = data_hash
        
        # 3. الكتابة النهائية
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        logger.warning(f"FORENSICS: Report saved to {file_path} (Signature: {data_hash[:8]}...)")
        return file_path

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    generator = IncidentReportGenerator()
    
    # محاكاة حادث
    ctx = IncidentContext(
        source_component="FirewallRulesEngine",
        incident_type="UNAUTHORIZED_ACCESS",
        severity="HIGH",
        description="Blocked connection attempt from blacklisted IP 192.168.1.66 on port 50051",
        related_container_id="alpha_core_v1"
    )
    
    report_path = generator.generate_report(ctx)
    
    print(f"\n--- Forensics Simulation Complete ---")
    print(f"Report generated at: {report_path}")
    
    # قراءة التقرير للتحقق
    with open(report_path, 'r') as f:
        saved_report = json.load(f)
        print(f"Snapshot CPU Load: {saved_report['system_snapshot']['cpu_load_percent']}%")
        print(f"Integrity Signature: {saved_report['integrity']['signature']}")