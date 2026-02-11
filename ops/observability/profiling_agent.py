# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - AUTOMATED PERFORMANCE PROFILING AGENT
==============================================================
Component Name: ops/observability/profiling_agent.py
Core Responsibility: رصد اختناقات الأداء (Bottlenecks) وتحليل استهلاك الموارد (Pillar: Performance).
Creation Date: 2026-02-03
Version: 1.0.0 (Sniper Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يعمل بمبدأ "Amadahl's Law".
تحسين 1% من الكود الذي يعمل 90% من الوقت، أفضل من تحسين 90% من الكود الذي يعمل 1% من الوقت.
يقوم هذا الوكيل بتحديد "المسار الحرج" (Critical Path) الذي يضيع فيه وقت المعالج.
"""

import cProfile
import pstats
import io
import time
import logging
import threading
import psutil
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from pathlib import Path

# إعداد السجلات
logger = logging.getLogger("AlphaProfiler")

@dataclass
class BottleNeckReport:
    """تقرير جنائي يحدد المتهم الرئيسي في بطء النظام."""
    function_name: str
    file_path: str
    line_number: int
    total_calls: int
    cumulative_time: float  # الوقت الإجمالي المستغرق في الدالة
    per_call_time: float    # متوسط الوقت لكل استدعاء
    timestamp: float

class ProfilingAgent:
    """
    وكيل التنميط (Profiling Agent).
    يراقب النظام في الخلفية، وإذا اكتشف ضغطاً، يبدأ التحقيق.
    """

    def __init__(self, output_dir: str = "data/profiling"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._is_running = False
        self._trigger_threshold_cpu = 70.0  # تفعيل إذا تجاوز المعالج 70%
        self._profiling_duration = 10       # مدة التسجيل بالثواني

    def start_watchdog(self):
        """بدء المراقبة الخلفية."""
        if self._is_running: return
        self._is_running = True
        threading.Thread(target=self._monitor_loop, daemon=True, name="ProfileWatchdog").start()
        logger.info("Performance Watchdog Activated.")

    def _monitor_loop(self):
        """حلقة المراقبة المستمرة."""
        while self._is_running:
            try:
                # 1. قياس ضغط المعالج
                cpu_usage = psutil.cpu_percent(interval=1.0)
                
                # 2. قرار التفعيل
                if cpu_usage > self._trigger_threshold_cpu:
                    logger.warning(f"High CPU Detected ({cpu_usage}%). Initiating Profiling Session...")
                    self.run_snapshot_session(reason="CPU_SPIKE")
                    
                    # فترة تهدئة (Cooldown) لمنع التنميط المستمر
                    time.sleep(60) 
                
                time.sleep(5)
            except Exception as e:
                logger.error(f"Watchdog Error: {e}")
                time.sleep(10)

    def run_snapshot_session(self, duration: int = 10, reason: str = "MANUAL") -> Optional[str]:
        """
        تشغيل جلسة تنميط فورية.
        :return: مسار تقرير التحليل إذا نجح.
        """
        logger.info(f"Starting Profiler ({duration}s) - Reason: {reason}")
        
        profiler = cProfile.Profile()
        
        try:
            # 1. تفعيل المسجل
            profiler.enable()
            
            # 2. الانتظار (تجميع البيانات بينما النظام يعمل)
            time.sleep(duration)
            
            # 3. إيقاف المسجل
            profiler.disable()
            
            # 4. تحليل البيانات
            return self._analyze_and_save(profiler, reason)
            
        except Exception as e:
            logger.error(f"Profiling Session Failed: {e}")
            return None

    def _analyze_and_save(self, profiler: cProfile.Profile, reason: str) -> str:
        """
        تحويل البيانات الخام إلى تقرير مقروء وتحديد "المتهمين".
        """
        s = io.StringIO()
        # ترتيب النتائج حسب الوقت التراكمي (cumulative) لكشف الدوال الثقيلة
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # طباعة أهم 20 دالة فقط

        # استخراج البيانات الخام للتحليل البرمجي
        # (هنا يمكننا كتابة منطق لاستخراج اسم الدالة الأبطأ تلقائياً)
        
        # حفظ التقرير النصي
        timestamp = int(time.time())
        filename = f"profile_{reason}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"ALPHA PERFORMANCE REPORT | Reason: {reason} | Time: {time.ctime(timestamp)}\n")
            f.write("="*80 + "\n")
            f.write(s.getvalue())
        
        logger.info(f"Profiling Report Saved: {filepath}")
        
        # محاولة تحديد "عنق الزجاجة" الأول برمجياً
        self._identify_top_bottleneck(ps)
        
        return str(filepath)

    def _identify_top_bottleneck(self, stats: pstats.Stats):
        """
        تحليل ذكي لمحاولة استخراج اسم الدالة المذنبة وإبلاغ السجلات.
        """
        try:
            # Stats.stats هو قاموس: مفتاحه (file, line, func)، وقيمته (cc, nc, tt, ct, callers)
            # cc: call count, ct: cumulative time
            
            # تحويل القاموس لقائمة مرتبة
            sorted_funcs = sorted(stats.stats.items(), key=lambda x: x[1][3], reverse=True)
            
            # تجاهل دوال النظام والمكتبات الخارجية (تقريبياً)
            for func_key, func_data in sorted_funcs:
                file_name, line, func_name = func_key
                cumulative_time = func_data[3]
                
                # نحن مهتمون فقط بملفات مشروعنا (تجاهل مكتبات python)
                if "alpha" in str(file_name) or "brain" in str(file_name):
                    logger.warning(
                        f"BOTTLENECK IDENTIFIED: Function '{func_name}' at {file_name}:{line} "
                        f"consumed {cumulative_time:.4f}s"
                    )
                    break # وجدنا المتهم الأول
                    
        except Exception as e:
            logger.error(f"Failed to identify bottleneck programmatically: {e}")

# --- Unit Test ---
if __name__ == "__main__":
    agent = ProfilingAgent()
    
    print("--- Simulating Heavy Load ---")
    
    # دالة بطيئة للتجربة
    def heavy_computation():
        total = 0
        for i in range(1000000): # حلقة ثقيلة
            total += i ** 2
        return total

    # تشغيل البروفايلر يدوياً
    # سنقوم بتشغيل الدالة في مسلك منفصل لمحاكاة عمل النظام
    threading.Thread(target=heavy_computation).start()
    
    # تشغيل التسجيل لمدة 2 ثانية
    report_path = agent.run_snapshot_session(duration=2, reason="TEST_RUN")
    
    print(f"\nReport generated at: {report_path}")
    print("Check the file content to see 'heavy_computation' listed at the top.")