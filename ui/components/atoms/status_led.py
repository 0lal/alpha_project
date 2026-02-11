from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

class StatusLED(QWidget):
    """
    مؤشر الحالة الضوئي (Forensic Status LED).
    يستخدم لرؤية حالة النظام (متصل/منقطع/خطر) بشكل فوري.
    """
    
    # تعريف الحالات
    OFF = 0
    OK = 1
    WARN = 2
    ERROR = 3
    SYNC = 4

    def __init__(self, size=12, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 4, size + 4)
        
        self._state = self.OK
        self._color = QColor("#00ff41") # Hacker Green الافتراضي
        self._tooltip = "System Operational"
        
        # للتأثير النبضي (Glow Effect)
        self._glow_alpha = 150
        self._glow_delta = -5
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_glow)
        self._timer.start(50)

    def set_status(self, state: int, message: str = ""):
        """تغيير حالة المؤشر"""
        self._state = state
        self._tooltip = message
        self.setToolTip(message)

        if state == self.OK:
            self._color = QColor("#00ff41")
        elif state == self.WARN:
            self._color = QColor("#ffb86c")
        elif state == self.ERROR:
            self._color = QColor("#ff5555")
        elif state == self.SYNC:
            self._color = QColor("#00ccff")
        else:
            self._color = QColor("#444444")
        
        self.update() # إعادة الرسم

    def _update_glow(self):
        """تحديث تأثير النبض"""
        self._glow_alpha += self._glow_delta
        if self._glow_alpha <= 50 or self._glow_alpha >= 200:
            self._glow_delta *= -1
        self.update()

    def paintEvent(self, event):
        """
        رسم المؤشر بدقة متناهية.
        تنبيه جنائي: يجب تحويل جميع الإحداثيات لـ int في PyQt6.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # الحسابات (مع التحويل الصريح لـ int)
        w = int(self.width())
        h = int(self.height())
        center_x = int(w / 2)
        center_y = int(h / 2)
        radius = int((min(w, h) - 4) / 2)

        # 1. رسم التوهج (Outer Glow)
        glow_color = QColor(self._color)
        glow_color.setAlpha(int(self._glow_alpha / 2))
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # رسم دائرة التوهج
        painter.drawEllipse(QPoint(center_x, center_y), radius + 2, radius + 2)

        # 2. رسم الجسم الأساسي (Core)
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
        
        # رسم الدائرة الأساسية (استخدام QPoint مع نصف قطر int)
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)

        # 3. رسم لمعة صغيرة (Highlight) لإعطاء شكل 3D
        highlight_color = QColor(255, 255, 255, 150)
        painter.setBrush(QBrush(highlight_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # رسم لمعة في الزاوية العلوية اليسرى
        lx = int(center_x - radius/2.5)
        ly = int(center_y - radius/2.5)
        lr = int(radius / 3)
        painter.drawEllipse(QPoint(lx, ly), lr, lr)
        
        painter.end() # إنهاء الرسام يدوياً للأمان ومنع Recursive Repaint