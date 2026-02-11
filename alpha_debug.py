# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

print("🔍 [STEP 1] Starting Forensic Diagnostic...")

try:
    import PySide6
    print(f"✅ [STEP 2] PySide6 found (Version: {PySide6.__version__})")
except ImportError:
    print("❌ [FAILED] PySide6 is NOT installed in this environment.")
    sys.exit(1)

from PySide6.QtWidgets import QApplication, QLabel

print("🔍 [STEP 3] Checking Project Structure...")
ROOT_DIR = Path(__file__).resolve().parent
print(f"📍 Root Directory: {ROOT_DIR}")

# التحقق من وجود الملفات الحيوية
critical_files = [
    "ui/views/main_window.py",
    "ui/core/integrations/bridge.py",
    "ui/components/molecules/side_nav_bar.py"
]

for f in critical_files:
    p = ROOT_DIR / f
    if p.exists():
        print(f"✅ File Exists: {f}")
    else:
        print(f"❌ MISSING FILE: {f}")

print("🔍 [STEP 4] Attempting to launch Minimal GUI...")
try:
    app = QApplication(sys.argv)
    test_win = QLabel("ALPHA DIAGNOSTIC: IF YOU SEE THIS, GUI WORKS")
    test_win.setMinimumSize(400, 200)
    test_win.show()
    print("🚀 [SUCCESS] Minimal GUI launched. Close the small window to continue.")
    app.exec()
except Exception as e:
    print(f"❌ [GUI FAILED]: {str(e)}")

print("🏁 Diagnostic Finished.")