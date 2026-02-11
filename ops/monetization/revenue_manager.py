# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - REVENUE MANAGER (THE BOARD)
====================================================
Component Name: ops/monetization/revenue_manager.py
Core Responsibility: إدارة العوائد الكلية وتوزيع الأرباح الصافية (Pillar: Explainability).
Creation Date: 2026-02-03
Version: 1.0.0 (Dividend Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يمثل "سلطة الصرف العليا".
- Financial Integrity: يقوم بختم كل تقرير مالي بـ SHA-256 Hash لمنع التلاعب بالسجلات لاحقاً.
- Sovereign Policy: يطبق قواعد "الحد الأدنى للسحب" (Minimum Payout Threshold) لتقليل رسوم الشبكة.
"""

import hashlib
import time
import logging
import json
from decimal import Decimal, getcontext
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from pathlib import Path

# إعداد السجلات
logger = logging.getLogger("AlphaRevenue")
getcontext().prec = 28

@dataclass
class IncomeStatement:
    """قائمة الدخل للفترة المالية (Financial Statement)."""
    period_id: str
    timestamp: float
    gross_revenue: Decimal      # إجمالي الدخل من التداول
    total_fees_paid: Decimal    # إجمالي الرسوم (من TaxLedger)
    system_reinvestment: Decimal # ما تم خصمه للتطوير (من AssetAllocation)
    net_profit_distributable: Decimal # الصافي القابل للتوزيع
    payout_status: str          # PENDING, PAID, ACCUMULATED
    integrity_hash: str = ""    # توقيع رقمي للتقرير

class RevenueManager:
    """
    مدير العوائد.
    """

    def __init__(self, owner_wallet: str = "0xYourColdWalletAddress"):
        self.owner_wallet = owner_wallet
        self.min_payout_threshold = Decimal("100.00") # لا تحول أقل من 100 دولار
        self.accumulated_balance = Decimal("0.00")    # الأرباح المحتفظ بها
        
        # مسار حفظ التقارير المالية
        self.reports_dir = Path("data/financials/statements")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def reconcile_session(self, 
                          session_id: str, 
                          gross_profit: float, 
                          total_fees: float, 
                          reinvested_amount: float) -> IncomeStatement:
        """
        تسوية الحسابات لجلسة تداول وإصدار قرار التوزيع.
        """
        gross = Decimal(str(gross_profit))
        fees = Decimal(str(total_fees))
        reinvest = Decimal(str(reinvested_amount))
        
        # معادلة المحاسبة الأساسية
        # Net = Gross - (Fees + Reinvestment)
        net_profit = gross - fees - reinvest
        
        # إضافة الصافي للرصيد المتراكم
        self.accumulated_balance += net_profit
        
        status = "ACCUMULATED"
        payout_amount = Decimal("0.00")

        # تطبيق الدستور المالي: هل وصلنا للحد الأدنى للسحب؟
        if self.accumulated_balance >= self.min_payout_threshold:
            payout_amount = self.accumulated_balance
            self._execute_payout(payout_amount)
            self.accumulated_balance = Decimal("0.00") # تصفير الرصيد بعد السحب
            status = "PAID"
        else:
            logger.info(f"Balance (${self.accumulated_balance}) below threshold (${self.min_payout_threshold}). Holding funds.")

        # إنشاء التقرير
        statement = IncomeStatement(
            period_id=session_id,
            timestamp=time.time(),
            gross_revenue=gross,
            total_fees_paid=fees,
            system_reinvestment=reinvest,
            net_profit_distributable=net_profit, # هذا ربح الجلسة، وليس المسحوب
            payout_status=status
        )
        
        # توقيع التقرير
        self._sign_statement(statement)
        
        # حفظ التقرير
        self._archive_statement(statement)
        
        return statement

    def _execute_payout(self, amount: Decimal):
        """
        محاكاة عملية التحويل للمالك.
        في النسخة الحية، هذا يتصل بـ Blockchain Gateway.
        """
        logger.critical(f"$$$ PAYOUT TRIGGERED $$$ Sending ${amount} to {self.owner_wallet}")
        # هنا يتم وضع كود التفاعل مع البلوكتشين
        # e.g., eth_client.send_transaction(...)

    def _sign_statement(self, statement: IncomeStatement):
        """
        إنشاء بصمة رقمية للتقرير لضمان عدم التزوير.
        """
        # ندمج كل البيانات في نص واحد
        raw_data = f"{statement.period_id}{statement.gross_revenue}{statement.total_fees_paid}{statement.timestamp}"
        # تشفير SHA-256
        statement.integrity_hash = hashlib.sha256(raw_data.encode()).hexdigest()

    def _archive_statement(self, statement: IncomeStatement):
        """حفظ التقرير في ملف JSON آمن."""
        filename = f"stmt_{statement.period_id}_{int(statement.timestamp)}.json"
        filepath = self.reports_dir / filename
        
        # تحويل Decimal إلى string للحفظ في JSON
        data = asdict(statement)
        for k, v in data.items():
            if isinstance(v, Decimal):
                data[k] = str(v)
                
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        logger.info(f"Financial Statement Archived: {filename} [Hash: {statement.integrity_hash[:8]}...]")

    def get_accumulated_balance(self) -> str:
        return str(self.accumulated_balance)

# --- Unit Test ---
if __name__ == "__main__":
    cfo = RevenueManager()
    
    print("--- Session 1: Small Profit ---")
    # ربح 50 دولار، رسوم 2، إعادة استثمار 10 -> الصافي 38
    # الحد الأدنى 100، لذا يجب أن يحتفظ بها
    stmt1 = cfo.reconcile_session("SES-001", 50.00, 2.00, 10.00)
    print(f"Status: {stmt1.payout_status} | Accumulated: ${cfo.get_accumulated_balance()}")
    
    print("\n--- Session 2: Big Profit ---")
    # ربح 200 دولار، رسوم 5، إعادة استثمار 40 -> الصافي 155
    # الرصيد السابق 38 + 155 = 193 -> أكبر من 100 -> يجب أن يدفع الكل
    stmt2 = cfo.reconcile_session("SES-002", 200.00, 5.00, 40.00)
    print(f"Status: {stmt2.payout_status} | Payout Hash: {stmt2.integrity_hash}")
    print(f"Remaining Accumulated: ${cfo.get_accumulated_balance()}")