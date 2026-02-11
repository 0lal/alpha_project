import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, 
    QLabel, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink
from ui.core.event_hub import event_hub

# --- استيراد المكونات الحيوية ---
from ui.components.molecules.stat_card import StatCard
from ui.components.atoms.value_ticker import ValueTicker
from ui.components.organisms.order_book import OrderBook
# ملاحظة: نفترض وجود FinancialChart، إذا لم يكن موجوداً سنضع مكانه Placeholder
try:
    from ui.components.organisms.financial_chart import FinancialChart
except ImportError:
    FinancialChart = None # Fallback

logger = logging.getLogger("Alpha.Cockpit")

class CockpitView(QWidget):
    """
    قمرة القيادة المركزية (The Command Center).
    
    المكونات:
    1. Top Bar: بطاقات الحالة (Balance, PnL, Daily Profit).
    2. Main Area (Left): الرسم البياني المالي (Financial Chart).
    3. Side Panel (Right): دفتر الأوامر (Order Book) + آخر الصفقات (Recent Trades).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # التخطيط الرئيسي عمودي: شريط علوي + منطقة عمل
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # 1. شريط العدادات العلوي (The HUD)
        self._build_top_hud()

        # 2. منطقة العمل المقسمة (Splitter)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)
        
        # A. المنطقة اليسرى (الشارت)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        
        if FinancialChart:
            self.chart = FinancialChart()
            self.chart_layout.addWidget(self.chart)
        else:
            # Fallback if chart component is missing
            lbl = QLabel("FINANCIAL CHART MODULE NOT LOADED")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("border: 2px dashed #555; color: #888;")
            self.chart_layout.addWidget(lbl)
            
        self.main_splitter.addWidget(self.chart_container)

        # B. المنطقة اليمنى (العمق والسوق)
        self.side_panel = QWidget()
        self.side_layout = QVBoxLayout(self.side_panel)
        self.side_layout.setContentsMargins(0, 0, 0, 0)
        self.side_layout.setSpacing(5)
        
        # عنوان صغير
        lbl_book = QLabel("ORDER BOOK (DEPTH)")
        lbl_book.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_book.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; letter-spacing: 1px;")
        self.side_layout.addWidget(lbl_book)
        
        # دفتر الأوامر
        self.order_book = OrderBook()
        self.side_layout.addWidget(self.order_book)
        
        # فاصل
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {theme_engine.get_color('grid_line')};")
        self.side_layout.addWidget(line)
        
        # آخر الصفقات (Market Trades) - Placeholder for now
        lbl_trades = QLabel("RECENT TRADES")
        lbl_trades.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_trades.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; letter-spacing: 1px;")
        self.side_layout.addWidget(lbl_trades)
        
        self.trades_list = QLabel("Waiting for market data...")
        self.trades_list.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.trades_list.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; font-family: Consolas;")
        self.side_layout.addWidget(self.trades_list)
        self.side_layout.addStretch() # دفع للأعلى

        self.main_splitter.addWidget(self.side_panel)
        
        # ضبط نسب التقسيم (70% شارت - 30% بيانات)
        self.main_splitter.setStretchFactor(0, 7)
        self.main_splitter.setStretchFactor(1, 3)

        self.layout.addWidget(self.main_splitter)

        # تطبيق الثيم
        theme_engine.theme_changed.connect(self._apply_theme)
        self._apply_theme()
        
        # ربط البيانات (محاكاة)
        self._setup_mock_data_connection()

    def _build_top_hud(self):
        """بناء شريط العدادات العلوية"""
        hud_container = QFrame()
        hud_container.setFixedHeight(100)
        hud_container.setStyleSheet(f"background-color: {theme_engine.get_color('surface')}; border-radius: 8px;")
        
        layout = QHBoxLayout(hud_container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(20)
        
        # 1. السعر الحالي (الأضخم)
        price_layout = QVBoxLayout()
        lbl_symbol = QLabel("BTC/USDT")
        lbl_symbol.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_symbol.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')};")
        
        self.ticker_price = ValueTicker("0.00")
        self.ticker_price.set_font_size(24) # خط ضخم
        
        price_layout.addWidget(lbl_symbol)
        price_layout.addWidget(self.ticker_price)
        layout.addLayout(price_layout)
        
        # فاصل عمودي
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.VLine)
        line1.setStyleSheet(f"color: {theme_engine.get_color('grid_line')};")
        layout.addWidget(line1)

        # 2. بطاقات الإحصائيات (Stat Cards)
        # الرصيد
        self.card_balance = StatCard("TOTAL BALANCE", "$10,000.00")
        layout.addWidget(self.card_balance)
        
        # الربح اليومي
        self.card_pnl = StatCard("DAILY PNL", "+$0.00")
        layout.addWidget(self.card_pnl)
        
        # الصفقات المفتوحة
        self.card_open_pos = StatCard("OPEN POSITIONS", "0")
        layout.addWidget(self.card_open_pos)
        
        # دفع البقية لليسار
        layout.addStretch()

        self.layout.addWidget(hud_container)

    def _apply_theme(self):
        """تحديث الألوان عند تغيير الثيم"""
        bg = theme_engine.get_color("background")
        border = theme_engine.get_color("grid_line")
        
        self.main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {border};
            }}
        """)

    # =========================================================================
    # Data Connectivity (Wiring)
    # =========================================================================
    def _setup_mock_data_connection(self):
        """
        في النظام الحقيقي، هنا نربط بـ EventHub.
        لغرض العرض، سنقوم فقط بتحديثات وهمية بسيطة لإثبات أن الواجهة تعمل.
        """
        # ربط بتحديثات السوق الحقيقية إذا كانت متوفرة
        event_hub.market_tick_received.connect(self._on_market_tick)
        event_hub.portfolio_update.connect(self._on_portfolio_update)

    @pyqtSlot(str, float, float)
    def _on_market_tick(self, symbol, price, volume):
        """استقبال تحديث السعر"""
        if "BTC" in symbol:
            self.ticker_price.set_value(price, fmt="{:,.2f}")

    @pyqtSlot(dict)
    def _on_portfolio_update(self, data):
        """استقبال تحديث المحفظة"""
        balance = data.get("total_balance", 0.0)
        pnl = data.get("daily_pnl", 0.0)
        
        self.card_balance.update_value(balance, suffix="")
        self.card_pnl.update_value(pnl, suffix="")