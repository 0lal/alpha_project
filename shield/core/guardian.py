#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - THE IMMORTAL GUARDIAN
=================================================================
Component: shield/core/guardian.py
Role: المراقب الأعلى (System Watchdog).
Forensic Features:
  - Dynamic Path Discovery (اكتشاف المسار الديناميكي).
  - Crash Loop Protection (حماية من إعادة التشغيل اللانهائية).
  - Graceful Shutdown Handling (إغلاق نظيف).
  - Environment Agnostic (يعمل على أي نظام تشغيل).
=================================================================
"""

import subprocess
import sys
import time
import logging
import signal
import os
from pathlib import Path
from datetime import datetime

# --- 1. اكتشاف المسار الديناميكي (The Fix) ---
# نحدد مكان هذا الملف، ثم نعود للخلف للوصول للجذر
# shield/core/guardian.py -> shield/core -> shield -> alpha_project (ROOT)
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent.parent
LAUNCHER_SCRIPT = ROOT_DIR / "alpha_launcher.py"

# إضافة الجذر لمسار النظام لضمان استيراد المديولات
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --- إعداد السجلات ---
LOG_DIR = ROOT_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "guardian_event.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | GUARDIAN | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AlphaGuardian")

class Guardian:
    """
    فئة الحارس.
    مسؤولة عن ضمان بقاء النظام حياً (High Availability).
    """
    
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.last_restart_time = datetime.min
        self.running = True

        # التقاط إشارات الإغلاق (Ctrl+C / Kill)
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        """معالج الإغلاق الآمن"""
        logger.warning("\n🛑 Guardian received TERMINATE signal.")
        self.running = False
        if self.process:
            logger.info("Killing Child Process (Alpha)...")
            # نحاول الإغلاق اللطيف أولاً
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Child process unresponsive. Forcing KILL.")
                self.process.kill()
        sys.exit(0)

    def spawn_system(self) -> int:
        """
        تشغيل النظام والانتظار.
        """
        if not LAUNCHER_SCRIPT.exists():
            logger.critical(f"❌ FATAL: Launcher not found at: {LAUNCHER_SCRIPT}")
            return -1

        # بناء الأمر: [python, script_path]
        cmd = [sys.executable, str(LAUNCHER_SCRIPT)]
        
        logger.info(f"🚀 Spawning Alpha System... (Revival #{self.restart_count})")
        logger.info(f"   Root: {ROOT_DIR}")

        try:
            # تشغيل العملية الفرعية
            self.process = subprocess.Popen(
                cmd,
                cwd=str(ROOT_DIR),
                env=os.environ.copy() # تمرير متغيرات البيئة
            )
            
            # الانتظار حتى تنتهي العملية (Blocking Call)
            return_code = self.process.wait()
            return return_code

        except Exception as e:
            logger.critical(f"🔥 Execution Failed: {e}")
            return -2

    def watch(self):
        """
        دورة المراقبة اللانهائية.
        """
        print(f"\n🛡️  ALPHA GUARDIAN ACTIVE")
        print(f"📍 Watching: {ROOT_DIR}")
        print("-" * 40)

        while self.running:
            start_time = datetime.now()
            
            # 1. تشغيل النظام
            exit_code = self.spawn_system()
            
            # 2. تحليل سبب الوفاة
            run_duration = (datetime.now() - start_time).total_seconds()
            
            if exit_code == 0:
                logger.info("✅ Alpha exited normally. Guardian standing down.")
                break
            
            elif exit_code == -1:
                logger.critical("❌ Launcher missing. Guardian aborting.")
                break

            else:
                logger.error(f"⚠️ Alpha CRASHED (Code: {exit_code}). Runtime: {run_duration:.1f}s")
                
                # 3. حماية من الانهيار المتكرر (Anti-Thrashing)
                # إذا انهار النظام في أقل من 5 ثوانٍ، ننتظر قليلاً لتبريد المعالج
                if run_duration < 5:
                    logger.warning("⚠️ Rapid crash detected. Cooling down for 10s...")
                    time.sleep(10)
                else:
                    time.sleep(2) # انتظار قصير طبيعي

                self.restart_count += 1
                self.last_restart_time = datetime.now()

if __name__ == "__main__":
    guardian = Guardian()
    guardian.watch()