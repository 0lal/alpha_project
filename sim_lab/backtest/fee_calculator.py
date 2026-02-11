# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVANCED FEE & COST CALCULATOR
=================================================================
Component: sim_lab/backtest/fee_calculator.py
Core Responsibility: حساب دقيق للتكاليف لضمان واقعية صافي الربح (Realism Pillar).
Design Pattern: Strategy Pattern / Configurable Calculator
Forensic Impact: يمنع "الأرباح الوهمية" (Paper Profits). يسجل تكلفة كل صفقة بدقة محاسبية.
=================================================================
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.fees")

class OrderType(Enum):
    MAKER = "MAKER" # توفير سيولة (Limit Order)
    TAKER = "TAKER" # أخذ سيولة (Market Order)

class ExchangeType(Enum):
    CEX = "CEX" # بورصة مركزية (Binance, Bybit)
    DEX = "DEX" # بورصة لامركزية (Uniswap)

@dataclass
class FeeStructure:
    """هيكل الرسوم للبورصة"""
    maker_rate: float       # نسبة مئوية (e.g., 0.001 for 0.1%)
    taker_rate: float       # نسبة مئوية
    flat_fee_usd: float = 0.0 # رسوم ثابتة (للشبكة أو الغاز)
    bn_discount: bool = False # هل يوجد خصم للعملة الأصلية (BNB)?

@dataclass
class CostReport:
    """تقرير التكاليف النهائية"""
    gross_amount: float     # المبلغ قبل الرسوم
    fee_amount: float       # قيمة العمولة
    net_amount: float       # المبلغ الصافي
    effective_rate: float   # النسبة الفعلية المخصومة
    note: str

class FeeCalculator:
    def __init__(self):
        # قاعدة بيانات الرسوم الافتراضية (يمكن تحديثها من الإعدادات)
        self.registry: Dict[str, FeeStructure] = {
            # Binance VIP 0
            "BINANCE_VIP0": FeeStructure(maker_rate=0.001, taker_rate=0.001),
            # Binance VIP 0 + BNB Discount (25% off)
            "BINANCE_VIP0_BNB": FeeStructure(maker_rate=0.00075, taker_rate=0.00075, bn_discount=True),
            # Bybit VIP 0
            "BYBIT_VIP0": FeeStructure(maker_rate=0.001, taker_rate=0.001),
            # Uniswap (Ethereum L1 - High Gas Simulation)
            "UNISWAP_ETH": FeeStructure(maker_rate=0.003, taker_rate=0.003, flat_fee_usd=15.0), # $15 Gas
            # PancakeSwap (BSC - Low Gas)
            "PANCAKESWAP_BSC": FeeStructure(maker_rate=0.0025, taker_rate=0.0025, flat_fee_usd=0.30)
        }

    def calculate_cost(self, 
                      exchange_id: str, 
                      order_type: OrderType, 
                      price: float, 
                      amount: float,
                      extra_latency_ms: int = 0) -> CostReport:
        """
        حساب التكلفة الإجمالية للصفقة.
        """
        gross_val = price * amount
        structure = self.registry.get(exchange_id, self.registry["BINANCE_VIP0"]) # Default to Binance

        # 1. تحديد النسبة الأساسية (Maker vs Taker)
        base_rate = structure.maker_rate if order_type == OrderType.MAKER else structure.taker_rate
        
        # 2. حساب العمولة النسبية
        percentage_fee = gross_val * base_rate

        # 3. إضافة الرسوم الثابتة (Gas Fees)
        # الرسوم الثابتة لا تعتمد على حجم الصفقة
        total_fee = percentage_fee + structure.flat_fee_usd

        # 4. محاكاة الانزلاق التقني (Technical Slippage / Execution Drift)
        # هذا يختلف عن انزلاق السوق. هذا تكلفة "البنية التحتية".
        # كل 10ms تأخير قد يكلف جزءاً من السعر في الأسواق السريعة (HFT context).
        # فرضية: كل 100ms تأخير تكلف 0.1 نقطة أساس (Basis Point)
        tech_slippage_cost = 0.0
        if extra_latency_ms > 0:
            drift_bps = (extra_latency_ms / 100.0) * 0.0001
            tech_slippage_cost = gross_val * drift_bps
            total_fee += tech_slippage_cost

        net_val = gross_val - total_fee
        effective_rate_bps = (total_fee / gross_val) * 10000 if gross_val > 0 else 0

        note = f"{exchange_id} | {order_type.name} | Base Rate: {base_rate*100}%"
        if structure.flat_fee_usd > 0:
            note += f" + Gas: ${structure.flat_fee_usd}"
        if tech_slippage_cost > 0:
            note += f" + Latency Cost: ${tech_slippage_cost:.4f}"

        # تسجيل للتدقيق إذا كانت الرسوم مرتفعة جداً (نسبة وتناسب)
        # مثلاً في DEX، صفقة بـ 10 دولار ورسوم غاز 15 دولار!
        if total_fee > (gross_val * 0.1): # Fees > 10% of trade
            logger.warning(f"FEE_ALERT: Fees represent {effective_rate_bps/100:.2f}% of trade value! (Small trade on high fee network?)")

        return CostReport(
            gross_amount=gross_val,
            fee_amount=total_fee,
            net_amount=net_val,
            effective_rate=effective_rate_bps,
            note=note
        )

# =================================================================
# اختبار المحاكاة (Unit Test)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    calc = FeeCalculator()
    
    print("--- Test 1: Standard Binance Trade ---")
    # شراء 1 BTC بـ 50,000$ (Taker)
    report1 = calc.calculate_cost("BINANCE_VIP0", OrderType.TAKER, 50000.0, 1.0)
    print(f"Gross: ${report1.gross_amount:,.2f}")
    print(f"Fee:   ${report1.fee_amount:,.2f} ({report1.note})")
    print(f"Net:   ${report1.net_amount:,.2f}")

    print("\n--- Test 2: Small DEX Trade (High Gas Impact) ---")
    # شراء ما قيمته 50$ من ETH على Uniswap
    report2 = calc.calculate_cost("UNISWAP_ETH", OrderType.TAKER, 3000.0, 0.0166) 
    print(f"Gross: ${report2.gross_amount:,.2f}")
    print(f"Fee:   ${report2.fee_amount:,.2f} ({report2.note})")
    print(f"Effective Rate: {report2.effective_rate/100:.2f}% (Should be huge)")

    print("\n--- Test 3: HFT Latency Penalty ---")
    # صفقة سريعة ولكن بتأخير شبكي 200ms
    report3 = calc.calculate_cost("BYBIT_VIP0", OrderType.MAKER, 1000.0, 10.0, extra_latency_ms=200)
    print(f"Gross: ${report3.gross_amount:,.2f}")
    print(f"Fee:   ${report3.fee_amount:,.2f}")
    print(f"Note:  {report3.note}")