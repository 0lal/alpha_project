# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - HYPOTHESIS GENERATION & SCIENTIFIC ENGINE
# =================================================================
# Component Name: brain/reasoning/hypothesis_gen.py
# Core Responsibility: توليد فرضيات سوقية واختبارها افتراضياً (The Scientific Method) (Intelligence Pillar).
# Design Pattern: Generator / Heuristic Search
# Forensic Impact: يوثق "مصدر الفكرة". هل كانت صفقة عشوائية أم نتيجة استنتاج نمطي محدد؟
# =================================================================

import logging
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class MarketHypothesis:
    id: str
    type: str          # e.g., "MEAN_REVERSION", "BREAKOUT", "CORRELATION"
    symbol: str
    premise: str       # "RSI is 85 + Price hit Bollinger Upper Band"
    prediction: str    # "Price will drop to EMA-20"
    confidence: float  # 0.0 to 1.0
    time_horizon: str  # "SHORT_TERM", "MEDIUM_TERM"
    suggested_action: str # "SHORT_SELL"

class HypothesisGenerator:
    """
    مولد الفرضيات.
    يقوم بمسح بيانات السوق لاستخراج أنماط كامنة وتحويلها إلى نظريات قابلة للاختبار.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Reasoning.Hypothesis")
        
        # مكتبة الأنماط (Pattern Library)
        # هذه هي "القوالب" التي يبحث عنها العالم
        self.patterns = [
            "RUBBER_BAND",   # التمدد السعري المفرط (Mean Reversion)
            "PRESSURE_COOKER", # انخفاض التقلب الشديد (Volatility Squeeze)
            "DIVERGENCE_HUNT"  # الاختلاف بين السعر والمؤشر
        ]

    def scan_opportunities(self, 
                           market_state: Dict[str, Any], 
                           tech_indicators: Dict[str, Any]) -> List[MarketHypothesis]:
        """
        المسح الشامل للفرص.
        
        Args:
            market_state: الحالة العامة (Volatility, Volume, etc.)
            tech_indicators: المؤشرات الفنية (RSI, BB, MACD...)
            
        Returns:
            قائمة بالفرضيات التي اجتازت الاختبار الأولي.
        """
        hypotheses = []
        symbol = market_state.get("symbol", "UNKNOWN")

        # 1. اختبار فرضية "الشريط المطاطي" (Mean Reversion)
        # السعر ابتعد كثيراً عن المتوسط، لا بد أن يعود.
        h1 = self._formulate_rubber_band(symbol, tech_indicators)
        if h1: hypotheses.append(h1)

        # 2. اختبار فرضية "طنجرة الضغط" (Volatility Breakout)
        # السعر محصور في نطاق ضيق جداً، انفجار وشيك.
        h2 = self._formulate_pressure_cooker(symbol, tech_indicators)
        if h2: hypotheses.append(h2)

        # 3. اختبار فرضية "الصيد المخالف" (Contrarian Divergence)
        # السعر يصعد والزخم يهبط.
        h3 = self._formulate_divergence(symbol, tech_indicators)
        if h3: hypotheses.append(h3)

        # تسجيل النتائج للأغراض الجنائية
        if hypotheses:
            self.logger.info(f"HYPOTHESIS_GEN: Generated {len(hypotheses)} theories for {symbol}.")
            
        return hypotheses

    def _formulate_rubber_band(self, symbol: str, indicators: Dict[str, Any]) -> Optional[MarketHypothesis]:
        """
        فرضية الارتداد للمتوسط.
        الشرط: RSI متطرف جداً (>80 أو <20) والسعر خارج البولنجر باند.
        """
        rsi = indicators.get("rsi", 50)
        bb_status = indicators.get("state", {}).get("bb_status", "INSIDE")
        
        if rsi > 75 and bb_status == "BREAKOUT_UPPER":
            return MarketHypothesis(
                id=str(uuid.uuid4())[:8],
                type="MEAN_REVERSION",
                symbol=symbol,
                premise=f"Extreme Overbought (RSI {rsi:.1f}) + BB Breakout",
                prediction="Price will revert to Mean (SMA-20)",
                confidence=0.75, # احتمالية عالية عادة
                time_horizon="SHORT_TERM",
                suggested_action="SHORT"
            )
        
        elif rsi < 25 and bb_status == "BREAKOUT_LOWER":
            return MarketHypothesis(
                id=str(uuid.uuid4())[:8],
                type="MEAN_REVERSION",
                symbol=symbol,
                premise=f"Extreme Oversold (RSI {rsi:.1f}) + BB Breakout",
                prediction="Price will revert to Mean (SMA-20)",
                confidence=0.75,
                time_horizon="SHORT_TERM",
                suggested_action="LONG"
            )
            
        return None

    def _formulate_pressure_cooker(self, symbol: str, indicators: Dict[str, Any]) -> Optional[MarketHypothesis]:
        """
        فرضية الانفجار السعري.
        الشرط: Bollinger Band Width منخفض جداً (Squeeze).
        """
        bb_width = indicators.get("indicators", {}).get("bb_width", 1.0)
        
        # هذا الرقم يعتمد على العملة، لنفترض 0.02 (2%) كحد للضغط الشديد
        if bb_width < 0.02:
            return MarketHypothesis(
                id=str(uuid.uuid4())[:8],
                type="BREAKOUT",
                symbol=symbol,
                premise=f"Volatility Squeeze detected (BB Width {bb_width:.4f})",
                prediction="Violent expansion imminent (Direction unknown without OrderFlow)",
                confidence=0.60, # نعرف أن هناك انفجار، لكن لا نعرف الاتجاه بدقة
                time_horizon="MEDIUM_TERM",
                suggested_action="PREPARE_STRADDLE" # استراتيجية للاتجاهين
            )
        return None

    def _formulate_divergence(self, symbol: str, indicators: Dict[str, Any]) -> Optional[MarketHypothesis]:
        """
        فرضية التباعد (تم كشفها مسبقاً بواسطة IndicatorsAgent).
        هنا نقوم بتحويل "الكشف" إلى "فرضية قابلة للتداول".
        """
        patterns = indicators.get("detected_patterns", [])
        
        if "BEARISH_DIVERGENCE" in patterns:
            return MarketHypothesis(
                id=str(uuid.uuid4())[:8],
                type="REVERSAL",
                symbol=symbol,
                premise="Price High vs Momentum Low (Bearish Div)",
                prediction="Trend exhaustion and reversal",
                confidence=0.80,
                time_horizon="MEDIUM_TERM",
                suggested_action="SHORT"
            )
        
        elif "BULLISH_DIVERGENCE" in patterns:
            return MarketHypothesis(
                id=str(uuid.uuid4())[:8],
                type="REVERSAL",
                symbol=symbol,
                premise="Price Low vs Momentum High (Bullish Div)",
                prediction="Trend exhaustion and reversal",
                confidence=0.80,
                time_horizon="MEDIUM_TERM",
                suggested_action="LONG"
            )
            
        return None