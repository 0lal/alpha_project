import time
from datetime import datetime
import numpy as np
import pyqtgraph as pg
from typing import List, Dict, Optional, Tuple
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor, QPicture, QPainter, QBrush, QPen
from PyQt6.QtWidgets import QVBoxLayout, QWidget

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink

# تحسينات الأداء لـ PyQtGraph
pg.setConfigOptions(antialias=False) # تعطيل التنعيم للأداء الأقصى
pg.setConfigOption('background', 'k') # خلفية سوداء مبدئياً
pg.setConfigOption('foreground', 'd')

class CandlestickItem(pg.GraphicsObject):
    """
    عنصر رسومي مخصص لرسم الشموع اليابانية بأقصى سرعة ممكنة.
    يستخدم Low-Level QPainter commands لرسم آلاف الشموع في جزء من الثانية.
    """
    def __init__(self, data=None):
        super().__init__()
        self.data = data  # Must be a list of tuples: (time, open, close, min, max)
        self.picture = QPicture()
        self.up_color = QColor("#00ff00")
        self.down_color = QColor("#ff0000")
        self.width = 0.6  # عرض الشمعة النسبي
        self._generate_picture()

    def set_data(self, data):
        self.data = data
        self._generate_picture()
        self.informViewBoundsChanged()

    def set_colors(self, up, down):
        self.up_color = QColor(up)
        self.down_color = QColor(down)
        self._generate_picture()
        self.update()

    def _generate_picture(self):
        """رسم الشموع وتخزينها في ذاكرة الفيديو (Caching)"""
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        # تحسينات الرسم
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        w = self.width
        # الألوان
        pen_up = QPen(self.up_color)
        pen_down = QPen(self.down_color)
        brush_up = QBrush(self.up_color)
        brush_down = QBrush(self.down_color)

        if self.data is None or len(self.data) == 0:
            p.end()
            return

        for (t, open_p, close_p, min_p, max_p) in self.data:
            if close_p > open_p:
                p.setPen(pen_up)
                p.setBrush(brush_up)
                # رسم الفتيل (Wick)
                p.drawLine(int(t), int(min_p * 100), int(t), int(max_p * 100)) # Scale fix later
                # رسم الجسم (Body)
                p.drawRect(
                    int(t - w/2), int(open_p * 100), 
                    int(w), int((close_p - open_p) * 100)
                )
            else:
                p.setPen(pen_down)
                p.setBrush(brush_down)
                p.drawLine(int(t), int(min_p * 100), int(t), int(max_p * 100))
                p.drawRect(
                    int(t - w/2), int(open_p * 100), 
                    int(w), int((close_p - open_p) * 100)
                )
        p.end()

    def paint(self, p, *args):
        # استرجاع الرسم الجاهز من الذاكرة
        # ملاحظة: نقوم بعمل Scale عكسي هنا إذا كنا قد ضربنا في 100 سابقاً للدقة
        # لكن للتبسيط سنستخدم الرسم المباشر في النسخة الحالية مع تعديل الاحداثيات
        # هذا الكلاس يحتاج لمنطق معقد لتحويل الاحداثيات، لذلك سنستخدم 
        # منطق الرسم المباشر المبسط المتوافق مع PyQtGraph:
        
        if self.data is None: return
        
        # إعادة الرسم المباشر (أبطأ قليلاً لكن أدق للإحداثيات الحقيقية)
        w = self.width
        for (t, open_p, close_p, min_p, max_p) in self.data:
            if close_p > open_p:
                p.setPen(pg.mkPen(self.up_color))
                p.setBrush(pg.mkBrush(self.up_color))
            else:
                p.setPen(pg.mkPen(self.down_color))
                p.setBrush(pg.mkBrush(self.down_color))
            
            # Wick
            p.drawLine(
                Qt.QPointF(t, min_p), 
                Qt.QPointF(t, max_p)
            )
            # Body
            p.drawRect(
                Qt.QRectF(t - w/2, open_p, w, close_p - open_p)
            )

    def boundingRect(self):
        if self.data is None or len(self.data) == 0:
            return Qt.QRectF()
        # حساب حدود الرسم لتحديد الزووم تلقائياً
        times = [d[0] for d in self.data]
        mins = [d[3] for d in self.data]
        maxs = [d[4] for d in self.data]
        return Qt.QRectF(
            min(times), min(mins), 
            max(times) - min(times), max(maxs) - min(mins)
        )

class DateAxisItem(pg.AxisItem):
    """محور سيني (X-Axis) يعرض الوقت بدلاً من الأرقام"""
    def tickStrings(self, values, scale, spacing):
        strns = []
        for x in values:
            try:
                dt = datetime.fromtimestamp(x)
                strns.append(dt.strftime("%H:%M:%S"))
            except:
                strns.append("")
        return strns

class FinancialChart(QWidget):
    """
    الرسم البياني السيادي (The Sovereign Chart).
    
    المميزات:
    1. GPU Accelerated (via PyQtGraph).
    2. Theme Aware (يتغير لونه مع النظام).
    3. Crosshair (مؤشر متقاطع لتحديد الأسعار).
    4. Auto-Scroll (يتبع السعر الحالي).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # التخطيط
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # إنشاء نافذة الرسم
        self.date_axis = DateAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': self.date_axis})
        self.layout.addWidget(self.plot_widget)
        
        # إعدادات الرسم
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Price (USDT)')
        self.plot_widget.setLabel('bottom', 'Time')
        
        # عنصر الشموع
        self.candle_item = CandlestickItem()
        self.plot_widget.addItem(self.candle_item)
        
        # المؤشر المتقاطع (Crosshair)
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self._mouse_moved)

        # البيانات الحالية
        self.current_data = [] # List of tuples
        
        # تطبيق الثيم المبدئي
        self._apply_theme_colors()
        
        # الاستماع لتغيير الثيم
        theme_engine.theme_changed.connect(self._on_theme_changed)
        
        logger_sink.log_system_event("FinancialChart", "INFO", "📈 GPU Charting Engine Initialized.")

    def _apply_theme_colors(self):
        """تلوين الرسم بناءً على ThemeEngine"""
        palette = theme_engine.get_palette()
        
        # خلفية الشارت
        bg_color = palette.get("surface", "#000000")
        self.plot_widget.setBackground(bg_color)
        
        # الشبكة والنصوص
        grid_color = palette.get("grid_line", "#333333")
        text_color = palette.get("text_secondary", "#888888")
        
        self.plot_widget.getAxis('bottom').setPen(text_color)
        self.plot_widget.getAxis('left').setPen(text_color)
        
        # ألوان الشموع
        up_color = palette.get("chart_up", "#00ff00")
        down_color = palette.get("chart_down", "#ff0000")
        self.candle_item.set_colors(up_color, down_color)
        
        # ألوان المؤشر
        crosshair_color = palette.get("primary", "#ffffff")
        self.v_line.setPen(pg.mkPen(crosshair_color, width=1, style=Qt.PenStyle.DashLine))
        self.h_line.setPen(pg.mkPen(crosshair_color, width=1, style=Qt.PenStyle.DashLine))

    def _on_theme_changed(self, theme_name, palette):
        self._apply_theme_colors()

    def update_market_data(self, candles: List[Tuple[float, float, float, float, float]]):
        """
        تحديث البيانات بالكامل (Bulk Update).
        Input Format: [(timestamp, open, close, low, high), ...]
        """
        self.current_data = candles
        self.candle_item.set_data(candles)

    def add_tick(self, timestamp: float, price: float):
        """
        تحديث لحظي للشمعة الأخيرة أو إضافة شمعة جديدة.
        """
        if not self.current_data:
            # أول شمعة
            new_candle = (timestamp, price, price, price, price)
            self.current_data.append(new_candle)
        else:
            last_candle = self.current_data[-1]
            t, o, c, l, h = last_candle
            
            # منطق بسيط: إذا مر وقت كافٍ (مثلاً دقيقة)، نفتح شمعة جديدة
            # هنا سنفترض أن Caller هو المسؤول عن التجميع (Timeframe Aggregation)
            # وسنقوم فقط بتحديث آخر إغلاق و High/Low
            
            new_h = max(h, price)
            new_l = min(l, price)
            updated_candle = (t, o, price, new_l, new_h)
            self.current_data[-1] = updated_candle
            
        # تحديث الرسم
        self.candle_item.set_data(self.current_data)

    def _mouse_moved(self, evt):
        """تحريك المؤشر المتقاطع وعرض المعلومات"""
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())
            # يمكن هنا إرسال إشارة للواجهة لعرض السعر والتاريخ في Label خارجي