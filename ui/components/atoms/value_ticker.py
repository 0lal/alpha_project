from PyQt6.QtWidgets import QLabel, QGraphicsColorizeEffect
from PyQt6.QtCore import Qt, QTimer, pyqtProperty, QPropertyAnimation, QEasingCurve, QObject
from PyQt6.QtGui import QColor, QPalette, QFont

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine

class ValueTicker(QLabel):
    """
    عداد رقمي ذكي (Smart Ticker Atom).
    
    المميزات:
    1. Tick Flash: وميض لوني عند تغير القيمة (أخضر للصعود، أحمر للهبوط).
    2. Monospace Font: أرقام ثابتة العرض لمنع اهتزاز الليآوت.
    3. Performance Optimized: يستخدم QGraphicsColorizeEffect لتلوين النص بفاعلية GPU.
    """

    def __init__(self, initial_value="0.00", parent=None):
        super().__init__(str(initial_value), parent)
        
        # الحالة الداخلية
        self._last_value = 0.0
        self._base_color = QColor("#ffffff") # سيتم تحديثه من الثيم
        
        # إعداد الخط (Consolas للأرقام هو الأفضل)
        self.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # تأثير التلوين (Colorize Effect) - أسرع من تغيير الـ Stylesheet
        self.color_effect = QGraphicsColorizeEffect(self)
        self.color_effect.setColor(self._base_color)
        self.setGraphicsEffect(self.color_effect)

        # إعداد الانيميشن (عودة اللون للأصل)
        self._anim = QPropertyAnimation(self.color_effect, b"color")
        self._anim.setDuration(800) # مدة الوميض 800ms
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        # ربط الثيم
        theme_engine.theme_changed.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self):
        """تحديث اللون الأساسي من الثيم"""
        # نستخدم لون النص الأساسي كلون "الراحة"
        self._base_color = QColor(theme_engine.get_color("text_primary"))
        
        # إذا لم يكن هناك انيميشن يعمل حالياً، نطبق اللون فوراً
        if self._anim.state() != QPropertyAnimation.State.Running:
            self.color_effect.setColor(self._base_color)

    def set_value(self, new_value: float, fmt: str = "{:,.2f}", flash: bool = True):
        """
        تحديث القيمة مع تأثير بصري.
        """
        try:
            current_val = float(new_value)
        except ValueError:
            self.setText(str(new_value))
            return

        # تحديث النص
        self.setText(fmt.format(current_val))

        if not flash:
            self._last_value = current_val
            return

        # تحديد اتجاه التغيير
        if current_val > self._last_value:
            flash_color = QColor(theme_engine.get_color("chart_up")) # Green
            self._trigger_flash(flash_color)
        elif current_val < self._last_value:
            flash_color = QColor(theme_engine.get_color("chart_down")) # Red
            self._trigger_flash(flash_color)
        
        self._last_value = current_val

    def _trigger_flash(self, color: QColor):
        """تشغيل وميض اللون والعودة للتدريج"""
        self._anim.stop()
        
        # نبدأ من لون الوميض (أخضر/أحمر)
        self.color_effect.setColor(color)
        
        # نعود تدريجياً للون الأساسي (أبيض/رمادي)
        self._anim.setStartValue(color)
        self._anim.setEndValue(self._base_color)
        self._anim.start()

    def set_font_size(self, size: int):
        f = self.font()
        f.setPointSize(size)
        self.setFont(f)