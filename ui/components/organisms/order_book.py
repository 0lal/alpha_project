from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QLabel, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QBrush, QLinearGradient, QFont

# --- استيراد البنية التحتية ---
from ui.core.event_hub import event_hub
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink

class OrderBookTable(QTableWidget):
    """
    جدول مخصص لعرض جانب واحد من الكتاب (Bids أو Asks).
    يدعم رسم أشرطة العمق (Depth Bars) في الخلفية.
    """
    def __init__(self, is_bids=True):
        super().__init__()
        self.is_bids = is_bids
        
        # إعداد الأعمدة: Price, Amount, Total
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Price", "Amount", "Total"])
        
        # إخفاء الرؤوس الجانبية وتعديل السلوك
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setShowGrid(False) # إخفاء الشبكة لمظهر أنظف
        
        # تنسيق الخط
        self.setFont(QFont("Consolas", 9))
        
        # تطبيق الثيم المبدئي
        self._apply_style()

    def _apply_style(self):
        bg = theme_engine.get_color("surface")
        text = theme_engine.get_color("text_primary")
        
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {bg};
                color: {text};
                border: none;
            }}
            QHeaderView::section {{
                background-color: {theme_engine.get_color("background")};
                color: {theme_engine.get_color("text_secondary")};
                border: none;
                padding: 4px;
            }}
        """)

    def update_rows(self, data, max_vol):
        """
        تحديث الصفوف بذكاء (Diff Update).
        data: list of [price, amount, total]
        max_vol: أكبر حجم في الكتاب بالكامل (لحساب طول الشريط)
        """
        self.setUpdatesEnabled(False) # تجميد الرسم لزيادة السرعة
        
        needed_rows = len(data)
        current_rows = self.rowCount()
        
        # 1. ضبط عدد الصفوف
        if needed_rows != current_rows:
            self.setRowCount(needed_rows)
            
        # 2. تعبئة البيانات
        base_color = theme_engine.get_color("chart_up") if self.is_bids else theme_engine.get_color("chart_down")
        bg_surface = theme_engine.get_color("surface")
        
        for r, (price, amount, total) in enumerate(data):
            # Price
            item_price = self.item(r, 0)
            if not item_price:
                item_price = QTableWidgetItem()
                item_price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_price.setForeground(QBrush(QColor(base_color)))
                self.setItem(r, 0, item_price)
            
            # تحديث النص فقط إذا تغير
            price_str = f"{price:.2f}"
            if item_price.text() != price_str:
                item_price.setText(price_str)

            # Amount
            item_amt = self.item(r, 1)
            if not item_amt:
                item_amt = QTableWidgetItem()
                item_amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.setItem(r, 1, item_amt)
            
            amt_str = f"{amount:.4f}"
            if item_amt.text() != amt_str:
                item_amt.setText(amt_str)

            # Total (Cumulative)
            item_total = self.item(r, 2)
            if not item_total:
                item_total = QTableWidgetItem()
                item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.setItem(r, 2, item_total)
            
            total_str = f"{total:.4f}"
            if item_total.text() != total_str:
                item_total.setText(total_str)

            # --- Visual Depth Bar (Forensic Feature) ---
            # رسم تدرج لوني في الخلفية يعبر عن حجم الطلب مقارنة بالبقية
            if max_vol > 0:
                ratio = min(1.0, total / max_vol)
                # إنشاء لون شفاف
                c = QColor(base_color)
                c.setAlpha(40) # شفافية 15%
                
                # إنشاء تدرج (Gradient) يبدأ من اليمين
                grad = QLinearGradient(0, 0, self.width(), 0)
                grad.setColorAt(1.0 - ratio, QColor(bg_surface)) # فراغ
                grad.setColorAt(1.0 - ratio + 0.01, c)           # بداية الشريط
                grad.setColorAt(1.0, c)                          # نهاية الشريط
                
                # تطبيق الخلفية على الصف بالكامل
                brush = QBrush(grad)
                item_price.setBackground(brush)
                item_amt.setBackground(brush)
                item_total.setBackground(brush)

        self.setUpdatesEnabled(True) # استئناف الرسم


class OrderBook(QWidget):
    """
    دفتر الأوامر المجمع (The Consolidated Order Book).
    يحتوي على جدولين (Ask في الأعلى، Bid في الأسفل) ومنطقة للسعر الحالي.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        # 1. Asks Table (Sellers - Red)
        self.table_asks = OrderBookTable(is_bids=False)
        # نعكس الترتيب للعرض (أقل سعر بيع في الأسفل)
        self.layout.addWidget(self.table_asks)
        
        # 2. Current Price Indicator (The Spread)
        self.lbl_spread = QLabel("SPREAD: 0.00")
        self.lbl_spread.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_spread.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_spread.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; background-color: {theme_engine.get_color('background')}; padding: 5px;")
        self.layout.addWidget(self.lbl_spread)
        
        # 3. Bids Table (Buyers - Green)
        self.table_bids = OrderBookTable(is_bids=True)
        self.layout.addWidget(self.table_bids)

        # --- Wiring ---
        event_hub.order_book_updated.connect(self._on_book_update)
        event_hub.market_tick_received.connect(self._on_tick) # لتحديث السعر الأوسط إن لزم
        
        theme_engine.theme_changed.connect(self._apply_theme)
        
        logger_sink.log_system_event("OrderBook", "INFO", "📖 Liquidity Radar Active.")

    def _apply_theme(self):
        self.table_asks._apply_style()
        self.table_bids._apply_style()
        self.lbl_spread.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; background-color: {theme_engine.get_color('background')}; padding: 5px;")

    @pyqtSlot(str, float, float)
    def _on_tick(self, ticker, price, vol):
        # يمكننا هنا تحديث السعر في المنتصف إذا لم تتوفر بيانات الـ Book كاملة
        # لكن الـ Spread الحقيقي يحسب من الـ Book
        pass

    @pyqtSlot(str, list, list)
    def _on_book_update(self, ticker: str, bids: list, asks: list):
        """
        Input format: list of [price, amount]
        """
        # 1. معالجة البيانات (حساب التراكمي Total)
        # Asks: نرتب تصاعدياً (أرخص بائع أولاً)
        asks_sorted = sorted(asks, key=lambda x: x[0])[:15] # نأخذ أقرب 15 مستوى
        # Bids: نرتب تنازلياً (أغلى مشتري أولاً)
        bids_sorted = sorted(bids, key=lambda x: x[0], reverse=True)[:15]
        
        # عكس الـ Asks للعرض (بحيث يكون السعر الأرخص في الأسفل، بجانب الـ Spread)
        asks_display = asks_sorted[::-1]
        
        # حساب التراكمي للعرض البصري (Depth Chart Logic)
        asks_data = []
        acc = 0
        for p, a in asks_sorted: # نحسب التراكمي من الأرخص للأغلى
            acc += a
            asks_data.append([p, a, acc])
        asks_data = asks_data[::-1] # نعكس مرة أخرى للعرض
            
        bids_data = []
        acc = 0
        for p, a in bids_sorted:
            acc += a
            bids_data.append([p, a, acc])

        # حساب أكبر حجم لضبط مقياس الرسم
        max_vol_asks = asks_data[0][2] if asks_data else 1
        max_vol_bids = bids_data[-1][2] if bids_data else 1 # آخر عنصر هو الأكبر تراكمياً
        global_max = max(max_vol_asks, max_vol_bids)

        # 2. تحديث الجداول
        self.table_asks.update_rows(asks_data, global_max)
        self.table_bids.update_rows(bids_data, global_max)

        # 3. تحديث الـ Spread
        if asks_sorted and bids_sorted:
            best_ask = asks_sorted[0][0]
            best_bid = bids_sorted[0][0]
            spread = best_ask - best_bid
            pct = (spread / best_ask) * 100
            self.lbl_spread.setText(f"SPREAD: {spread:.2f} ({pct:.3f}%)")