# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - TUI RENDERER ENGINE
# =================================================================
# Component Name: shield/nexus/interface/tui/renderer.py
# Core Responsibility: محرك رسم النصوص، الجداول، واللوحات في التيرمينال.
# Design Pattern: View Component (MVC)
# Library: Rich (Terminal Formatting)
# =================================================================

from datetime import datetime
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.style import Style
from rich.align import Align
from rich import box

class TUIRenderer:
    """
    محرك العرض (The Rendering Engine).
    مسؤول عن تحويل البيانات الخام (JSON/Dicts) إلى مكونات بصرية جميلة
    قابلة للعرض في التيرمينال.
    """

    def __init__(self):
        self.console = Console()
        # تعريف الأنماط السيادية (Sovereign Theme)
        self.styles = {
            "header": Style(color="green", bold=True, bgcolor="black"),
            "warning": Style(color="yellow", bold=True),
            "critical": Style(color="red", bold=True, blink=True),
            "success": Style(color="bright_green", bold=True),
            "info": Style(color="cyan"),
            "border": "green"
        }

    def create_layout(self) -> Layout:
        """
        بناء الهيكل العظمي للشاشة (The Skeleton).
        يقسم الشاشة إلى: رأس، جسم (سوق + سجلات)، وتذييل.
        """
        layout = Layout()
        
        # تقسيم عمودي: رأس (3 أسطر) - جسم (متغير) - تذييل (3 أسطر)
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )

        # تقسيم الجسم أفقياً: بيانات السوق (يسار 70%) - سجلات النظام (يمين 30%)
        layout["body"].split_row(
            Layout(name="market_panel", ratio=7),
            Layout(name="logs_panel", ratio=3)
        )

        return layout

    def render_header(self, system_status: str = "ONLINE", cpu_usage: float = 0.0) -> Panel:
        """
        رسم شريط العنوان العلوي.
        """
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # تحديد لون الحالة
        status_color = "bright_green" if system_status == "ONLINE" else "red"
        
        # بناء النص
        header_text = Text()
        header_text.append("ALPHA SOVEREIGN ", style="bold white")
        header_text.append(" | ", style="dim")
        header_text.append(f"STATUS: {system_status}", style=status_color)
        header_text.append(" | ", style="dim")
        header_text.append(f"CPU: {cpu_usage}%", style="cyan")
        header_text.append(" | ", style="dim")
        header_text.append(f"{time_str}", style="yellow")

        return Panel(
            Align.center(header_text),
            box=box.DOUBLE,
            style=self.styles["border"],
            title="[bold green]NEXUS COCKPIT[/]"
        )

    def render_market_table(self, ticks: List[Dict[str, Any]]) -> Panel:
        """
        رسم جدول الأسعار الحية (Live Market Data).
        """
        table = Table(expand=True, box=box.SIMPLE_HEAD, border_style="green")

        # تعريف الأعمدة
        table.add_column("Symbol", style="cyan", no_wrap=True)
        table.add_column("Price", justify="right", style="green")
        table.add_column("Change %", justify="right")
        table.add_column("Volume", justify="right", style="magenta")
        table.add_column("Signal", justify="center")

        # تعبئة البيانات
        for tick in ticks:
            # تلوين النسبة المئوية
            change = tick.get("change", 0.0)
            change_color = "green" if change >= 0 else "red"
            change_str = f"[{change_color}]{change:+.2f}%[/]"

            # إشارة التداول (إن وجدت)
            signal = tick.get("signal", "-")
            signal_style = "bold green" if signal == "BUY" else "bold red" if signal == "SELL" else "dim"

            table.add_row(
                tick.get("symbol", "UNKNOWN"),
                f"{tick.get('price', 0.0):,.2f}",
                change_str,
                f"{tick.get('volume', 0):,.0f}",
                f"[{signal_style}]{signal}[/]"
            )

        return Panel(
            table,
            title="[bold blue]MARKET FEED[/]",
            border_style="blue"
        )

    def render_logs_panel(self, logs: List[str]) -> Panel:
        """
        رسم لوحة السجلات (Logs) الجانبية.
        """
        log_text = Text()
        
        for log in logs[-15:]: # عرض آخر 15 سجل فقط
            # تلوين السطر بناءً على محتواه
            style = "white"
            if "ERROR" in log or "CRITICAL" in log:
                style = "bold red"
            elif "WARNING" in log:
                style = "yellow"
            elif "SUCCESS" in log:
                style = "green"
                
            log_text.append(f"{log}\n", style=style)

        return Panel(
            log_text,
            title="[bold yellow]SYSTEM LOGS[/]",
            border_style="yellow"
        )

    def render_footer(self, last_cmd: str = "") -> Panel:
        """
        رسم شريط الحالة السفلي وموجه الأوامر.
        """
        footer_text = Text()
        footer_text.append("COMMAND > ", style="bold green blink")
        footer_text.append(last_cmd or "Listening...", style="white")

        return Panel(
            footer_text,
            box=box.ROUNDED,
            border_style="white"
        )

# =================================================================
# Global Renderer Instance
# =================================================================
tui_renderer = TUIRenderer()