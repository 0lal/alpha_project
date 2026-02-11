import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, 
    QLabel, QTabWidget, QTextBrowser, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.sound_engine import SoundEngine
from ui.core.logger_sink import logger_sink

# --- استيراد المكونات ---
from ui.components.organisms.code_editor import CodeEditor
from ui.components.atoms.modern_buttons import ActionButton, ModernButton
from ui.components.atoms.status_led import StatusLED

logger = logging.getLogger("Alpha.Lab")

class LabView(QWidget):
    """
    مختبر التطوير والاختبار (The Strategy Lab).
    
    المهمة:
    1. كتابة وتعديل استراتيجيات بايثون مع تلوين الكود (Syntax Highlighting).
    2. التحقق من سلامة الكود قبل الحفظ (AST Validation).
    3. عرض نتائج الاختبار (Backtest Logs) في نفس الشاشة.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # تخطيط الصفحة: شريط أدوات علوي + محرر مقسم
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # 1. شريط الأدوات (Toolbar)
        self._build_toolbar()

        # 2. المنطقة الرئيسية (Splitter: Code vs Results)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(2)
        
        # A. المحرر (Code Editor)
        self.editor_container = QWidget()
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        # عنوان صغير فوق المحرر
        lbl_editor = QLabel("PYTHON STRATEGY EDITOR")
        lbl_editor.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_editor.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; letter-spacing: 1px;")
        editor_layout.addWidget(lbl_editor)
        
        self.code_editor = CodeEditor()
        # ربط إشارة التحقق من الكود بتحديث الواجهة
        self.code_editor.validation_status_changed.connect(self._on_validation_changed)
        editor_layout.addWidget(self.code_editor)
        
        self.splitter.addWidget(self.editor_container)

        # B. منطقة النتائج (Results Console)
        self.results_container = QTabWidget()
        self.results_container.setDocumentMode(True)
        
        # Tab 1: Console Logs
        self.console_output = QTextBrowser()
        self.console_output.setOpenExternalLinks(False)
        self.console_output.setFont(QFont("Consolas", 9))
        self.console_output.setReadOnly(True)
        self.results_container.addTab(self.console_output, "Simulation Output")
        
        # Tab 2: Trade List (Placeholder)
        self.trade_list = QLabel("No trades generated yet.")
        self.trade_list.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_container.addTab(self.trade_list, "Trade List")

        self.splitter.addWidget(self.results_container)
        
        # ضبط نسب التقسيم (70% للكود، 30% للنتائج)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)

        self.layout.addWidget(self.splitter)

        # تحميل مثال افتراضي
        self._load_template_strategy()
        
        # تطبيق الثيم
        theme_engine.theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _build_toolbar(self):
        """بناء أزرار التحكم العلوية"""
        toolbar = QHBoxLayout()
        
        # مؤشر الحالة (صالح/غير صالح)
        self.status_led = StatusLED(size=16)
        self.status_led.set_status(StatusLED.OK, "Code Valid")
        toolbar.addWidget(self.status_led)
        
        toolbar.addSpacing(10)

        # الأزرار
        self.btn_load = ActionButton("OPEN FILE")
        self.btn_load.clicked.connect(self._load_file)
        
        self.btn_save = ActionButton("SAVE")
        self.btn_save.clicked.connect(self._save_file)
        
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        
        toolbar.addStretch()
        
        # زر التشغيل (الأهم)
        self.btn_run = ModernButton("RUN BACKTEST", color="#00ff41") # Green
        self.btn_run.clicked.connect(self._run_simulation)
        self.btn_run.setFixedWidth(150)
        toolbar.addWidget(self.btn_run)

        self.layout.addLayout(toolbar)

    def _apply_theme(self):
        """تخصيص ألوان التبويبات والفاصل"""
        bg = theme_engine.get_color("background")
        surface = theme_engine.get_color("surface")
        border = theme_engine.get_color("grid_line")
        text = theme_engine.get_color("text_primary")
        
        self.console_output.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {surface};
                color: {text};
                border: none;
                font-family: 'Consolas';
            }}
        """)
        
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {border};
            }}
        """)

    # =========================================================================
    # Logic & Event Handlers
    # =========================================================================

    def _on_validation_changed(self, is_valid: bool, msg: str):
        """يستقبل نتيجة فحص الكود من CodeEditor"""
        if is_valid:
            self.status_led.set_status(StatusLED.OK, "Syntax Correct")
            self.btn_run.setEnabled(True)
            self.btn_run.setToolTip("Ready to simulate")
        else:
            self.status_led.set_status(StatusLED.ERROR, msg)
            self.btn_run.setEnabled(False) # منع التشغيل إذا كان الكود مكسوراً
            self.btn_run.setToolTip(f"Fix Errors: {msg}")

    def _run_simulation(self):
        """محاكاة تشغيل الاستراتيجية"""
        code = self.code_editor.get_code()
        if not code:
            return

        logger_sink.log_system_event("Lab", "INFO", "🧪 Starting simulation...")
        SoundEngine.get_instance().play("click.wav")
        
        # تنظيف الكونسول
        self.console_output.clear()
        self.console_output.append(">>> INITIALIZING ALPHA BACKTEST ENGINE...")
        self.console_output.append(">>> PARSING STRATEGY...")
        
        # محاكاة تأخير المعالجة (لإعطاء شعور بالعمل)
        QTimer.singleShot(500, lambda: self._simulate_execution(code))

    def _simulate_execution(self, code):
        """دالة وهمية لمحاكاة النتائج (في الواقع سترسل الكود للباك إند)"""
        # هنا سيتم استدعاء StrategyManager الحقيقي لاحقاً
        
        # عرض نتائج وهمية للإثبات
        self.console_output.append(f"✅ Strategy Syntax: OK")
        self.console_output.append(f"📊 Market Data: BTC/USDT (1H)")
        self.console_output.append("-" * 40)
        self.console_output.append("SIMULATION STARTED...")
        self.console_output.append("[Day 1] BUY  @ 45,000 | Signal: RSI < 30")
        self.console_output.append("[Day 3] SELL @ 47,500 | Signal: RSI > 70")
        self.console_output.append("[Day 5] BUY  @ 46,200 | Signal: MACD Cross")
        self.console_output.append("-" * 40)
        self.console_output.append("🏁 SIMULATION COMPLETED.")
        self.console_output.append("💰 ESTIMATED PnL: +5.5%")
        
        SoundEngine.get_instance().play("success.wav")
        self.results_container.setCurrentIndex(0) # التركيز على الكونسول

    def _load_template_strategy(self):
        """كود افتراضي للبداية"""
        template = """
class MyStrategy(Strategy):
    def init(self):
        self.rsi = self.I(ta.rsi, self.data.Close, 14)

    def next(self):
        # الشراء إذا كان المؤشر أقل من 30
        if self.rsi[-1] < 30:
            self.buy()
            
        # البيع إذا كان المؤشر أعلى من 70
        elif self.rsi[-1] > 70:
            self.sell()
"""
        self.code_editor.set_code(template.strip())

    def _save_file(self):
        """حفظ الكود إلى ملف"""
        path, _ = QFileDialog.getSaveFileName(self, "Save Strategy", "", "Python Files (*.py)")
        if path:
            try:
                with open(path, 'w') as f:
                    f.write(self.code_editor.toPlainText())
                logger_sink.log_system_event("Lab", "SUCCESS", f"Strategy saved to {path}")
                SoundEngine.get_instance().play("success.wav")
            except Exception as e:
                logger_sink.log_system_event("Lab", "ERROR", f"Save failed: {e}")

    def _load_file(self):
        """فتح ملف"""
        path, _ = QFileDialog.getOpenFileName(self, "Open Strategy", "", "Python Files (*.py)")
        if path:
            try:
                with open(path, 'r') as f:
                    self.code_editor.set_code(f.read())
                logger_sink.log_system_event("Lab", "INFO", f"Strategy loaded from {path}")
            except Exception as e:
                logger_sink.log_system_event("Lab", "ERROR", f"Load failed: {e}")