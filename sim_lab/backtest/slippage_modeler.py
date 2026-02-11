# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - REALISTIC SLIPPAGE MODELER
=================================================================
Component: sim_lab/backtest/slippage_modeler.py
Core Responsibility: محاكاة تأثير السوق (Market Impact) والانزلاق السعري لضمان واقعية الاختبارات (Realism Pillar).
Design Pattern: Strategy Pattern / Mathematical Modeling
Forensic Impact: يمنع "خداع الذات" في النتائج. يسجل تكلفة السيولة لكل صفقة افتراضية.
=================================================================
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.slippage")

@dataclass
class MarketSnapshot:
    """لقطة لبيانات السوق في لحظة التنفيذ"""
    price: float
    volume_24h: float       # حجم التداول اليومي (لقياس عمق السوق)
    volatility_atr: float   # متوسط المدى الحقيقي (لقياس التقلب)
    bid_ask_spread: float   # الفارق السعري الحالي

@dataclass
class ExecutionReport:
    """تقرير التنفيذ المعدل"""
    requested_price: float
    executed_price: float
    slippage_cost: float
    slippage_bps: float     # نقاط أساس (Basis Points)
    reason: str             # مصدر الانزلاق (Spread vs Impact)

class SlippageModeler:
    """
    نموذج يحاكي فيزياء السوق.
    يعتمد على "قانون الجذر التربيعي لتأثير السوق" (Square Root Law of Market Impact).
    Formula: Impact ~= Volatility * sqrt(OrderSize / DailyVolume)
    """

    def __init__(self, impact_factor: float = 0.5, min_spread_bps: float = 5.0):
        self.impact_factor = impact_factor # معامل ضبط الحساسية (يعتمد على المنصة)
        self.min_spread_bps = min_spread_bps # الحد الأدنى للانزلاق (Spread Floor)

    def calculate_execution(self, 
                          side: str, 
                          order_size: float, 
                          snapshot: MarketSnapshot) -> ExecutionReport:
        """
        حساب سعر التنفيذ الواقعي.
        side: 'BUY' or 'SELL'
        """
        if order_size <= 0 or snapshot.price <= 0:
            return ExecutionReport(snapshot.price, snapshot.price, 0.0, 0.0, "INVALID_INPUT")

        # 1. تكلفة الفارق السعري (Spread Cost)
        # حتى في أفضل الظروف، ستدفع نصف الفارق السعري
        spread_cost_abs = snapshot.bid_ask_spread / 2.0
        
        # التأكد من أن الفارق لا يقل عن الحد الأدنى (للمحاكاة المتحفظة)
        min_spread_abs = snapshot.price * (self.min_spread_bps / 10000.0)
        base_cost = max(spread_cost_abs, min_spread_abs)

        # 2. تكلفة تأثير السوق (Market Impact Cost)
        # كلما زاد حجم الأمر مقارنة بحجم السوق، زاد الانزلاق بشكل غير خطي
        # نستخدم نسخة مبسطة من نموذج Almgren-Chriss
        
        # تجنب القسمة على صفر
        safe_volume = max(snapshot.volume_24h, order_size * 100) 
        
        participation_rate = order_size / safe_volume
        
        # التأثير يعتمد على التقلب (ATR) ونسبة المشاركة
        market_impact_pct = self.impact_factor * snapshot.volatility_atr * np.sqrt(participation_rate)
        market_impact_abs = snapshot.price * market_impact_pct

        # 3. التكلفة الإجمالية
        total_slippage = base_cost + market_impact_abs

        # 4. حساب السعر النهائي
        if side.upper() == 'BUY':
            executed_price = snapshot.price + total_slippage
        else: # SELL
            executed_price = snapshot.price - total_slippage

        # حساب نقاط الأساس للتقرير
        slippage_bps = (total_slippage / snapshot.price) * 10000

        # تحديد السبب الرئيسي (لأغراض التحليل)
        reason = "SPREAD_DOMINANT" if base_cost > market_impact_abs else "VOLUME_IMPACT_DOMINANT"

        # تسجيل جنائي للصفقات الكبيرة ذات الانزلاق العالي
        if slippage_bps > 50: # أكثر من 0.5% انزلاق
            logger.warning(
                f"SLIPPAGE_ALERT: High slippage detected ({slippage_bps:.1f} bps). "
                f"Size: {order_size}, Vol: {snapshot.volume_24h}, Impact: {market_impact_abs:.4f}"
            )

        return ExecutionReport(
            requested_price=snapshot.price,
            executed_price=executed_price,
            slippage_cost=total_slippage * order_size, # التكلفة بالدولار
            slippage_bps=slippage_bps,
            reason=reason
        )

# =================================================================
# اختبار المحاكاة (Unit Test)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    modeler = SlippageModeler(impact_factor=0.8, min_spread_bps=2.0)
    
    # سيناريو: سوق سائل (Liquid Market) - BTC
    btc_snapshot = MarketSnapshot(
        price=60000.0,
        volume_24h=10_000_000_000.0, # 10 مليار
        volatility_atr=0.02,         # 2%
        bid_ask_spread=10.0          # فارق ضيق
    )
    
    print("--- Test 1: Small BTC Order (High Liquidity) ---")
    report = modeler.calculate_execution('BUY', 1.0, btc_snapshot) # شراء 1 بيتكوين
    print(f"Req: {report.requested_price} -> Exec: {report.executed_price:.2f}")
    print(f"Slippage: {report.slippage_bps:.2f} bps | Reason: {report.reason}")

    # سيناريو: عملة ميمية منخفضة السيولة (Illiquid Shitcoin)
    shitcoin_snapshot = MarketSnapshot(
        price=1.0,
        volume_24h=50_000.0,    # حجم تداول ضعيف جداً
        volatility_atr=0.10,    # تقلب عالي 10%
        bid_ask_spread=0.05     # فارق واسع (5%)
    )

    print("\n--- Test 2: Large Shitcoin Order (Low Liquidity) ---")
    # محاولة شراء بـ 10,000 دولار (20% من حجم السوق اليومي!)
    report_whale = modeler.calculate_execution('BUY', 10_000.0, shitcoin_snapshot)
    print(f"Req: {report_whale.requested_price} -> Exec: {report_whale.executed_price:.4f}")
    print(f"Slippage: {report_whale.slippage_bps:.2f} bps ({report_whale.slippage_bps/100:.2f}%)")
    print(f"Cost: ${report_whale.slippage_cost:.2f} | Reason: {report_whale.reason}")