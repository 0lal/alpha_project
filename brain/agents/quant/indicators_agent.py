# Technical Analysis Core

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - ADVANCED INDICATORS ENGINE
# =================================================================
# Component Name: brain/agents/quant/indicators_agent.py
# Core Responsibility: تشغيل محرك المؤشرات الفنية المتقدمة والبحث عن الارتباطات والأنماط (Intelligence Pillar).
# Design Pattern: Agent / Computable Function
# Forensic Impact: يوفر "السياق الفني" للحركة. إذا تحرك السعر عكس المؤشرات (Divergence)، فهذا دليل محتمل على التلاعب.
# =================================================================

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

class IndicatorsAgent:
    """
    وكيل المؤشرات الفنية.
    يقوم بحساب الرياضيات المعقدة خلف الرسوم البيانية لاستخراج إشارات الدخول والخروج.
    يعتمد على Pandas Vectorization للأداء العالي بدلاً من الحلقات التكرارية البطيئة.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Quant.Indicators")
        
        # إعدادات المؤشرات القياسية
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2.0

    def analyze_market_state(self, candles_df: pd.DataFrame) -> Dict[str, Any]:
        """
        تحليل حالة السوق بناءً على الشموع التاريخية.
        
        Args:
            candles_df: DataFrame يحتوي على [open, high, low, close, volume]
            
        Returns:
            تقرير فني شامل (Technical Report).
        """
        if candles_df.empty or len(candles_df) < 50:
            return {"status": "INSUFFICIENT_DATA"}

        try:
            # 1. حساب المؤشرات الأساسية
            df = candles_df.copy()
            self._add_rsi(df)
            self._add_macd(df)
            self._add_bollinger_bands(df)
            self._add_atr(df)
            self._add_vwap(df)

            # 2. استخراج القيم الحالية (آخر شمعة)
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # 3. الكشف عن الأنماط المتقدمة (Signals Detection)
            signals = []
            
            # A. فحص تشبع الشراء/البيع (RSI Extremes)
            rsi_state = "NEUTRAL"
            if latest['rsi'] > 70: rsi_state = "OVERBOUGHT"
            elif latest['rsi'] < 30: rsi_state = "OVERSOLD"

            # B. تقاطع الماكد (MACD Crossover)
            # إذا كان الخط السريع تحت البطيع في الشمعة السابقة، وأصبح فوقه الآن -> تقاطع إيجابي
            if prev['macd'] < prev['macd_signal'] and latest['macd'] > latest['macd_signal']:
                signals.append("MACD_GOLDEN_CROSS")
            elif prev['macd'] > prev['macd_signal'] and latest['macd'] < latest['macd_signal']:
                signals.append("MACD_DEATH_CROSS")

            # C. الكشف عن التباعد (Regular Divergence)
            # مثال: السعر يحقق قمة جديدة، لكن RSI يحقق قمة أدنى (ضعف الاتجاه الصاعد)
            divergence = self._detect_rsi_divergence(df)
            if divergence:
                signals.append(divergence)

            # D. اختراق البولنجر (Bollinger Breakout)
            bb_status = "INSIDE"
            if latest['close'] > latest['bb_upper']: bb_status = "BREAKOUT_UPPER"
            elif latest['close'] < latest['bb_lower']: bb_status = "BREAKOUT_LOWER"

            # 4. تجميع التقرير
            return {
                "agent": "IndicatorsAgent",
                "timestamp": str(latest.name) if isinstance(latest.name, (str, pd.Timestamp)) else None,
                "indicators": {
                    "rsi": round(latest['rsi'], 2),
                    "macd_hist": round(latest['macd_hist'], 4),
                    "bb_width": round((latest['bb_upper'] - latest['bb_lower']) / latest['bb_lower'], 4),
                    "atr": round(latest['atr'], 2),
                    "vwap": round(latest['vwap'], 2)
                },
                "state": {
                    "rsi_status": rsi_state,
                    "bb_status": bb_status,
                    "trend_strength": self._calculate_adx_proxy(df) # مؤشر تقريبي لقوة الاتجاه
                },
                "detected_patterns": signals
            }

        except Exception as e:
            self.logger.error(f"INDICATOR_FAIL: خطأ أثناء الحساب: {e}")
            return {"status": "ERROR", "msg": str(e)}

    # ------------------------------------------------------------------
    # محرك الحسابات (Calculation Engine - Vectorized)
    # ------------------------------------------------------------------

    def _add_rsi(self, df: pd.DataFrame):
        """Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        # التعامل مع القسمة على صفر
        df['rsi'] = df['rsi'].fillna(50)

    def _add_macd(self, df: pd.DataFrame):
        """Moving Average Convergence Divergence"""
        exp1 = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

    def _add_bollinger_bands(self, df: pd.DataFrame):
        """Bollinger Bands"""
        sma = df['close'].rolling(window=self.bb_period).mean()
        std = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = sma + (std * self.bb_std)
        df['bb_lower'] = sma - (std * self.bb_std)

    def _add_atr(self, df: pd.DataFrame):
        """Average True Range (Volatilty)"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(window=14).mean()

    def _add_vwap(self, df: pd.DataFrame):
        """Volume Weighted Average Price"""
        # حساب تراكمي بسيط (Cumulative)
        v = df['volume'].values
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (tp * v).cumsum() / v.cumsum()

    def _detect_rsi_divergence(self, df: pd.DataFrame, window=10) -> Optional[str]:
        """
        كشف التباعد بين السعر ومؤشر RSI.
        منطق معقد يتطلب مقارنة القمم (Peaks) والقيعان (Troughs).
        """
        # تبسيط للكشف: مقارنة السعر والمؤشر بين آخر قمة وحالية
        # (يتطلب خوارزمية Peak Detection كاملة، هنا نضع نسخة مبسطة فعالة)
        
        # Bearish Divergence: Price Up, RSI Down
        price_trend = df['close'].iloc[-window:].is_monotonic_increasing
        rsi_trend = df['rsi'].iloc[-window:].is_monotonic_decreasing
        
        if price_trend and rsi_trend:
            return "BEARISH_DIVERGENCE"

        # Bullish Divergence: Price Down, RSI Up
        price_down = df['close'].iloc[-window:].is_monotonic_decreasing
        rsi_up = df['rsi'].iloc[-window:].is_monotonic_increasing
        
        if price_down and rsi_up:
            return "BULLISH_DIVERGENCE"
            
        return None

    def _calculate_adx_proxy(self, df: pd.DataFrame) -> str:
        """تقدير قوة الاتجاه بناءً على عرض البولنجر أو ميل المتوسطات."""
        # إذا كان الماكد يبتعد عن الإشارة بقوة، فالاتجاه قوي
        hist_strength = abs(df['macd_hist'].iloc[-1])
        if hist_strength > df['close'].iloc[-1] * 0.0005: # نسبة تقريبية
            return "STRONG"
        return "WEAK"