# Dark Pool Scanner

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - SMART ORDER ROUTER (SOR) & LIQUIDITY SEEKER
# =================================================================
# Component Name: brain/agents/execution/liquidity_seek.py
# Core Responsibility: البحث عن السيولة وتوجيه الأوامر الذكي لتقليل الانزلاق (Performance Pillar).
# Design Pattern: Aggregator / Greedy Optimization
# Forensic Impact: يمنع "بصمة الفيل" (Elephant Footprint). توزيع السيولة يمنع المراقبين من معرفة الحجم الحقيقي للمشتري.
# =================================================================

import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class LiquidityBucket:
    exchange: str
    price: float
    available_qty: float
    fee_rate: float
    trust_score: float # 0.0 to 1.0 (تفضيل البورصات الموثوقة)

class LiquiditySeeker:
    """
    الباحث عن السيولة (SOR).
    يقوم ببناء دفتر أوامر موحد (VOB) وحساب المسار الأمثل للتنفيذ.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Execution.Liquidity")
        
        # إعدادات البورصات (Taker Fees)
        self.exchange_config = {
            "BINANCE":  {"taker_fee": 0.00075, "trust": 0.95},
            "KRAKEN":   {"taker_fee": 0.0026,  "trust": 0.90},
            "COINBASE": {"taker_fee": 0.0060,  "trust": 0.85},
            "DYDX":     {"taker_fee": 0.0005,  "trust": 0.80}, # أرخص لكن سيولة أقل أحياناً
            "OTC_DESK": {"taker_fee": 0.0000,  "trust": 0.99}  # خارج المنصة (بدون انزلاق غالباً)
        }

    def get_routing_plan(self, symbol: str, side: str, total_qty: float, market_snapshots: Dict[str, Any]) -> Dict[str, Any]:
        """
        حساب خطة التوجيه المثلى (Optimal Routing Plan).
        
        Args:
            symbol: الرمز (BTCUSDT).
            side: BUY or SELL.
            total_qty: الكمية المطلوبة.
            market_snapshots: بيانات عمق السوق الحالية لكل بورصة.
            
        Returns:
            خطة توزيع الكميات على البورصات.
        """
        # 1. تجميع السيولة (Aggregation)
        # تحويل دفاتر الأوامر المتفرقة إلى قائمة واحدة من "الدلاء" (Buckets)
        liquidity_pool = self._aggregate_liquidity(side, market_snapshots)
        
        if not liquidity_pool:
            return {"status": "NO_LIQUIDITY", "plan": []}

        # 2. الترتيب الذكي (Smart Sorting)
        # الترتيب حسب "السعر الفعلي" (السعر + الرسوم)
        # إذا كنا نشتري: نريد الأرخص. إذا كنا نبيع: نريد الأغلى.
        is_buy = (side == "BUY")
        liquidity_pool.sort(key=lambda x: self._calculate_effective_price(x, is_buy))
        
        if not is_buy:
            liquidity_pool.reverse() # للبيع نبدأ بالأعلى سعراً

        # 3. خوارزمية ملء الدلاء (Water-Filling Algorithm)
        routing_plan = {} # {EXCHANGE: qty}
        remaining_qty = total_qty
        avg_price_accumulator = 0.0
        
        for bucket in liquidity_pool:
            if remaining_qty <= 0:
                break
                
            # الكمية التي نأخذها من هذا الدلو
            take_qty = min(remaining_qty, bucket.available_qty)
            
            if take_qty > 0:
                current_alloc = routing_plan.get(bucket.exchange, 0.0)
                routing_plan[bucket.exchange] = current_alloc + take_qty
                
                # حساب التكلفة للمتوسط
                cost = take_qty * bucket.price
                avg_price_accumulator += cost
                
                remaining_qty -= take_qty

        # 4. تحليل النتيجة
        filled_qty = total_qty - remaining_qty
        if filled_qty == 0:
             return {"status": "FAIL", "reason": "Zero fill"}
             
        avg_vwap = avg_price_accumulator / filled_qty
        
        # كشف الانزلاق المتوقع (Slippage Audit)
        # نقارن متوسط سعر تنفيذنا بأفضل سعر في السوق
        best_price = liquidity_pool[0].price
        slippage_pct = abs(avg_vwap - best_price) / best_price

        plan_summary = {
            "agent": "LiquiditySeeker",
            "symbol": symbol,
            "requested_qty": total_qty,
            "routed_qty": round(filled_qty, 6),
            "estimated_vwap": round(avg_vwap, 2),
            "expected_slippage_pct": round(slippage_pct * 100, 4),
            "routes": [
                {"exchange": ex, "qty": round(q, 6), "pct": round((q/filled_qty)*100, 1)} 
                for ex, q in routing_plan.items()
            ],
            "status": "PARTIAL_FILL" if remaining_qty > 0 else "COMPLETE"
        }
        
        if slippage_pct > 0.02: # تحذير إذا كان الانزلاق أكثر من 2%
            self.logger.warning(f"HIGH_SLIPPAGE_WARNING: {symbol} plan implies {slippage_pct*100:.2f}% slippage.")

        return plan_summary

    def _aggregate_liquidity(self, side: str, snapshots: Dict[str, Any]) -> List[LiquidityBucket]:
        """تحويل بيانات البورصات الخام إلى كائنات موحدة."""
        pool = []
        target_key = 'asks' if side == "BUY" else 'bids'
        
        for exchange, data in snapshots.items():
            # التحقق من صحة البيانات
            if target_key not in data: continue
            
            book_levels = data[target_key] # [[price, qty], [price, qty]...]
            conf = self.exchange_config.get(exchange, {"taker_fee": 0.001, "trust": 0.5})
            
            for price, qty in book_levels:
                # تصفية "الغبار" (الكميات التافهة) لتسريع المعالجة
                if (price * qty) > 10.0: 
                    pool.append(LiquidityBucket(
                        exchange=exchange,
                        price=float(price),
                        available_qty=float(qty),
                        fee_rate=conf["taker_fee"],
                        trust_score=conf["trust"]
                    ))
        return pool

    def _calculate_effective_price(self, bucket: LiquidityBucket, is_buy: bool) -> float:
        """
        حساب السعر الحقيقي بعد الرسوم.
        Buy: Price * (1 + fee)
        Sell: Price * (1 - fee)
        """
        if is_buy:
            return bucket.price * (1.0 + bucket.fee_rate)
        else:
            # في البيع، نريد السعر الأعلى. لكن هنا نحن نرتب للأفضلية.
            # لجعل الـ sort يعمل بشكل موحد، يمكننا إرجاع السعر الصافي الذي سنستلمه.
            return bucket.price * (1.0 - bucket.fee_rate)