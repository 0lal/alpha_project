# -*- coding: utf-8 -*-
import os
import shutil

# تحديد المسار الجذري
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

print(f"🔧 Starting Alpha System Installation in: {ROOT_DIR}")

# 1. تعريف خريطة الملفات (المسار : المحتوى)
files_map = {
    # ---------------------------------------------------------
    # الجذر
    # ---------------------------------------------------------
    "run_alpha.py": r'''# -*- coding: utf-8 -*-
import sys
import os

# ضبط المسارات
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'brain'))

from PySide6.QtWidgets import QApplication
from interface.app_launcher import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Alpha Sovereign")
    window = MainWindow()
    window.show()
    print("🚀 ALPHA SYSTEM ONLINE")
    sys.exit(app.exec())
''',

    # ---------------------------------------------------------
    # CORE (الجسر والعمليات)
    # ---------------------------------------------------------
    "core/__init__.py": "",
    
    "core/bridge.py": r'''# -*- coding: utf-8 -*-
import sys
import os

# محاولة ربط العقل
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from brain.brain_router import AlphaBrainCore
    print("✅ BRIDGE: Connected to Brain.")
except ImportError:
    print("⚠️ BRIDGE: Using Fallback Core (Brain Not Found).")
    class AlphaBrainCore:
        def think_about_context(self, s, t): return {"sentiment": "NO_BRAIN", "confidence": 0.0, "regime": "ERROR"}
        def evaluate_trade_proposal(self, s, d, a): return {"approved": False, "reason": "System Disconnected"}

class SystemBridge:
    def __init__(self):
        self.cortex = AlphaBrainCore()

    def process_user_query(self, text: str) -> str:
        text = text.upper()
        if "تحليل" in text or "ANALYZE" in text:
            res = self.cortex.think_about_context("BTCUSDT", "1h")
            return f"📊 التقرير:\n• الاتجاه: {res.get('sentiment')}\n• الثقة: {res.get('confidence',0)*100:.1f}%"
        elif "شراء" in text:
            res = self.cortex.evaluate_trade_proposal("BTC", "BUY", 1.0)
            return f"🛡️ القرار: {'موافقة' if res.get('approved') else 'رفض'}\nالسبب: {res.get('reason')}"
        return "الأمر غير معروف. جرب 'تحليل' أو 'شراء'."
''',

    "core/workers.py": r'''# -*- coding: utf-8 -*-
from PySide6.QtCore import QThread, Signal
from core.bridge import SystemBridge

class BrainWorker(QThread):
    response_received = Signal(str)
    def __init__(self):
        super().__init__()
        self.bridge = SystemBridge()
        self.pending_text = None

    def run(self):
        if self.pending_text:
            resp = self.bridge.process_user_query(self.pending_text)
            self.response_received.emit(resp)
            self.pending_text = None

    def analyze(self, text):
        self.pending_text = text
        self.start()
''',

    # ---------------------------------------------------------
    # INTERFACE (الواجهة)
    # ---------------------------------------------------------
    "interface/__init__.py": "",
    
    "interface/app_launcher.py": r'''# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QLabel
from PySide6.QtCore import Qt
from interface.assets.styles import AlphaStyles
from interface.components.sidebar import Sidebar
from interface.pages.advisory_view import AdvisoryView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALPHA SOVEREIGN")
        self.resize(1200, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(AlphaStyles.MASTER)
        
        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        layout.addWidget(self.sidebar)
        
        self.stack = QStackedWidget()
        self.stack.addWidget(QLabel("لوحة القيادة", alignment=Qt.AlignCenter)) # 0
        self.stack.addWidget(AdvisoryView()) # 1
        layout.addWidget(self.stack)
        
        self.switch_page(1)

    def switch_page(self, index):
        if index < self.stack.count():
            self.stack.setCurrentIndex(index)
''',

    # Assets
    "interface/assets/__init__.py": "",
    "interface/assets/styles.py": r'''# -*- coding: utf-8 -*-
class AlphaColors:
    BG = "#050505"; SURFACE = "#09090B"; ACCENT = "#00E5FF"; TEXT = "#FFFFFF"

class AlphaStyles:
    MASTER = f"QMainWindow {{ background: {AlphaColors.BG}; }} QWidget {{ color: {AlphaColors.TEXT}; font-family: Segoe UI; font-size: 14px; }}"
    BTN_SIDEBAR = f"QPushButton {{ background: transparent; border: none; text-align: right; padding: 15px; color: #888; }} QPushButton:hover {{ color: {AlphaColors.ACCENT}; }} QPushButton[active='true'] {{ color: {AlphaColors.ACCENT}; border-right: 3px solid {AlphaColors.ACCENT}; background: #111; }}"
''',

    # Components
    "interface/components/__init__.py": "",
    "interface/components/sidebar.py": r'''# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from interface.assets.styles import AlphaStyles, AlphaColors

class Sidebar(QFrame):
    page_changed = Signal(int)
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {AlphaColors.SURFACE}; min-width: 220px;")
        layout = QVBoxLayout(self)
        
        title = QLabel("ALPHA\nSOVEREIGN")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {AlphaColors.ACCENT}; font-weight: bold; font-size: 20px; margin: 20px;")
        layout.addWidget(title)
        
        self.btns = []
        for i, txt in enumerate(["القيادة", "الشورى", "السجلات"]):
            btn = QPushButton(txt)
            btn.setStyleSheet(AlphaStyles.BTN_SIDEBAR)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, x=i: self.clk(x))
            layout.addWidget(btn)
            self.btns.append(btn)
        
        layout.addStretch()
        self.clk(1)

    def clk(self, idx):
        self.page_changed.emit(idx)
        for i, b in enumerate(self.btns):
            b.setProperty("active", i == idx)
            b.style().unpolish(b); b.style().polish(b)
''',

    "interface/components/chat_box.py": r'''# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton
from interface.assets.styles import AlphaColors

class ChatBox(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.cb = callback
        layout = QVBoxLayout(self)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"background: #0D0D0D; border: 1px solid #333; border-radius: 8px;")
        
        inp_lay = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("أمر التحليل...")
        self.inp.setStyleSheet("background: #151515; border: 1px solid #333; padding: 10px;")
        self.inp.returnPressed.connect(self.send)
        
        btn = QPushButton("إرسال")
        btn.setStyleSheet(f"background: {AlphaColors.ACCENT}; color: black; font-weight: bold; padding: 10px;")
        btn.clicked.connect(self.send)
        
        inp_lay.addWidget(self.inp); inp_lay.addWidget(btn)
        layout.addWidget(self.log); layout.addLayout(inp_lay)

    def send(self):
        t = self.inp.text()
        if t:
            self.log.append(f"<br><b>أنت:</b> {t}")
            self.cb(t)
            self.inp.clear()

    def add_msg(self, t):
        self.log.append(f"<b style='color:{AlphaColors.ACCENT}'>ألفا:</b> {t}")
''',

    # Pages
    "interface/pages/__init__.py": "",
    "interface/pages/advisory_view.py": r'''# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from interface.components.chat_box import ChatBox
from core.workers import BrainWorker

class AdvisoryView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("غرفة الشورى", styleSheet="font-size: 18px; font-weight: bold; color: #666;"))
        
        self.worker = BrainWorker()
        self.worker.response_received.connect(self.on_resp)
        
        self.chat = ChatBox(self.worker.analyze)
        layout.addWidget(self.chat)
        self.chat.add_msg("النظام متصل.")

    def on_resp(self, t):
        self.chat.add_msg(t)
'''
}

# 2. عملية التثبيت (إنشاء المجلدات والملفات)
for path, content in files_map.items():
    full_path = os.path.join(ROOT_DIR, path)
    
    # إنشاء المجلد إذا لم يكن موجوداً
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # كتابة الملف
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Installed: {path}")

print("\n🎉 INSTALLATION COMPLETE!")
print("Run this command now: python run_alpha.py")