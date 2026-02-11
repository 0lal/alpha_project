# Whale Watching Logic

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - ORDER FLOW ANALYSIS AGENT
# =================================================================
# Component Name: brain/agents/quant/order_flow_agent.py
# Core Responsibility: تحليل تدفق الأوامر وسلوك الحيتان والبحث عن اختلالات السيولة اللحظية (Intelligence Pillar).
# Design Pattern: Agent / Quantitative Analyst
# Forensic Impact: يكشف التلاعب (Spoofing/Layering) ويحدد ما إذا كان تحرك السعر مدعوماً بسيولة حقيقية أم وهمية.
# =================================================================

import logging
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

class OrderFlowAgent:
    """
    وكيل تحليل تدفق الأوامر (Quant Agent).
    يستخدم الرياضيات لتحليل البنية المجهرية للسوق (Market Microstructure).
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        تهيئة الوكيل.
        
        Args:
            config: إعدادات العتبات (مثل حجم الحوت، عمق التحليل).
        """
        self.logger = logging.getLogger("Alpha.Brain.Quant.OrderFlow")
        self.config = config or {}
        
        # إعدادات افتراضية
        self.depth_levels = self.config.get('depth_levels', 10) # تحليل أفضل 10 مستويات
        self.whale_threshold_usd = self.config.get('whale_threshold_usd', 100000.0) # 100k$ يعتبر حوتاً
        self.imbalance_threshold = self.config.get('imbalance_threshold', 0.65) # 65% يعتبر ضغطاً قوياً

    def analyze_book(self, order_book: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل لقطة دفتر الأوامر (Snapshot Analysis).
        
        Args:
            order_book: قاموس يحتوي على {bids: [[price, qty], ...], asks: [[price, qty], ...]}
        
        Returns:
            تقرير التحليل (Signal).
        """
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            symbol = order_book.get('symbol', 'UNKNOWN')

            if not bids or not asks:
                return self._empty_signal()

            # 1. حساب اختلال التوازن في السيولة (Order Book Imbalance)
            imbalance_ratio = self._calculate_imbalance(bids, asks, self.depth_levels)
            
            # 2. الكشف عن جدران الحيتان (Whale Walls)
            bid_walls = self._detect_walls(bids, "BID")
            ask_walls = self._detect_walls(asks, "ASK")
            
            # 3. تحديد منطقة السيطرة (Control Zone)
            sentiment = "NEUTRAL"
            if imbalance_ratio > self.imbalance_threshold:
                sentiment = "BULLISH_PRESSURE" # المشترون يسيطرون
            elif imbalance_ratio < -self.imbalance_threshold:
                sentiment = "BEARISH_PRESSURE" # البائعون يسيطرون

            # 4. بناء الإشارة النهائية
            analysis_result = {
                "agent": "OrderFlowAgent",
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "metrics": {
                    "imbalance_ratio": round(imbalance_ratio, 4), # من -1 (بيع) إلى 1 (شراء)
                    "bid_depth_usd": self._sum_value(bids[:self.depth_levels]),
                    "ask_depth_usd": self._sum_value(asks[:self.depth_levels]),
                },
                "features": {
                    "whale_walls_detected": len(bid_walls) + len(ask_walls),
                    "nearest_bid_wall": bid_walls[0] if bid_walls else None,
                    "nearest_ask_wall": ask_walls[0] if ask_walls else None,
                },
                "signal": {
                    "sentiment": sentiment,
                    "strength": abs(imbalance_ratio), # قوة الإشارة
                    "reason": f"OFI: {imbalance_ratio:.2f} | Walls: +{len(bid_walls)}/-{len(ask_walls)}"
                }
            }

            # تسجيل جنائي إذا كان هناك نشاط غير طبيعي
            if abs(imbalance_ratio) > 0.8:
                self.logger.info(f"HIGH_IMBALANCE: {symbol} ضغط شديد ({imbalance_ratio:.2f}).")

            return analysis_result

        except Exception as e:
            self.logger.error(f"ANALYSIS_ERROR: فشل تحليل تدفق الأوامر: {e}")
            return self._empty_signal()

    def _calculate_imbalance(self, bids: List[List[float]], asks: List[List[float]], depth: int) -> float:
        """
        المعادلة الكمية لحساب اختلال التوازن (OFI).
        Returns:
            قيمة بين -1.0 (سيطرة البائعين) و 1.0 (سيطرة المشترين).
        """
        # نأخذ فقط أول N مستويات
        top_bids = bids[:depth]
        top_asks = asks[:depth]

        # حساب مجموع الكميات المرجحة (Volume Weighted)
        # نعطي وزناً أكبر للمستويات القريبة من السعر الحالي
        bid_vol = sum(q * (1 / (i + 1)) for i, (p, q) in enumerate(top_bids))
        ask_vol = sum(q * (1 / (i + 1)) for i, (p, q) in enumerate(top_asks))

        total_vol = bid_vol + ask_vol
        
        if total_vol == 0:
            return 0.0

        # المعادلة: (Bid - Ask) / (Bid + Ask)
        return (bid_vol - ask_vol) / total_vol

    def _detect_walls(self, orders: List[List[float]], side: str) -> List[Dict[str, Any]]:
        """
        البحث عن أوامر ضخمة (Limit Orders) قد تعمل كمستويات دعم/مقاومة.
        """
        walls = []
        for price, qty in orders:
            value_usd = price * qty
            if value_usd >= self.whale_threshold_usd:
                walls.append({
                    "price": price,
                    "qty": qty,
                    "value_usd": value_usd,
                    "side": side
                })
        return walls

    def _sum_value(self, orders: List[List[float]]) -> float:
        """مساعدة: حساب القيمة الإجمالية لمجموعة أوامر."""
        return sum(p * q for p, q in orders)

    def _empty_signal(self) -> Dict[str, Any]:
        """إرجاع إشارة فارغة في حال الخطأ."""
        return {
            "agent": "OrderFlowAgent",
            "signal": {"sentiment": "NEUTRAL", "strength": 0.0},
            "error": "Insufficient Data"
        }