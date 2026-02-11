from collections import deque
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect, QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QObject, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QIcon

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink

class ToastWidget(QWidget):
    """
    الإشعار المرئي الفعلي (The Bubble).
    """
    closed = pyqtSignal() # إشارة عند الانتهاء لتنظيف الذاكرة

    def __init__(self, title: str, message: str, level: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating) # لا تسرق التركيز من النافذة الرئيسية

        self.level = level.upper()
        self.setFixedSize(320, 80)

        # --- Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        
        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        
        # Message
        self.lbl_message = QLabel(message)
        self.lbl_message.setFont(QFont("Segoe UI", 9))
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setStyleSheet("color: #cccccc;") # لون افتراضي وسيتم تحديثه

        self.layout.addWidget(self.lbl_title)
        self.layout.addWidget(self.lbl_message)

        # --- Animation Setup ---
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(1)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(400)
        self.anim_out.setStartValue(1)
        self.anim_out.setEndValue(0)
        self.anim_out.finished.connect(self.close) # تدمير النافذة عند انتهاء الاختفاء

        # --- Auto-Close Timer ---
        self.life_timer = QTimer()
        self.life_timer.setSingleShot(True)
        self.life_timer.timeout.connect(self.start_fade_out)
        self.life_timer.start(4000) # يظهر لمدة 4 ثوانٍ

        # تطبيق الثيم
        self._apply_style()

    def _apply_style(self):
        """تلوين الإشعار حسب نوعه والثيم الحالي"""
        bg_color = theme_engine.get_color("surface")
        text_color = theme_engine.get_color("text_primary")
        border_color = "#444444"

        # تحديد لون الشريط الجانبي بناءً على النوع
        if self.level == "SUCCESS":
            accent_color = theme_engine.get_color("primary") # Green
        elif self.level == "ERROR" or self.level == "CRITICAL":
            accent_color = theme_engine.get_color("danger") # Red
        elif self.level == "WARNING":
            accent_color = theme_engine.get_color("secondary") # Cyan/Yellow
        else:
            accent_color = "#888888" # Gray for info

        # ستايل CSS مخصص مع حدود ملونة
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-left: 5px solid {accent_color};
                border-radius: 4px;
            }}
            QLabel {{
                border: none;
                color: {text_color};
                background-color: transparent;
            }}
        """)

    def start_fade_out(self):
        self.anim_out.start()

    def enterEvent(self, event):
        """إيقاف المؤقت عند مرور الماوس (Forensic Readability)"""
        self.life_timer.stop()
        self.setGraphicsEffect(None) # إزالة الشفافية لرؤية واضحة
        super().enterEvent(event)

    def leaveEvent(self, event):
        """استئناف الاختفاء عند إبعاد الماوس"""
        self.setGraphicsEffect(self.opacity_effect)
        self.life_timer.start(1000) # منح ثانية واحدة إضافية ثم الاختفاء
        super().leaveEvent(event)
    
    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class ToastManager(QObject):
    """
    مدير الإشعارات (The Traffic Controller).
    مسؤول عن إنشاء الإشعارات وتحديد أماكنها على الشاشة.
    """
    _instance = None

    def __init__(self):
        super().__init__()
        if ToastManager._instance is not None:
            raise Exception("ToastManager is a Singleton!")
        
        self.active_toasts = [] # قائمة الإشعارات الحالية
        self.queue = deque()    # طابور الانتظار
        self.max_visible = 4    # أقصى عدد يظهر معاً

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    def show_toast(self, title: str, message: str, level: str = "INFO"):
        """
        طلب عرض إشعار جديد.
        يمكن استدعاؤها من أي مكان في البرنامج.
        """
        # نضيفه للطابور أولاً
        self.queue.append((title, message, level))
        self._process_queue()

    def _process_queue(self):
        """محاولة عرض التالي في الطابور"""
        if len(self.active_toasts) >= self.max_visible:
            return # الشاشة ممتلئة

        if not self.queue:
            return # الطابور فارغ

        title, message, level = self.queue.popleft()
        
        # البحث عن النافذة الرئيسية لتحديد الموقع
        main_window = self._get_main_window()
        if not main_window:
            # إذا لم تكن الواجهة جاهزة بعد، نعيد العنصر للطابور
            self.queue.appendleft((title, message, level))
            return

        # إنشاء الـ Toast
        toast = ToastWidget(title, message, level, parent=main_window)
        
        # حساب الموقع (الزاوية اليمنى السفلية مع التكديس للأعلى)
        # نحسب الإزاحة بناءً على عدد الإشعارات الحالية
        idx = len(self.active_toasts)
        offset_y = 50 + (idx * 90) # 80 height + 10 margin
        
        geo = main_window.geometry()
        x_pos = geo.width() - 340 # 320 width + 20 margin
        y_pos = geo.height() - offset_y
        
        toast.move(x_pos, y_pos)
        toast.show()
        toast.anim_in.start()
        
        # تتبع الإشعار
        self.active_toasts.append(toast)
        
        # تنظيف القائمة عند الإغلاق
        toast.closed.connect(lambda: self._on_toast_closed(toast))

    def _on_toast_closed(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        # إعادة ترتيب الباقين (اختياري، أو ننتظر القادم)
        self._reposition_toasts()
        # محاولة عرض المزيد من الطابور
        self._process_queue()

    def _reposition_toasts(self):
        """تحريك الإشعارات الباقية لملء الفراغات (Slide Effect)"""
        main_window = self._get_main_window()
        if not main_window: return
        
        geo = main_window.geometry()
        x_pos = geo.width() - 340

        for idx, toast in enumerate(self.active_toasts):
            target_y = geo.height() - (50 + (idx * 90))
            # يمكن إضافة انيميشن للحركة هنا مستقبلاً
            toast.move(x_pos, target_y)

    def _get_main_window(self):
        """دالة مساعدة للعثور على النافذة الأم"""
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

# Global Accessor
toast_manager = ToastManager.get_instance()