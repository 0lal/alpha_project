# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - TUI CHARTS WIDGET
# =================================================================
# Component Name: shield/nexus/interface/tui/widgets/charts.py
# Core Responsibility: رسم المخططات البيانية (Line/Candle) باستخدام ASCII.
# Design Pattern: Rendering Engine
# =================================================================

from typing import List
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.layout import Layout

class PriceChartWidget:
    """
    أداة رسم مخطط السعر (Price Chart).
    تستخدم محارف "البلوكات" (Block Characters) لتمثيل ارتفاع وانخفاض السعر
    بدقة أعلى من النصوص العادية.
    """

    def __init__(self, height: int = 10):
        self.height = height
        # محارف التظليل لتمثيل مستويات مختلفة من السعر داخل السطر الواحد
        self.blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    def render(self, symbol: str, prices: List[float], width: int = 60) -> Panel:
        """
        توليد لوحة الرسم البياني.
        Args:
            symbol: رمز العملة (BTCUSDT).
            prices: قائمة الأسعار التاريخية.
            width: عرض الرسم البياني (عدد الأعمدة).
        """
        if not prices:
            return Panel(Align.center("[yellow]NO MARKET DATA[/]"), title=symbol)

        # 1. تقليص البيانات لتناسب العرض (Downsampling)
        # إذا كانت البيانات أكثر من عرض الشاشة، نأخذ عينات منها
        view_data = prices[-width:]
        
        # 2. حساب الحدود القصوى والدنيا (Scaling)
        min_p = min(view_data)
        max_p = max(view_data)
        price_range = max_p - min_p if max_p != min_p else 1.0
        
        # 3. بناء الرسم (The Plotting Loop)
        rows = [""] * self.height
        
        for price in view_data:
            # تطبيع السعر (Normalization) ليكون بين 0 و ارتفاع الشارت
            normalized = (price - min_p) / price_range * (self.height - 1)
            
            row_idx = int(normalized)   # في أي سطر يقع السعر؟
            remainder = normalized - row_idx # لتحديد دقة البلوك
            
            block_idx = int(remainder * (len(self.blocks) - 1))
            char = self.blocks[block_idx]

            # تلوين الشمعة (أخضر للصعود، أحمر للهبوط مقارنة بالسابق)
            # للتبسيط هنا سنلون بناءً على الموقع النسبي، 
            # (في النسخة الكاملة نقارن بالسعر السابق)
            color = "green" if row_idx > (self.height / 2) else "red"
            
            # ملء المصفوفة
            for i in range(self.height):
                # المحور Y مقلوب في التيرمينال (0 هو الأعلى)، لذا نعكسه
                actual_row = (self.height - 1) - i
                
                if i == row_idx:
                    rows[actual_row] += f"[{color}]{char}[/]"
                elif i < row_idx:
                    # تظليل المنطقة تحت الخط (Area Chart Effect)
                    rows[actual_row] += f"[{color} dim]│[/]" 
                else:
                    rows[actual_row] += " "

        # 4. تجميع الأسطر في نص واحد
        chart_text = Text.from_markup("\n".join(rows))
        
        # إضافة معلومات السعر الحالي
        last_price = view_data[-1]
        footer_info = f"[bold white]{symbol}[/] | Last: [bold yellow]{last_price:,.2f}[/]"

        return Panel(
            chart_text,
            title="[bold blue]MARKET DEPTH SCAN[/]",
            subtitle=footer_info,
            border_style="blue",
            box=None # بدون حدود إضافية لدمجه في التصميم
        )

class OrderBookWidget:
    """
    أداة عرض سجل الأوامر (Order Book).
    يعرض العروض (Asks) والطلبات (Bids) بشكل متقابل.
    """
    
    def render(self, asks: List[float], bids: List[float]) -> Text:
        # سنقوم بتنفيذ هذا المنطق لتمثيل عمق السوق نصياً
        # (Placeholder implementation)
        content = Text()
        content.append("ASKS (Sell)\n", style="red bold")
        for p in asks[:5]:
            content.append(f"{p:,.2f}\n", style="red")
            
        content.append("-" * 20 + "\n", style="dim")
        
        content.append("BIDS (Buy)\n", style="green bold")
        for p in bids[:5]:
            content.append(f"{p:,.2f}\n", style="green")
            
        return content