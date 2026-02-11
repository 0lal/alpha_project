# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - STRATEGY CONFIGURATION MANAGER
=================================================================
Component: brain/core/strategy_manager.py
Core Responsibility: إدارة ملف تعريف الاستراتيجية بأمان ذري (Atomic Safety).
Forensic Features:
  - Atomic Writes (منع فساد الملف عند انقطاع الطاقة).
  - Schema Validation (منع القيم غير المنطقية).
  - Auto-Recovery (إعادة بناء الملف إذا تم حذفه).
=================================================================
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

# تحديد المسار ديناميكياً
try:
    CURRENT_FILE = Path(__file__).resolve()
    ROOT_DIR = CURRENT_FILE.parent.parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
except:
    ROOT_DIR = Path(".").resolve()

CONFIG_PATH = ROOT_DIR / "config" / "logic" / "strategy_profile.json"

# إعداد السجلات
logger = logging.getLogger("Alpha.Brain.ConfigMgr")

# الإعدادات الافتراضية الآمنة (Factory Reset)
DEFAULT_PROFILE = {
    "_meta": {
        "version": "2.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "updated_by": "AUTO_RECOVERY"
    },
    "modules": {
        "quant_analysis": {"enabled": True, "weight": 1.0, "mode": "STANDARD"},
        "sentiment_analysis": {"enabled": True, "weight": 1.0, "mode": "HYBRID"},
        "hybrid_reasoning": {"enabled": False, "weight": 0.0, "mode": "DISABLED"} # معطل افتراضياً للأمان
    },
    "risk_parameters": {"strict_mode": True},
    "global_switch": "PAUSED"
}

class StrategyConfigManager:
    """
    مدير التكوين الاستراتيجي.
    يضمن أن العقل يقرأ دائماً إعدادات صالحة.
    """

    def __init__(self):
        self._ensure_config_exists()
        self.cache = self.load_profile()

    def _ensure_config_exists(self):
        """التأكد من وجود الملف والمجلد"""
        if not CONFIG_PATH.exists():
            logger.warning("Strategy Profile missing. Generating Factory Default.")
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.save_profile(DEFAULT_PROFILE, "SYSTEM_INIT")

    def load_profile(self) -> Dict[str, Any]:
        """تحميل الإعدادات مع معالجة الأخطاء"""
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # فحص سريع للصحة (Sanity Check)
                if "modules" not in data:
                    raise ValueError("Invalid Config Schema")
                return data
        except Exception as e:
            logger.error(f"Config Corruption Detected: {e}. Reverting to Default.")
            return DEFAULT_PROFILE

    def save_profile(self, new_data: Dict[str, Any], author: str = "USER") -> bool:
        """
        حفظ ذري (Atomic Save).
        يكتب في ملف مؤقت .tmp ثم يقوم بعمل Rename.
        هذا يضمن أنه لا توجد لحظة يكون فيها الملف فارغاً أو تالفاً.
        """
        try:
            # تحديث الميتا داتا
            new_data["_meta"] = {
                "version": "2.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "updated_by": author
            }

            # 1. الكتابة في ملف مؤقت
            temp_path = CONFIG_PATH.with_suffix(".tmp")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno()) # إجبار الكتابة على القرص

            # 2. الاستبدال الذري (Atomic Replace)
            shutil.move(str(temp_path), str(CONFIG_PATH))
            
            # تحديث الكاش
            self.cache = new_data
            logger.info(f"Strategy Profile Updated by {author}.")
            return True

        except Exception as e:
            logger.critical(f"Failed to save strategy profile: {e}")
            return False

    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """استرجاع إعدادات وحدة معينة"""
        modules = self.cache.get("modules", {})
        return modules.get(module_name, {"enabled": False, "weight": 0.0})

    def update_module_state(self, module_name: str, enabled: bool, weight: float = None):
        """تحديث سريع لوحدة واحدة"""
        data = self.load_profile()
        if module_name in data["modules"]:
            data["modules"][module_name]["enabled"] = enabled
            if weight is not None:
                data["modules"][module_name]["weight"] = max(0.0, float(weight))
            self.save_profile(data, "API_UPDATE")

# =================================================================
# Forensic Verification
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = StrategyConfigManager()
    
    print(f"[*] Config Path: {CONFIG_PATH}")
    print("[*] Current State:")
    print(json.dumps(mgr.cache["modules"], indent=2))
    
    # Test Update
    print("\n[*] Enabling Hybrid Reasoning...")
    mgr.update_module_state("hybrid_reasoning", True, weight=2.5)
    
    # Reload to verify
    reloaded = mgr.load_profile()
    print(f"[*] New Weight: {reloaded['modules']['hybrid_reasoning']['weight']}")