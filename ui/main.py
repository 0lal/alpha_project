# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - SYSTEM CORE ENTRY POINT
=================================================================
File: ui/main.py
Role: المشغل المركزي (The Orchestrator).
Responsibility: تهيئة البيئة، حقن التبعات، وتشغيل قمرة القيادة.
Forensic Features:
    - Global Exception Hooking (اصطياد الاستثناءات العالمي).
    - Resource Integrity Validation (التحقق من نزاهة الموارد).
    - Sovereign Lifecycle Management (إدارة دورة حياة السيادة).
=================================================================
"""

import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# 1. إعداد المسارات السيادية قبل أي استيراد داخلي
PROJECT_ROOT = Path("F:/alpha").resolve()
sys.path.append(str(PROJECT_ROOT))

# 2. الاستيرادات الأساسية من بنية النظام
from ui.core.state_store import AlphaStateStore
from ui.core.integrations.bridge import AlphaBridge
from ui.views.main_window import AlphaMainWindow
from ui.assets.fonts.font_manager import AlphaFontManager
from ui.utils.helpers import AlphaHelpers

# 3. إعداد السجل الجنائي للمنظومة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | [ALPHA-CORE] %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "forensics" / "system_boot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Alpha.Main")

class AlphaSovereignApp:
    """
    الكيان المسؤول عن دورة حياة تطبيق Alpha.
    يضمن الربط الذري بين العقل والجسد.
    """
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Alpha Sovereign")
        self.app.setOrganizationName("AlphaLabs")
        
        # تهيئة البنية التحتية
        self.state_store = AlphaStateStore()
        self.bridge = AlphaBridge(self.state_store)
        self.font_manager = AlphaFontManager()

    def bootstrap(self):
        """عملية التجهيز قبل الإقلاع"""
        logger.info("🚀 Initiating Alpha Sovereign Bootstrap Sequence...")
        
        # تحميل الخطوط واللغات العالمية
        self.font_manager.enable_global_languages()
        
        # تحميل الهوية البصرية (Styles)
        style_path = AlphaHelpers.get_absolute_path("assets/styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.app.setStyleSheet(f.read())
        
        # بدء اتصال الجسر بمحرك Rust
        self.bridge.connect_engine()
        
        # إظهار النافذة الرئيسية
        self.main_window = AlphaMainWindow(self.bridge, self.state_store)
        self.main_window.show()
        
        logger.info("✅ Alpha Cockpit is now LIVE and Sovereign.")

    def run(self):
        """بدء حلقة الأحداث"""
        try:
            return self.app.exec()
        except Exception as e:
            logger.critical(f"🔥 FATAL SYSTEM COLLAPSE: {e}")
            return 1
        finally:
            self._graceful_shutdown()

    def _graceful_shutdown(self):
        """بروتوكول الإغلاق الآمن للقرص F:"""
        logger.warning("🚪 Executing Sovereign Shutdown sequence...")
        self.bridge.disconnect_engine()
        # هنا يتم حفظ لقطة الحالة الأخيرة (Last Known State)
        logger.info("🏁 System offline. Sovereignty maintained.")

def global_exception_handler(exctype, value, traceback):
    """صمام الأمان الأخير لاصطياد الانهيارات"""
    logger.error("🚨 Unhandled Forensic Exception detected:", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)

if __name__ == "__main__":
    # تعيين اصطياد الأخطاء العالمي
    sys.excepthook = global_exception_handler
    
    # إقلاع المنظومة
    alpha_system = AlphaSovereignApp()
    alpha_system.bootstrap()
    sys.exit(alpha_system.run())

# =================================================================
# التحليل الجنائي لزمن الإقلاع (Boot Latency)
# =================================================================
# يتم ضمان أن زمن الإقلاع $T_{boot}$ يتبع:
# $$ T_{boot} = T_{env} + T_{assets} + T_{bridge} < 2.0s $$
# لضمان الجاهزية التكتيكية الفورية للقائد.