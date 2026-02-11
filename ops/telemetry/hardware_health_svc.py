# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - HARDWARE HEALTH TELEMETRY SERVICE
==========================================================
Component Name: ops/telemetry/hardware_health_svc.py
Core Responsibility: مراقبة الحالة الفيزيائية (حرارة، ذاكرة، ضغط) لمنع الاختناق الحراري (Pillar: Stability).
Creation Date: 2026-02-03
Version: 1.0.0 (Thermal Shield Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يوفر الأدلة الجنائية في حالات "التباطؤ المفاجئ" (Lag Spikes).
إذا اشتكى المتداول من بطء التنفيذ، نراجع سجلات هذا الملف:
- هل حدث Thermal Throttling؟ (انخفاض تردد المعالج لحماية نفسه).
- هل حدث OOM Kill؟ (نفاد الذاكرة وقتل العملية).
"""

import psutil
import platform
import logging
import os
from dataclasses import dataclass, asdict
from typing import Dict, Optional

# إعداد السجلات
logger = logging.getLogger("AlphaHardware")

@dataclass
class HardwareStatus:
    """
    بنية بيانات تمثل الحالة الصحية للحاسوب في لحظة معينة.
    """
    cpu_usage_percent: float
    ram_usage_percent: float
    ram_available_gb: float
    cpu_temperature: Optional[float] # قد يكون None في بعض الأنظمة
    is_throttling: bool              # هل النظام يعاني من اختناق؟
    status: str                      # HEALTHY, WARNING, CRITICAL

class HardwareHealthService:
    """
    خدمة المراقبة الفيزيائية.
    تتعامل مع اختلافات أنظمة التشغيل (Windows vs Linux) لاستخراج بيانات المستشعرات.
    """

    def __init__(self):
        self.os_type = platform.system()
        # حدود الخطر (Thresholds)
        self.TEMP_WARNING = 80.0  # درجة مئوية
        self.RAM_CRITICAL = 90.0  # نسبة مئوية
        
    def scan_vital_signs(self) -> HardwareStatus:
        """
        إجراء فحص شامل للمؤشرات الحيوية للجهاز.
        """
        try:
            # 1. فحص المعالج (CPU)
            # interval=0.1 يعطي قراءة لحظية دقيقة بدلاً من المتوسط الطويل
            cpu_pct = psutil.cpu_percent(interval=0.1)
            
            # 2. فحص الذاكرة (RAM)
            mem = psutil.virtual_memory()
            ram_pct = mem.percent
            ram_gb = round(mem.available / (1024 ** 3), 2)
            
            # 3. فحص الحرارة (Thermal) - الجزء الأصعب لاختلاف الأنظمة
            temp = self._get_cpu_temperature()
            
            # 4. تحليل التشخيص (Heuristic Analysis)
            is_throttling = False
            status = "HEALTHY"
            
            # قواعد التشخيص
            if temp and temp > self.TEMP_WARNING:
                status = "WARNING"
                is_throttling = True # افتراض أن النظام سيقوم بالخنق الحراري
                logger.warning(f"High CPU Temp detected: {temp}°C")
                
            if ram_pct > self.RAM_CRITICAL:
                status = "CRITICAL"
                logger.critical(f"Memory Pressure Critical: {ram_pct}% used! Risk of OOM Kill.")

            return HardwareStatus(
                cpu_usage_percent=cpu_pct,
                ram_usage_percent=ram_pct,
                ram_available_gb=ram_gb,
                cpu_temperature=temp,
                is_throttling=is_throttling,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Hardware Scan Failed: {e}")
            # إرجاع حالة طوارئ وهمية لمنع انهيار البرنامج
            return HardwareStatus(0, 0, 0, None, False, "ERROR")

    def _get_cpu_temperature(self) -> Optional[float]:
        """
        استخراج درجة حرارة المعالج بطريقة متوافقة مع عدة أنظمة.
        """
        try:
            # Linux / macOS Approach
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if not temps:
                    return None
                
                # البحث عن حساسات المعالج الشائعة
                for name in ['coretemp', 'cpu_thermal', 'k10temp']:
                    if name in temps:
                        # أخذ متوسط حرارة الأنوية
                        entries = temps[name]
                        avg_temp = sum(e.current for e in entries) / len(entries)
                        return round(avg_temp, 1)
            
            # Windows Approach (psutil often fails here without Admin rights or WMI)
            # في بيئات الإنتاج الحقيقية على ويندوز، نستخدم مكتبة `wmi`
            # هنا نستخدم fallback بسيط
            return None 

        except Exception:
            return None

    def check_disk_space(self, path: str = ".") -> Dict[str, float]:
        """
        فحص مساحة القرص الصلب. ضروري جداً لقواعد البيانات والسجلات.
        """
        try:
            usage = psutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            }
        except Exception as e:
            logger.error(f"Disk Check Failed: {e}")
            return {}

# --- Unit Test ---
if __name__ == "__main__":
    svc = HardwareHealthService()
    
    print("--- Hardware Diagnostics ---")
    vitals = svc.scan_vital_signs()
    
    # عرض التقرير
    print(f"STATUS: {vitals.status}")
    print(f"CPU Load: {vitals.cpu_usage_percent}%")
    print(f"RAM Load: {vitals.ram_usage_percent}% (Available: {vitals.ram_available_gb} GB)")
    
    if vitals.cpu_temperature:
        print(f"CPU Temp: {vitals.cpu_temperature}°C")
    else:
        print("CPU Temp: Sensor not available (OS/Permission restriction)")
        
    print(f"Disk Check (.): {svc.check_disk_space('.')}")