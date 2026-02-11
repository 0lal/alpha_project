# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - CLI COMMAND PARSER
# =================================================================
# Component Name: shield/nexus/interface/api/command_parser.py
# Core Responsibility: ترجمة الأوامر النصية إلى هياكل بيانات قابلة للتنفيذ.
# Design Pattern: Interpreter / Command Pattern
# Security: Input Sanitization (تنظيف المدخلات لمنع الـ Injection).
# =================================================================

import re
import logging
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, ValidationError

# إعداد السجلات
logger = logging.getLogger("Alpha.Nexus.CLI")

# ----------------------------------------------------------------
# نماذج الأوامر (Command Models)
# ----------------------------------------------------------------

class ParsedCommand(BaseModel):
    """الهيكل الموحد لأي أمر بعد ترجمته"""
    action: str             # الفعل الرئيسي (BUY, SELL, STOP)
    target: Optional[str]   # الهدف (BTCUSDT, SYSTEM)
    params: Dict[str, Any]  # المعاملات الإضافية (amount, price, reason)
    raw_text: str           # النص الأصلي للمرجعية

# ----------------------------------------------------------------
# المحلل الرئيسي (The Parser Engine)
# ----------------------------------------------------------------

class CommandParser:
    """
    محرك تحليل الأوامر النصية.
    يدعم صيغاً متعددة مثل:
    - /buy BTCUSDT 0.5
    - /sell ETHUSDT 10.0 limit=2500
    - /panic "Market Crash"
    """

    def __init__(self):
        # تعريف الأنماط (Regex Patterns) للأوامر المعروفة
        self.patterns = {
            # الصيغة: /action symbol amount [key=value]
            "TRADE": re.compile(r"^/(buy|sell)\s+([a-zA-Z0-9]+)\s+([0-9.]+)(.*)$", re.IGNORECASE),
            
            # الصيغة: /stop reason
            "SYSTEM": re.compile(r"^/(stop|restart|status)\s*(.*)$", re.IGNORECASE),
            
            # الصيغة: /log 10
            "QUERY": re.compile(r"^/(log|audit|balance)\s*(.*)$", re.IGNORECASE)
        }

    def parse(self, text: str) -> ParsedCommand:
        """
        تحويل النص إلى كائن ParsedCommand.
        """
        text = text.strip()
        if not text.startswith("/"):
            raise ValueError("يجب أن يبدأ الأمر بـ '/' (مثال: /status)")

        # 1. محاولة مطابقة أوامر التداول (Trade Commands)
        match_trade = self.patterns["TRADE"].match(text)
        if match_trade:
            return self._parse_trade(match_trade, text)

        # 2. محاولة مطابقة أوامر النظام (System Commands)
        match_sys = self.patterns["SYSTEM"].match(text)
        if match_sys:
            return self._parse_system(match_sys, text)

        # 3. محاولة مطابقة أوامر الاستعلام (Query Commands)
        match_query = self.patterns["QUERY"].match(text)
        if match_query:
            return self._parse_query(match_query, text)

        # فشل التعرف على الأمر
        logger.warning(f"CLI_UNKNOWN: أمر غير معروف: {text}")
        raise ValueError(f"أمر غير معروف أو صيغة خاطئة: {text.split()[0]}")

    def _parse_trade(self, match: re.Match, raw: str) -> ParsedCommand:
        """معالجة أوامر البيع والشراء"""
        action = match.group(1).upper()
        symbol = match.group(2).upper()
        amount = float(match.group(3))
        extras_str = match.group(4).strip()

        params = {"amount": amount, "type": "MARKET"} # Default to Market Order

        # استخراج المعاملات الاختيارية (مثل price=50000)
        if extras_str:
            params.update(self._extract_kwargs(extras_str))

        return ParsedCommand(
            action=action,
            target=symbol,
            params=params,
            raw_text=raw
        )

    def _parse_system(self, match: re.Match, raw: str) -> ParsedCommand:
        """معالجة أوامر النظام (Stop/Status)"""
        action = match.group(1).upper()
        arg = match.group(2).strip().strip('"') # إزالة علامات التنصيص

        params = {}
        if action == "STOP":
            params["reason"] = arg or "Manual Intervention"
            target = "SYSTEM"
        elif action == "STATUS":
            target = arg or "ALL"
        else:
            target = "SYSTEM"

        return ParsedCommand(
            action=action,
            target=target,
            params=params,
            raw_text=raw
        )

    def _parse_query(self, match: re.Match, raw: str) -> ParsedCommand:
        """معالجة أوامر الاستعلام"""
        action = match.group(1).upper()
        arg = match.group(2).strip()

        params = {}
        if action == "LOG":
            # محاولة تحويل الرقم (مثال: /log 50)
            try:
                params["limit"] = int(arg) if arg else 10
            except ValueError:
                params["limit"] = 10
        
        return ParsedCommand(
            action=action,
            target="DB",
            params=params,
            raw_text=raw
        )

    def _extract_kwargs(self, text: str) -> Dict[str, Any]:
        """
        استخراج المعاملات بصيغة key=value
        مثال: "price=100 type=limit" -> {'price': 100.0, 'type': 'limit'}
        """
        kwargs = {}
        # تقسيم النص بناءً على المسافات
        parts = text.split()
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                # محاولة تحويل القيمة لرقم إن أمكن
                try:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass # إبقاء القيمة كنص
                kwargs[key.lower()] = value
        return kwargs

# =================================================================
# Global Instance
# =================================================================
cli_parser = CommandParser()