from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QCursor

from ui.core.theme_engine import theme_engine

class ModernButton(QPushButton):
    """
    زر حديث يدعم تخصيص اللون والنص.
    """
    def __init__(self, text: str, color: str = None, parent=None):
        # لاحظ إضافة color=None هنا في التعريف
        super().__init__(text, parent)
        
        # اللون الافتراضي هو اللون الأساسي للثيم إذا لم يحدد المستخدم لوناً
        self.accent_color = color if color else theme_engine.get_color("primary")
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(35)
        
        # تطبيق الستايل المبدئي
        self._apply_style()
        
        # تحديث الستايل عند تغيير الثيم
        theme_engine.theme_changed.connect(self._update_theme_color)

    def _update_theme_color(self):
        # إذا لم يكن اللون مخصصاً (None)، نحدثه مع الثيم
        # أما إذا كان مخصصاً (مثل الأحمر للإغلاق)، نتركه كما هو
        # لكننا هنا سنعيد تطبيق الستايل لضمان تحديث الخلفيات
        self._apply_style()

    def _apply_style(self):
        text_col = theme_engine.get_color("text_primary")
        bg_surface = theme_engine.get_color("surface")
        
        # استخدام اللون المحدد
        c = self.accent_color
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_surface};
                color: {c};
                border: 1px solid {c};
                border-radius: 4px;
                font-weight: bold;
                padding: 5px 15px;
                font-family: "Segoe UI";
            }}
            QPushButton:hover {{
                background-color: {c};
                color: {theme_engine.get_color("background")};
            }}
            QPushButton:pressed {{
                background-color: {bg_surface};
                color: {c};
                border: 2px solid {c};
            }}
            QPushButton:disabled {{
                color: #555555;
                border: 1px solid #333333;
                background-color: transparent;
            }}
        """)

class ActionButton(ModernButton):
    """
    زر إجراءات صغيرة (أيقونات أو نصوص قصيرة) مثل أزرار النافذة العلوية.
    """
    def __init__(self, text: str, color: str = None, parent=None):
        super().__init__(text, color, parent)
        self.setFixedSize(30, 30)
        
        # ستايل أبسط قليلاً (بدون حدود بارزة إلا عند التحويم)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.accent_color};
                border: none;
                font-weight: bold;
                font-size: 14px;
                border-radius: 15px; /* دائري */
            }}
            QPushButton:hover {{
                background-color: {self.accent_color};
                color: #ffffff;
            }}
        """)