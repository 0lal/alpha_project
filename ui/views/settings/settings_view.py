import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QComboBox, QGroupBox, QScrollArea, QFormLayout,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

# --- استيراد البنية التحتية ---
from ui.core.config_provider import config
from ui.core.theme_engine import theme_engine
from ui.core.sound_engine import SoundEngine
from ui.components.atoms.modern_buttons import ModernButton, ActionButton
from ui.components.atoms.toggle_switch import ToggleSwitch

logger = logging.getLogger("Alpha.Settings")

class SettingsView(QWidget):
    """
    مركز التحكم في الإعدادات (Control Center).
    
    المهمة:
    1. إدارة مفاتيح API بأمان (Visual Masking).
    2. تخصيص المظهر (Themes) والصوت.
    3. إعدادات المخاطر (Risk Management Configuration).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # تخطيط الصفحة الرئيسي
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # عنوان الصفحة
        lbl_title = QLabel("SYSTEM CONFIGURATION")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {theme_engine.get_color('primary')};")
        self.main_layout.addWidget(lbl_title)

        # منطقة التمرير (لضمان عدم اختفاء الإعدادات في الشاشات الصغيرة)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(25)
        
        # --- بناء الأقسام ---
        self._build_api_section()      # مفاتيح البورصة والذكاء الاصطناعي
        self._build_appearance_section() # الثيمات والخطوط
        self._build_risk_section()     # إدارة المخاطر
        self._build_audio_section()    # إعدادات الصوت
        
        # إضافة فراغ في الأسفل
        self.content_layout.addStretch()
        
        scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(scroll)

        # --- شريط الأزرار السفلي (Save / Reset) ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = ModernButton("SAVE CONFIGURATION", color="#00ff41") # Green
        self.btn_save.setFixedWidth(200)
        self.btn_save.clicked.connect(self._save_settings)
        
        btn_layout.addWidget(self.btn_save)
        self.main_layout.addLayout(btn_layout)

        # تحميل الإعدادات الحالية
        self._load_current_settings()
        
        # تطبيق الثيم
        theme_engine.theme_changed.connect(self._apply_theme)
        self._apply_theme()

    # =========================================================================
    # 1. API Keys Section (The Vault)
    # =========================================================================
    def _build_api_section(self):
        group = QGroupBox("🔐 API CONNECTIONS")
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setSpacing(10)

        # Binance Key
        self.txt_binance_key = self._create_password_input()
        layout.addRow("Binance API Key:", self.txt_binance_key)

        # Binance Secret
        self.txt_binance_secret = self._create_password_input()
        layout.addRow("Binance Secret:", self.txt_binance_secret)

        # OpenAI Key (المستشار الذكي)
        self.txt_openai_key = self._create_password_input()
        layout.addRow("OpenAI / Gemini Key:", self.txt_openai_key)
        
        # زر اختبار الاتصال (وهمي حالياً)
        btn_test = ActionButton("TEST CONNECTION", color="#00ccff")
        btn_test.setFixedWidth(150)
        btn_test.clicked.connect(lambda: SoundEngine.get_instance().play("success.wav"))
        layout.addRow("", btn_test)

        self.content_layout.addWidget(group)

    def _create_password_input(self) -> QLineEdit:
        """إنشاء حقل إدخال محمي (Masked) مع إمكانية الإظهار"""
        inp = QLineEdit()
        inp.setEchoMode(QLineEdit.EchoMode.Password) # النجوم ****
        inp.setPlaceholderText("Paste key here...")
        
        # يمكن إضافة زر "عين" هنا للإظهار (سأكتفي بالتبسيط للأمان)
        return inp

    # =========================================================================
    # 2. Appearance Section (Visuals)
    # =========================================================================
    def _build_appearance_section(self):
        group = QGroupBox("🎨 APPEARANCE")
        layout = QFormLayout(group)

        # Theme Selector
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["sovereign_dark", "matrix_green"])
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed) # Live Preview
        layout.addRow("Interface Theme:", self.combo_theme)

        # Transparency Toggle (Window opacity)
        self.chk_transparency = ToggleSwitch()
        layout.addRow("Glass Effect:", self.chk_transparency)

        self.content_layout.addWidget(group)

    # =========================================================================
    # 3. Risk Management Section (Safety)
    # =========================================================================
    def _build_risk_section(self):
        group = QGroupBox("🛡️ RISK MANAGEMENT")
        layout = QFormLayout(group)

        # Max Risk Per Trade
        self.inp_risk_per_trade = QLineEdit()
        self.inp_risk_per_trade.setPlaceholderText("e.g. 1.0")
        layout.addRow("Max Risk Per Trade (%):", self.inp_risk_per_trade)

        # Max Open Trades
        self.inp_max_trades = QLineEdit()
        self.inp_max_trades.setPlaceholderText("e.g. 3")
        layout.addRow("Max Open Trades:", self.inp_max_trades)
        
        # Panic Button Mode
        self.chk_auto_panic = ToggleSwitch()
        layout.addRow("Auto-Panic on 5% Drop:", self.chk_auto_panic)

        self.content_layout.addWidget(group)

    # =========================================================================
    # 4. Audio Section
    # =========================================================================
    def _build_audio_section(self):
        group = QGroupBox("🔊 AUDIO FEEDBACK")
        layout = QHBoxLayout(group)
        
        self.chk_sound_enabled = ToggleSwitch()
        self.chk_sound_enabled.setChecked(True)
        
        btn_test_sound = ActionButton("Test Sounds")
        btn_test_sound.clicked.connect(lambda: SoundEngine.get_instance().play("panic.wav"))
        
        layout.addWidget(QLabel("Enable UI Sounds:"))
        layout.addWidget(self.chk_sound_enabled)
        layout.addStretch()
        layout.addWidget(btn_test_sound)
        
        self.content_layout.addWidget(group)

    # =========================================================================
    # Logic & Persistence
    # =========================================================================
    
    def _load_current_settings(self):
        """قراءة الإعدادات من الملف وعرضها"""
        # ملاحظة: في التطبيق الحقيقي، لا تخزن المفاتيح كنص واضح.
        # هنا نفترض أن config.get يفك التشفير إذا لزم الأمر.
        self.txt_binance_key.setText(config.get("api.binance.key", ""))
        self.txt_binance_secret.setText(config.get("api.binance.secret", ""))
        self.txt_openai_key.setText(config.get("api.openai.key", ""))
        
        current_theme = config.get("theme", "sovereign_dark")
        self.combo_theme.setCurrentText(current_theme)
        
        self.inp_risk_per_trade.setText(str(config.get("risk.percent", "1.0")))
        self.inp_max_trades.setText(str(config.get("risk.max_trades", "3")))

    def _save_settings(self):
        """حفظ الإعدادات والتحقق منها"""
        # 1. Input Sanitization (تنظيف المدخلات)
        b_key = self.txt_binance_key.text().strip()
        b_secret = self.txt_binance_secret.text().strip()
        ai_key = self.txt_openai_key.text().strip()
        
        # 2. Update Config Object
        config.set("api.binance.key", b_key)
        config.set("api.binance.secret", b_secret)
        config.set("api.openai.key", ai_key)
        
        config.set("theme", self.combo_theme.currentText())
        
        try:
            risk = float(self.inp_risk_per_trade.text())
            config.set("risk.percent", risk)
        except ValueError:
            pass # Ignore invalid numbers
            
        # 3. Write to Disk
        config.save()
        
        # 4. Feedback
        SoundEngine.get_instance().play("success.wav")
        # يمكن إضافة Toast Notification هنا مستقبلاً
        logger.info("Configuration saved successfully.")

    def _on_theme_changed(self, text):
        """تطبيق الثيم فوراً عند الاختيار (Live Preview)"""
        theme_engine.apply_theme(text)

    def _apply_theme(self):
        """تحديث ستايل الصفحة نفسها"""
        # نعتمد على QSS العام، لكن يمكن إضافة تخصيصات هنا
        pass