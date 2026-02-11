from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from ui.core.theme_engine import theme_engine

class StatCard(QFrame):
    """
    بطاقة إحصائيات (Stat Card).
    تعرض عنواناً وقيمة (مثلاً: الرصيد، الربح).
    
    المميزات:
    - تلوين ذكي للقيمة (أخضر للربح، أحمر للخسارة).
    - دعم الثيمات.
    """
    def __init__(self, title: str, value: str = "0.00", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.value_text = value
        
        # إعداد الإطار
        self.setFixedSize(160, 90) # حجم ثابت ومناسب
        
        # التخطيط الداخلي
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)
        
        # العنوان
        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_title)
        
        # القيمة
        self.lbl_value = QLabel(self.value_text)
        self.lbl_value.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_value)
        
        # إضافة ظل خفيف
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        # تطبيق الثيم
        self._apply_theme()
        theme_engine.theme_changed.connect(self._apply_theme)

    def update_value(self, value: float, prefix: str = "$", suffix: str = ""):
        """تحديث القيمة وتلوينها"""
        # تحويل الرقم لنص
        if isinstance(value, (int, float)):
            txt = f"{prefix}{value:,.2f}{suffix}"
            if value > 0:
                txt = f"+{txt}" # إضافة علامة موجب
        else:
            txt = str(value)
            
        self.value_text = txt
        self.lbl_value.setText(txt)
        
        # تلوين القيمة بناءً على الرقم
        # نستخدم دالة منفصلة للتلوين لا تستدعي _apply_theme لتجنب الحلقة المفرغة
        self._colorize_value(value)

    def _colorize_value(self, value):
        """تغيير لون النص فقط دون إعادة رسم البطاقة بالكامل"""
        if isinstance(value, (int, float)):
            if value > 0:
                col = theme_engine.get_color("chart_up") # Green
            elif value < 0:
                col = theme_engine.get_color("chart_down") # Red
            else:
                col = theme_engine.get_color("text_primary")
        else:
            col = theme_engine.get_color("text_primary")
            
        # تحديث ستايل الليبل فقط
        self.lbl_value.setStyleSheet(f"color: {col}; border: none; background: transparent;")

    def _apply_theme(self):
        """تطبيق ألوان الثيم الأساسية (الخلفية والعنوان)"""
        bg = theme_engine.get_color("surface")
        title_col = theme_engine.get_color("text_secondary")
        border = theme_engine.get_color("grid_line")
        
        # ستايل الإطار الرئيسي
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)
        
        # ستايل العنوان
        self.lbl_title.setStyleSheet(f"color: {title_col}; border: none; background: transparent;")
        
        # إعادة تلوين القيمة الحالية (لضمان تناسقها مع الثيم الجديد)
        # نحاول تخمين القيمة رقمياً لإعادة التلوين، أو نستخدم اللون الافتراضي
        try:
            # محاولة استخراج رقم من النص لتلوينه
            clean_val = self.value_text.replace("$", "").replace(",", "").replace("+", "")
            val_float = float(clean_val)
            self._colorize_value(val_float)
        except ValueError:
            # إذا لم يكن رقماً، نستخدم لون النص الأساسي
            primary_col = theme_engine.get_color("text_primary")
            self.lbl_value.setStyleSheet(f"color: {primary_col}; border: none; background: transparent;")