# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - TAX & FEE FORENSIC LEDGER
==================================================
Component Name: ops/monetization/tax_fee_ledger.py
Core Responsibility: تدوين دقيق لكل العمولات والرسوم لضمان شفافية "صافي الربح" (Pillar: Explainability).
Creation Date: 2026-02-03
Version: 1.0.0 (The Auditor Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يفصل بين "الربح الإجمالي" (Gross) و"الربح الصافي" (Net).
- يتتبع رسوم الـ Gas (في العملات الرقمية) بشكل منفصل لأنها تعتبر تكلفة تشغيلية وليست خسارة تداول.
- يجهز البيانات للتقارير الضريبية (FIFO/LIFO) إذا تطلب الأمر مستقبلاً.
"""

import csv
import time
import logging
import threading
from decimal import Decimal, getcontext
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from enum import Enum
from pathlib import Path

# إعداد السجلات
logger = logging.getLogger("AlphaLedger")
getcontext().prec = 28  # دقة مالية عالية

class FeeType(Enum):
    EXCHANGE_COMMISSION = "COMMISSION"  # رسوم المنصة (0.1% مثلاً)
    NETWORK_GAS = "GAS_FEE"             # رسوم التحويل (ETH Gas)
    SPREAD_COST = "SPREAD"              # تكلفة الانزلاق (Hidden Cost)
    WITHDRAWAL_FEE = "WITHDRAWAL"       # رسوم السحب
    FUNDING_RATE = "FUNDING"            # رسوم التمويل في العقود الآجلة

@dataclass(frozen=True) # تجميد البيانات لضمان عدم التلاعب (Immutability)
class FeeEntry:
    """سجل واحد لرسوم مدفوعة."""
    entry_id: str           # معرف فريد (UUID)
    trade_id: str           # ربط بالصفقة الأصلية
    timestamp: float        # وقت الدفع
    fee_type: str           # نوع الرسم (من Enum)
    amount: Decimal         # القيمة
    asset: str              # العملة المدفوع بها (e.g., BNB, USDT, ETH)
    platform: str           # Binance, DEX, etc.

class TaxFeeLedger:
    """
    السجل المحاسبي المركزي.
    """

    def __init__(self, export_dir: str = "data/financials"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.csv_file = self.export_dir / "fees_ledger.csv"
        
        self._lock = threading.Lock()
        self._entries: List[FeeEntry] = []
        
        # التأكد من وجود ملف CSV مع الترويسة
        self._init_csv()

    def _init_csv(self):
        """إنشاء ملف السجل إذا لم يكن موجوداً."""
        if not self.csv_file.exists():
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["EntryID", "TradeID", "Time", "Type", "Amount", "Asset", "Platform"])

    def record_fee(self, trade_id: str, fee_type: FeeType, amount: float, asset: str, platform: str = "Unknown") -> FeeEntry:
        """
        تسجيل رسم جديد.
        """
        if amount < 0:
            logger.warning(f"Negative fee detected for trade {trade_id}! Assessing as rebate.")

        entry = FeeEntry(
            entry_id=f"FEE-{int(time.time()*1000)}",
            trade_id=trade_id,
            timestamp=time.time(),
            fee_type=fee_type.value,
            amount=Decimal(str(amount)),
            asset=asset.upper(),
            platform=platform
        )

        with self._lock:
            self._entries.append(entry)
            self._flush_to_disk(entry)

        logger.info(f"FEE RECORDED: {amount} {asset} ({fee_type.value}) for Trade {trade_id}")
        return entry

    def _flush_to_disk(self, entry: FeeEntry):
        """كتابة السجل فوراً للقرص (Persistence)."""
        try:
            with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    entry.entry_id,
                    entry.trade_id,
                    time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(entry.timestamp)),
                    entry.fee_type,
                    f"{entry.amount:.8f}",
                    entry.asset,
                    entry.platform
                ])
        except Exception as e:
            logger.error(f"Failed to write fee to CSV: {e}")

    def calculate_period_costs(self, start_time: float, end_time: float) -> Dict[str, Decimal]:
        """
        حساب إجمالي التكاليف في فترة زمنية معينة (مقسمة حسب العملة).
        مثال: كم دفعنا USDT و BNB اليوم؟
        """
        totals = {}
        
        with self._lock:
            # فلترة السجلات في الذاكرة
            relevant_entries = [
                e for e in self._entries 
                if start_time <= e.timestamp <= end_time
            ]
            
            for entry in relevant_entries:
                if entry.asset not in totals:
                    totals[entry.asset] = Decimal("0.0")
                totals[entry.asset] += entry.amount
                
        return totals

    def estimate_tax_deductible(self) -> Decimal:
        """
        تقدير التكاليف القابلة للخصم الضريبي (محاكاة).
        عادة، رسوم التداول تخصم من الأرباح.
        """
        # هنا سنفترض أننا نحسب كل الرسوم المسجلة كخصومات
        total_deduction_usd = Decimal("0.0")
        
        # تنويه: هذا يتطلب معرفة سعر صرف العملة (Asset) مقابل الدولار لحظة الدفع.
        # للتبسيط هنا، سنفترض أن كل الرسوم بـ USDT.
        for entry in self._entries:
            if entry.asset in ["USDT", "USDC", "USD"]:
                total_deduction_usd += entry.amount
        
        return total_deduction_usd

# --- Unit Test ---
if __name__ == "__main__":
    ledger = TaxFeeLedger("data/test_financials")
    
    print("--- Simulating Trading Fees ---")
    
    # 1. رسم صفقة عادية
    ledger.record_fee("TRD-101", FeeType.EXCHANGE_COMMISSION, 0.50, "USDT", "Binance")
    
    # 2. رسم غاز (شبكة)
    ledger.record_fee("TRD-102", FeeType.NETWORK_GAS, 0.002, "ETH", "Uniswap")
    
    # 3. رسم تمويل (Futures Funding)
    ledger.record_fee("TRD-103", FeeType.FUNDING_RATE, 1.20, "USDT", "Bybit")
    
    time.sleep(0.1)
    
    # حساب التكاليف
    now = time.time()
    costs = ledger.calculate_period_costs(now - 3600, now) # آخر ساعة
    
    print("\n--- Cost Summary (Last Hour) ---")
    for asset, amount in costs.items():
        print(f"Total {asset}: {amount}")
        
    print(f"\n[+] Ledger saved to: {ledger.csv_file.absolute()}")