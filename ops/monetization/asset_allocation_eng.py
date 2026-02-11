# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - ASSET ALLOCATION ENGINE (CFO)
======================================================
Component Name: ops/monetization/asset_allocation_eng.py
Core Responsibility: توزيع الأرباح بذكاء ديناميكي (Pillar: Adaptability).
Creation Date: 2026-02-03
Version: 1.0.0 (Compound Interest Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يتعامل مع "المال".
- الدقة الحسابية: نستخدم مكتبة `decimal` لمنع أخطاء الفاصلة العائمة (Floating Point Errors).
- استراتيجية التكيف: النسب المئوية ليست ثابتة؛ تتغير بناءً على "صحة النظام" (Health Score).
- التدقيق: كل سنت يتم تحريكه يسجل برقم مرجعي فريد (Transaction ID).
"""

import logging
import uuid
import time
from decimal import Decimal, ROUND_HALF_UP, getcontext
from dataclasses import dataclass, asdict
from typing import Dict, Optional

# إعداد السجلات
logger = logging.getLogger("AlphaCFO")

# ضبط دقة الحسابات المالية (28 خانة عشرية)
getcontext().prec = 28

@dataclass
class AllocationStrategy:
    """القواعد الحاكمة لتوزيع الأموال (السياسة المالية)."""
    reinvestment_ratio: Decimal    # إعادة استثمار (زيادة حجم الصفقات)
    hardware_reserve_ratio: Decimal # تطوير العتاد (شراء سيرفرات، دفع فواتير سحابية)
    opex_ratio: Decimal            # مصاريف تشغيلية (API Fees, Data Subs)
    owner_dividend_ratio: Decimal  # أرباح المالك (Sovereignty)

    def validate(self) -> bool:
        """التأكد من أن النسب مجموعها 1.0 (100%)"""
        total = (self.reinvestment_ratio + self.hardware_reserve_ratio + 
                 self.opex_ratio + self.owner_dividend_ratio)
        return total == Decimal("1.0")

@dataclass
class AllocationResult:
    """تقرير التوزيع النهائي لعملية ربح واحدة."""
    transaction_id: str
    total_profit: Decimal
    reinvested_amount: Decimal
    hardware_fund_amount: Decimal
    opex_fund_amount: Decimal
    owner_payout_amount: Decimal
    timestamp: float
    strategy_used: str

class AssetAllocationEngine:
    """
    المحرك المالي.
    يستقبل الأرباح ويقطع "الكعكة" بناءً على احتياجات النظام الحالية.
    """

    def __init__(self):
        # السياسة الافتراضية: التركيز على النمو (Growth Mode)
        self.default_strategy = AllocationStrategy(
            reinvestment_ratio=Decimal("0.60"),      # 60% نمو
            hardware_reserve_ratio=Decimal("0.20"),  # 20% تطوير
            opex_ratio=Decimal("0.10"),              # 10% مصاريف
            owner_dividend_ratio=Decimal("0.10")     # 10% للمالك
        )
        
        # الأرصدة المتراكمة (Virtual Ledgers)
        self.ledgers = {
            "reinvestment": Decimal("0.0"),
            "hardware": Decimal("0.0"),
            "opex": Decimal("0.0"),
            "owner": Decimal("0.0")
        }

    def process_profit_event(self, profit_amount: float, system_health: Dict[str, str] = None) -> Optional[AllocationResult]:
        """
        معالجة حدث ربح جديد وتوزيعه.
        :param profit_amount: قيمة الربح بالدولار/USDT.
        :param system_health: حالة النظام (لتعديل الاستراتيجية ديناميكياً).
        """
        amount = Decimal(str(profit_amount))
        
        if amount <= 0:
            logger.warning(f"Ignored non-positive profit event: {amount}")
            return None

        # 1. تحديد الاستراتيجية بناءً على وضع النظام
        strategy = self._adjust_strategy_dynamic(system_health)
        
        if not strategy.validate():
            logger.critical("Allocation Strategy sum != 100%. Freezing funds.")
            return None

        # 2. الحساب الدقيق
        reinvest = (amount * strategy.reinvestment_ratio).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        hardware = (amount * strategy.hardware_reserve_ratio).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        opex = (amount * strategy.opex_ratio).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        
        # الباقي يذهب للمالك (لضمان عدم ضياع كسور السنت بسبب التقريب)
        owner = amount - (reinvest + hardware + opex)

        # 3. تحديث الدفاتر (Ledgers)
        self.ledgers["reinvestment"] += reinvest
        self.ledgers["hardware"] += hardware
        self.ledgers["opex"] += opex
        self.ledgers["owner"] += owner

        # 4. إصدار التقرير
        tx_id = str(uuid.uuid4())
        logger.info(f"PROFIT ALLOCATED [{tx_id}]: +${amount} -> Reinvest:${reinvest} | HW:${hardware} | Owner:${owner}")
        
        return AllocationResult(
            transaction_id=tx_id,
            total_profit=amount,
            reinvested_amount=reinvest,
            hardware_fund_amount=hardware,
            opex_fund_amount=opex,
            owner_payout_amount=owner,
            timestamp=time.time(),
            strategy_used="DYNAMIC_ADAPTIVE" if system_health else "DEFAULT_GROWTH"
        )

    def _adjust_strategy_dynamic(self, health_context: Optional[Dict]) -> AllocationStrategy:
        """
        العقل المالي: يغير النسب بناءً على الحاجة.
        """
        if not health_context:
            return self.default_strategy

        # مثال: إذا كان العتاد يعاني (Hardware status is CRITICAL)
        # نقوم بزيادة ميزانية العتاد فوراً على حساب أرباح المالك وإعادة الاستثمار
        if health_context.get("hardware_status") == "WARNING":
            logger.info("ADAPTING STRATEGY: Increasing Hardware Budget due to System Strain.")
            return AllocationStrategy(
                reinvestment_ratio=Decimal("0.40"),      # خفض النمو
                hardware_reserve_ratio=Decimal("0.40"),  # مضاعفة ميزانية العتاد
                opex_ratio=Decimal("0.10"),
                owner_dividend_ratio=Decimal("0.10")
            )
        
        return self.default_strategy

    def get_ledger_balances(self) -> Dict[str, str]:
        """عرض الأرصدة الحالية (لواجهة المستخدم)."""
        return {k: str(v) for k, v in self.ledgers.items()}

# --- Unit Test ---
if __name__ == "__main__":
    cfo = AssetAllocationEngine()
    
    print("--- Simulating Profit Allocation ---")
    
    # سيناريو 1: ربح طبيعي والنظام سليم
    print("\n[Event 1] Profit: $1000, System: Healthy")
    res1 = cfo.process_profit_event(1000.00)
    print(asdict(res1))

    # سيناريو 2: ربح والنظام يعاني من حرارة عالية (يحتاج صيانة)
    print("\n[Event 2] Profit: $500, System: Stressed (Hardware Warning)")
    health_report = {"hardware_status": "WARNING"}
    res2 = cfo.process_profit_event(500.00, system_health=health_report)
    print(asdict(res2))
    
    # عرض الأرصدة النهائية
    print("\n--- Final Treasury Balances ---")
    print(cfo.get_ledger_balances())