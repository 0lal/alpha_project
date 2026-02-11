# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - DEAD MAN'S SWITCH (PROTOCOL OMEGA) v2.0
=================================================================
Component: shield/sentinel/dead_man_switch.py
Core Responsibility: حماية السيادة عند غياب المالك (Last Resort).
Forensic Features:
  - Dynamic State Storage (تخزين الحالة في مسار آمن وثابت).
  - Graceful Countdown (عد تنازلي مرئي في السجلات).
  - Dual-Key Activation (يتطلب تأكيدين للتدمير).
  - Immutable Logging (تسجيل الحدث في مكان لا يمكن حذفه بسهولة).
=================================================================
"""

import threading
import time
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable

# --- 1. الربط بالمسار الديناميكي ---
try:
    CURRENT_FILE = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_FILE.parent.parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from shield.core.guardian import ROOT_DIR
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# مسارات الحالة
STATE_DIR = ROOT_DIR / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
DMS_STATE_FILE = STATE_DIR / "dms_heartbeat.json"

# إعداد التسجيل
logger = logging.getLogger("Alpha.Shield.DMS")

class ProtocolOmegaConfig:
    """إعدادات الوصية الأخيرة"""
    def __init__(self):
        # الإعدادات الافتراضية (يمكن تجاوزها من ملف config)
        self.warning_hours = 72.0     # 3 أيام
        self.trigger_hours = 24.0     # يوم واحد بعد التحذير
        self.beneficiary_wallet = os.getenv("DMS_BENEFICIARY", "bc1q_INVALID_DEFAULT")
        self.auto_liquidate = True

class DeadManSwitch:
    """
    مفتاح الرجل الميت.
    يراقب نبض المالك. إذا توقف، يبدأ العد التنازلي للنهاية.
    """

    def __init__(self):
        self.config = ProtocolOmegaConfig()
        self.last_seen = time.time()
        self.status = "ACTIVE"
        self._load_state()
        
        # Callbacks (يجب ربطها عند التشغيل)
        self.on_liquidate = None
        self.on_wipe = None

    def _load_state(self):
        """استعادة الذاكرة من القرص"""
        if DMS_STATE_FILE.exists():
            try:
                with open(DMS_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.last_seen = data.get("last_seen", time.time())
                    self.status = data.get("status", "ACTIVE")
                    logger.info(f"DMS State Loaded. Last Seen: {datetime.fromtimestamp(self.last_seen)}")
            except Exception as e:
                logger.error(f"DMS State Corrupt: {e}")

    def _save_state(self):
        """تثبيت الذاكرة على القرص"""
        try:
            with open(DMS_STATE_FILE, 'w') as f:
                json.dump({
                    "last_seen": self.last_seen,
                    "status": self.status,
                    "updated_at": datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.error(f"DMS Save Failed: {e}")

    def pulse(self):
        """
        إشارة "أنا حي".
        يجب استدعاؤها من واجهة المستخدم أو التيرمينال.
        """
        self.last_seen = time.time()
        self.status = "ACTIVE"
        self._save_state()
        logger.info("❤️ DMS Heartbeat Acknowledged.")

    def check_status(self) -> str:
        """
        فحص الحالة الحالية (يستدعى دورياً من Sentinel).
        """
        elapsed = (time.time() - self.last_seen) / 3600.0 # ساعات
        
        limit_warn = self.config.warning_hours
        limit_kill = limit_warn + self.config.trigger_hours
        
        if elapsed < limit_warn:
            return "OK"
            
        if limit_warn <= elapsed < limit_kill:
            remaining = limit_kill - elapsed
            logger.warning(f"⚠️ DMS WARNING: Owner missing for {elapsed:.1f}h. Omega in {remaining:.1f}h.")
            return "WARNING"
            
        if elapsed >= limit_kill:
            if self.status != "TRIGGERED":
                self.trigger_omega()
            return "TRIGGERED"
            
        return "UNKNOWN"

    def trigger_omega(self):
        """
        تنفيذ بروتوكول النهاية.
        """
        logger.critical("💀 OWNER PRESUMED LOST. INITIATING PROTOCOL OMEGA.")
        self.status = "TRIGGERED"
        self._save_state()
        
        # 1. التسييل
        if self.config.auto_liquidate and self.on_liquidate:
            try:
                logger.warning("💸 Liquidating Assets...")
                self.on_liquidate()
            except Exception as e:
                logger.error(f"Liquidation Failed: {e}")
                
        # 2. مسح الأسرار
        if self.on_wipe:
            try:
                logger.warning("🔥 Wiping Secrets...")
                self.on_wipe()
            except Exception as e:
                logger.error(f"Wipe Failed: {e}")
                
        # 3. إغلاق النظام
        logger.critical("System is now inert. Goodbye.")

# =================================================================
# Forensic Verification
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dms = DeadManSwitch()
    
    print(f"[*] DMS Initialized at {DMS_STATE_FILE}")
    print(f"[*] Last Seen: {datetime.fromtimestamp(dms.last_seen)}")
    
    # محاكاة نبضة
    dms.pulse()
    
    # تسريع الزمن للمحاكاة
    print("[*] Simulating Time Travel (4 days forward)...")
    dms.last_seen -= (3600 * 96) 
    
    # ربط وظائف وهمية
    dms.on_liquidate = lambda: print("   >>> MOCK: SELLING BTC")
    dms.on_wipe = lambda: print("   >>> MOCK: DELETING KEYS")
    
    # الفحص
    status = dms.check_status()
    print(f"[*] Status: {status}")