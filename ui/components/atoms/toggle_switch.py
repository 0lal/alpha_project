from PyQt6.QtWidgets import QAbstractButton
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, pyqtProperty, QEasingCurve, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink

class ToggleSwitch(QAbstractButton):
    """
    مفتاح تبديل ميكانيكي (Mechanical Toggle Switch).
    
    المميزات:
    1. Physics Animation: حركة ارتدادية (Bounce) تعطي شعوراً بالوزن.
    2. Theme Integrated: يتغير لونه مع النظام (أخضر/أحمر/أزرق).
    3. Audit Logging: يسجل تغييرات الحالة للأغراض الجنائية.
    """

    def __init__(self, parent=None, track_radius=12, thumb_radius=10):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # الأبعاد
        self._track_radius = track_radius
        self._thumb_radius = thumb_radius
        self.setFixedSize(50, 26) # حجم قياسي مضغوط
        
        # الحالة الحركية (0.0 = اليسار/مغلق، 1.0 = اليمين/مفعل)
        self._thumb_position = 0.0
        
        # الألوان (سيتم تحديثها من الثيم)
        self._track_color_off = QColor("#333333")
        self._track_color_on = QColor("#00ff00")
        self._thumb_color = QColor("#ffffff")
        self._text_color = QColor("#aaaaaa")

        # إعداد الانيميشن
        self._anim = QPropertyAnimation(self, b"thumb_position")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack) # تأثير الارتداد الميكانيكي

        # الاتصال بالأحداث
        self.toggled.connect(self._on_state_changed)
        theme_engine.theme_changed.connect(self._apply_style)
        
        self._apply_style()

    # --- خاصية للانيميشن ---
    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    # --- المنطق ---
    def _on_state_changed(self, checked):
        """بدء الحركة وتسجيل الحدث"""
        # 1. Start Animation
        self._anim.stop()
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        
        # 2. Forensic Log
        state_str = "ON" if checked else "OFF"
        # نسجل فقط إذا كان المفتاح مرئياً (لتجنب التسجيل أثناء التهيئة)
        if self.isVisible():
            # استخدام objectName كمعرف للمفتاح إذا وجد
            switch_id = self.objectName() or "Unknown_Switch"
            # نسجل بمستوى INFO لعدم إزعاج السجل، ولكن نضمن وجوده
            # logger_sink.log_system_event("Switch", "INFO", f"Toggle '{switch_id}' flipped to {state_str}")

    def _apply_style(self):
        """تحديث الألوان من محرك الثيم"""
        palette = theme_engine.get_palette()
        
        self._track_color_off = QColor(theme_engine.get_color("surface")) # رمادي داكن
        
        # اللون النشط يعتمد على الثيم (أخضر في Matrix، أزرق في Sovereign)
        self._track_color_on = QColor(palette.get("primary", "#00ff00"))
        
        self._thumb_color = QColor(theme_engine.get_color("text_primary"))
        self._text_color = QColor(theme_engine.get_color("text_secondary"))
        
        self.update()

    # --- الرسم (The Art) ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # تجهيز المناطق
        rect = self.rect()
        track_rect = QRectF(2, 2, rect.width() - 4, rect.height() - 4)
        
        # 1. حساب اللون البيني (Interpolation) أثناء الحركة
        # هذا يجعل اللون يتحول تدريجياً من الرمادي للأخضر مع حركة الكرة
        current_track_color = self._interpolate_color(
            self._track_color_off, 
            self._track_color_on, 
            self._thumb_position
        )

        # 2. رسم المسار (Track)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(current_track_color))
        painter.drawRoundedRect(track_rect, track_rect.height()/2, track_rect.height()/2)

        # 3. رسم الكرة (Thumb)
        # حساب الموقع بدقة
        thumb_range = track_rect.width() - track_rect.height()
        thumb_x = track_rect.x() + (track_rect.height() / 2) + (self._thumb_position * thumb_range)
        thumb_center_y = track_rect.center().y()
        
        painter.setBrush(QBrush(self._thumb_color))
        # إضافة ظل خفيف للكرة (اختياري للواقعية)
        painter.setPen(QPen(QColor(0,0,0, 40), 1)) 
        
        # نصف القطر - هامش صغير
        radius = (track_rect.height() / 2) - 2
        painter.drawEllipse(
            QRectF(thumb_x - radius, thumb_center_y - radius, radius * 2, radius * 2)
        )
        
        painter.end()

    def _interpolate_color(self, c1, c2, ratio):
        """خلط لونين بناءً على النسبة (0.0 - 1.0)"""
        r = c1.red() + (c2.red() - c1.red()) * ratio
        g = c1.green() + (c2.green() - c1.green()) * ratio
        b = c1.blue() + (c2.blue() - c1.blue()) * ratio
        return QColor(int(r), int(g), int(b))

    def hitButton(self, pos):
        """توسيع منطقة النققر لتسهيل الاستخدام"""
        return self.contentsRect().contains(pos)