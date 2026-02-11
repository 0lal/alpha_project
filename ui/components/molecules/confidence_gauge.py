from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient, QBrush

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine

class ConfidenceGauge(QWidget):
    """
    مقياس ثقة دائري متقدم (Radial Confidence Gauge).
    
    المميزات:
    1. GPU-Style Rendering: رسم مخصص باستخدام QPainter لأقصى دقة.
    2. Dynamic Zones: يتلون بناءً على قيمة الثقة (أحمر -> أصفر -> أخضر).
    3. Animated: حركة انسيابية للمؤشر لمنع التشتت البصري.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120) # حجم مثالي للوحة القيادة
        
        # القيمة الحالية (0.0 إلى 1.0)
        self._confidence = 0.0
        self._displayed_value = 0.0 # القيمة أثناء الانيميشن
        
        # إعداد الانيميشن
        self._anim = QPropertyAnimation(self, b"displayed_value")
        self._anim.setDuration(600) # حركة ناعمة خلال 0.6 ثانية
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack) # تأثير ارتداد خفيف (Mechanical feel)

        # ربط الثيم
        theme_engine.theme_changed.connect(self.update)

    # --- Property for Animation ---
    @pyqtProperty(float)
    def displayed_value(self):
        return self._displayed_value

    @displayed_value.setter
    def displayed_value(self, val):
        self._displayed_value = val
        self.update() # إعادة الرسم عند كل إطار

    # --- Public API ---
    def set_confidence(self, value: float):
        """
        تحديث قيمة الثقة.
        value: رقم بين 0.0 و 1.0
        """
        # تقييد القيمة (Clamping)
        target = max(0.0, min(1.0, value))
        self._confidence = target
        
        # بدء الانيميشن نحو القيمة الجديدة
        self._anim.stop()
        self._anim.setStartValue(self._displayed_value)
        self._anim.setEndValue(target * 100) # نحولها لنسبة مئوية للرسم
        self._anim.start()

    # --- Painting Logic (الرسم اليدوي) ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # الأبعاد
        width = self.width()
        height = self.height()
        rect = QRectF(10, 10, width - 20, height - 20)
        
        # 1. الخلفية (Track)
        track_color = QColor(theme_engine.get_color("surface"))
        track_pen = QPen(track_color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        # نرسم قوساً بمقدار 270 درجة (مفتوح من الأسفل)
        # startAngle: 225 درجة (الساعة 7:30)، spanAngle: -270 (عكس عقارب الساعة)
        painter.drawArc(rect, 225 * 16, -270 * 16)

        # 2. تحديد لون المؤشر (Zone Logic)
        val = self._displayed_value
        if val < 60:
            bar_color = QColor(theme_engine.get_color("danger")) # أحمر
        elif val < 80:
            bar_color = QColor(theme_engine.get_color("secondary")) # أصفر/سماوي
        else:
            bar_color = QColor(theme_engine.get_color("chart_up")) # أخضر

        # 3. شريط التقدم (Progress Arc)
        progress_pen = QPen(bar_color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)
        
        # حساب الزاوية بناءً على القيمة
        span = -270 * (val / 100.0)
        if abs(span) > 0.1: # رسم فقط إذا كانت هناك قيمة
            painter.drawArc(rect, 225 * 16, int(span * 16))

        # 4. النص الرقمي (Digital Readout)
        painter.setPen(theme_engine.get_color("text_primary"))
        font_val = QFont("Consolas", 22, QFont.Weight.Bold)
        painter.setFont(font_val)
        
        text_rect = QRectF(0, 0, width, height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{int(val)}%")

        # 5. التسمية (Label)
        painter.setPen(theme_engine.get_color("text_secondary"))
        font_lbl = QFont("Segoe UI", 9)
        painter.setFont(font_lbl)
        
        # رسم كلمة "CONFIDENCE" أسفل الرقم
        lbl_rect = QRectF(0, 25, width, height) # إزاحة للأسفل
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, "AI TRUST")

        painter.end()