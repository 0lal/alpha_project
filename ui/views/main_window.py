import sys
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, 
    QFrame, QLabel, QApplication, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QSettings, QTimer, QSize
from PyQt6.QtGui import QIcon, QColor, QMouseEvent, QAction

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.sound_engine import SoundEngine
from ui.core.logger_sink import logger_sink
from ui.core.config_provider import config

# --- استيراد المكونات ---
from ui.components.molecules.side_nav_bar import SideNavBar
from ui.components.atoms.status_led import StatusLED
from ui.components.atoms.modern_buttons import ActionButton

# --- استيراد الشاشات (Views) ---
# نستخدم Try-Import لمنع انهيار البرنامج بالكامل إذا كان هناك خطأ في ملف واحد
try:
    from ui.views.advisor.advisor_view import AdvisorView
except ImportError as e:
    logging.error(f"Failed to load AdvisorView: {e}")
    AdvisorView = None

try:
    from ui.views.cockpit.cockpit_view import CockpitView
except ImportError as e:
    logging.error(f"Failed to load CockpitView: {e}")
    CockpitView = None

try:
    from ui.views.lab.lab_view import LabView
except ImportError as e:
    logging.error(f"Failed to load LabView: {e}")
    LabView = None

try:
    from ui.views.settings.settings_view import SettingsView
except ImportError as e:
    logging.error(f"Failed to load SettingsView: {e}")
    SettingsView = None


class CustomTitleBar(QFrame):
    """
    شريط العنوان السيادي (Sovereign Title Bar).
    
    المهمة الجنائية:
    1. Drag Handler: السماح بسحب النافذة (لأننا ألغينا إطار الويندوز الأصلي).
    2. System Status: عرض حالة النظام (LED) في مكان دائم الرؤية.
    3. Quick Actions: أزرار الإغلاق والتصغير المخصصة.
    """
    def __init__(self, parent_window):
        super().__init__()
        self.window = parent_window
        self.setFixedHeight(40)
        self._apply_style()
        
        # ربط تغيير الثيم لتحديث اللون
        theme_engine.theme_changed.connect(lambda: self._apply_style())
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(10)
        
        # 1. مؤشر الحالة الأمني (System Health)
        self.led_status = StatusLED(size=10)
        self.led_status.set_status(StatusLED.OK, "System Secure")
        layout.addWidget(self.led_status)

        # 2. العنوان
        self.lbl_title = QLabel("ALPHA TERMINAL")
        self.lbl_title.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self.lbl_title)
        
        layout.addStretch()

        # 3. أزرار التحكم (Window Controls)
        # Minimize
        btn_min = ActionButton("-", color="#888888")
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.window.showMinimized)
        layout.addWidget(btn_min)
        
        # Close (Panic Exit)
        btn_close = ActionButton("✕", color="#ff5555")
        btn_close.setFixedSize(30, 30)
        btn_close.clicked.connect(self.window.close)
        layout.addWidget(btn_close)

    def _apply_style(self):
        bg = theme_engine.get_color("background") # نفس لون الخلفية للاندماج
        border = theme_engine.get_color("grid_line")
        self.setStyleSheet(f"background-color: {bg}; border-bottom: 1px solid {border};")

    # --- منطق سحب النافذة (Dragging Logic) ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window.drag_pos = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.window.drag_pos:
            self.window.move(event.globalPosition().toPoint() - self.window.drag_pos)
            event.accept()


class MainWindow(QMainWindow):
    """
    المركبة الأم (The Mothership).
    
    الهيكلة:
    - Frameless: سيطرة كاملة على البيكسلات.
    - Stacked Architecture: تحميل كل الشاشات في الذاكرة لسرعة التبديل.
    - State Persistence: تذكر مكان وحجم النافذة وآخر شاشة مفتوحة.
    """
    def __init__(self):
        super().__init__()
        
        # إعدادات النافذة الأساسية
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # متغيرات السحب
        self.drag_pos = None

        # 1. الحاوية المركزية
        self.central_widget = QWidget()
        self.central_widget.setObjectName("RootContainer") # للستايل
        self.setCentralWidget(self.central_widget)
        
        # تطبيق الثيم وتحديثه
        self._apply_root_theme()
        theme_engine.theme_changed.connect(self._apply_root_theme)

        # 2. التخطيط الرئيسي (أفقي: قائمة جانبية + محتوى)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 3. القائمة الجانبية (Sidebar)
        self.side_nav = SideNavBar()
        self.side_nav.page_changed.connect(self.switch_page)
        self.main_layout.addWidget(self.side_nav)

        # 4. حاوية المحتوى (عمودي: شريط عنوان + شاشات)
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # A. شريط العنوان المخصص
        self.title_bar = CustomTitleBar(self)
        self.content_layout.addWidget(self.title_bar)

        # B. مكدس الشاشات (The Views Stack)
        self.pages_stack = QStackedWidget()
        self.content_layout.addWidget(self.pages_stack)

        self.main_layout.addWidget(self.content_container)

        # 5. تحميل الشاشات
        self._init_views()

        # 6. استعادة الحالة السابقة (Forensic State Restoration)
        self._restore_session_state()

        # تشغيل صوت الإقلاع
        QTimer.singleShot(500, lambda: SoundEngine.get_instance().play("success.wav"))
        logger_sink.log_system_event("MainWindow", "INFO", "🚀 Alpha System Online.")

    def _init_views(self):
        """
        تهيئة وتحميل الشاشات.
        نستخدم الـ Fail-Safe: إذا فشلت شاشة، نضع مكانها رسالة خطأ بدلاً من انهيار البرنامج.
        """
        # Index 0: Advisor (Chat)
        if AdvisorView:
            self.pages_stack.addWidget(AdvisorView())
        else:
            self._add_error_placeholder("Advisor Module Failed")

        # Index 1: Cockpit (Dashboard)
        if CockpitView:
            self.pages_stack.addWidget(CockpitView())
        else:
            self._add_error_placeholder("Cockpit Module Failed")

        # Index 2: Lab (Strategy)
        if LabView:
            self.pages_stack.addWidget(LabView())
        else:
            self._add_error_placeholder("Lab Module Failed")

        # Index 3: Settings
        if SettingsView:
            self.pages_stack.addWidget(SettingsView())
        else:
            self._add_error_placeholder("Settings Module Failed")

        # Index 4: Forensics (Future)
        self._add_error_placeholder("Forensics Module (Under Construction)")

    def _add_error_placeholder(self, message: str):
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #ff5555; font-size: 14px; font-weight: bold;")
        self.pages_stack.addWidget(lbl)

    def switch_page(self, page_id: str):
        """التنقل بين الصفحات"""
        logger_sink.log_system_event("Nav", "INFO", f"Switching to {page_id}")
        
        # Mapping between Sidebar IDs and Stack Indexes
        # يجب أن يتطابق هذا مع ترتيب الإضافة في _init_views
        mapping = {
            "advisor_view": 0,
            "dashboard_view": 1, # Cockpit
            "strategy_view": 2,  # Lab
            "settings_view": 3,
            "forensics_view": 4
        }
        
        index = mapping.get(page_id, 0)
        self.pages_stack.setCurrentIndex(index)
        
        # تأثير صوتي خفيف
        SoundEngine.get_instance().play("click.wav")

    def _apply_root_theme(self):
        """تلوين الإطار الخارجي"""
        bg = theme_engine.get_color("background")
        border = theme_engine.get_color("grid_line")
        
        # نستخدم Border Radius لإعطاء شكل حديث للنافذة ككل
        self.central_widget.setStyleSheet(f"""
            #RootContainer {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 5px; 
            }}
        """)

    def _restore_session_state(self):
        """استعادة مكان النافذة وحجمها"""
        settings = QSettings("AlphaSystems", "AlphaTerminal")
        
        # استعادة الهندسة (المكان والحجم)
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1280, 850)

    def closeEvent(self, event):
        """
        بروتوكول الإغلاق الآمن.
        """
        logger_sink.log_system_event("MainWindow", "WARN", "Initiating shutdown protocol...")
        
        # حفظ الحالة
        settings = QSettings("AlphaSystems", "AlphaTerminal")
        settings.setValue("geometry", self.saveGeometry())
        
        logger_sink.log_system_event("MainWindow", "INFO", "Session Saved. Shutdown complete.")
        event.accept()