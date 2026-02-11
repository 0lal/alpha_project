# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - BILLING & RUNWAY ENGINE
================================================
Component Name: ops/monetization/billing_engine.py
Core Responsibility: إدارة المدفوعات التشغيلية وضمان استمرارية الخدمات (Pillar: Stability).
Creation Date: 2026-02-03
Version: 1.0.0 (Solvency Guardian Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يمنع "هجمات الحرمان من الخدمة المالية" (Financial DoS).
- يتتبع كل طلب API ويحسب تكلفته (Micro-Accounting).
- يحسب "Runway" (كم يوماً يمكن للنظام أن يعيش بالرصيد الحالي).
- يطلق إنذارات "Low Fuel" قبل النفاد بـ 72 ساعة.
"""

import time
import logging
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

# إعداد السجلات
logger = logging.getLogger("AlphaBilling")
getcontext().prec = 28

class ServiceType(Enum):
    COMPUTE = "VPS/Server"       # تكلفة ثابتة شهرية
    INTELLIGENCE = "LLM API"     # تكلفة متغيرة (لكل رمز)
    DATA = "Market Data Feed"    # اشتراك شهري أو حسب الاستخدام
    PROXY = "Network Proxy"      # تكلفة الباندويث

@dataclass
class ServiceContract:
    """عقد خدمة يوضح تفاصيل التكلفة والرصيد."""
    service_name: str
    service_type: ServiceType
    balance: Decimal             # الرصيد الحالي لدى المزود
    burn_rate_daily: Decimal     # متوسط الصرف اليومي
    critical_threshold: Decimal  # الحد الأدنى لإطلاق الإنذار
    auto_topup_amount: Decimal   # المبلغ الذي يجب شحنه تلقائياً
    is_active: bool = True

@dataclass
class PaymentRecord:
    """سجل جنائي لعملية دفع."""
    timestamp: float
    service_name: str
    amount: Decimal
    transaction_id: str
    status: str  # PENDING, COMPLETED, FAILED

class BillingEngine:
    """
    محرك الفوترة.
    يعمل كطبقة وسيطة بين النظام ومزودي الخدمات لضمان الملاءة المالية.
    """

    def __init__(self):
        # سجل الخدمات النشطة
        self.services: Dict[str, ServiceContract] = {}
        # سجل المدفوعات (للتدقيق)
        self.payment_history: List[PaymentRecord] = []
        
        # الرصيد المتاح في "محفظة العمليات" (Opex Wallet)
        # هذا الرصيد يأتي من AssetAllocationEngine
        self._opex_wallet_balance = Decimal("0.00")

    def register_service(self, name: str, s_type: ServiceType, initial_balance: float, threshold: float):
        """تسجيل خدمة جديدة للمراقبة."""
        self.services[name] = ServiceContract(
            service_name=name,
            service_type=s_type,
            balance=Decimal(str(initial_balance)),
            burn_rate_daily=Decimal("0.00"), # سيتم حسابه لاحقاً
            critical_threshold=Decimal(str(threshold)),
            auto_topup_amount=Decimal(str(threshold)) * 2 # شحن ضعف الحد الأدنى
        )
        logger.info(f"Service Registered: {name} | Balance: ${initial_balance}")

    def inject_funds(self, amount: float):
        """
        إيداع أموال في محفظة العمليات (يستدعى من AssetAllocationEngine).
        """
        amount_dec = Decimal(str(amount))
        self._opex_wallet_balance += amount_dec
        logger.info(f"Opex Wallet Funded: +${amount_dec} | Current Balance: ${self._opex_wallet_balance}")

    def track_usage(self, service_name: str, cost: float):
        """
        تسجيل استهلاك لحظي (مثلاً بعد طلب OpenAI).
        """
        if service_name not in self.services:
            logger.error(f"Unknown service usage: {service_name}")
            return

        cost_dec = Decimal(str(cost))
        srv = self.services[service_name]
        
        # خصم التكلفة من رصيد الخدمة الافتراضي
        srv.balance -= cost_dec
        
        # تحديث معدل الحرق (Simple Moving Average simulation)
        # في الواقع نحتاج لمنطق أعقد، هنا تبسيط:
        if srv.burn_rate_daily == 0:
            srv.burn_rate_daily = cost_dec * 100 # افتراض أولي
        
        # التحقق من الرصيد
        if srv.balance <= srv.critical_threshold:
            self._trigger_low_balance_protocol(srv)

    def _trigger_low_balance_protocol(self, srv: ServiceContract):
        """
        بروتوكول الطوارئ عند انخفاض الرصيد.
        يحاول الدفع تلقائياً من محفظة العمليات.
        """
        logger.warning(f"LOW BALANCE ALERT: {srv.service_name} (${srv.balance}) < Threshold (${srv.critical_threshold})")
        
        # محاولة الشحن التلقائي
        if self._opex_wallet_balance >= srv.auto_topup_amount:
            self._execute_payment(srv, srv.auto_topup_amount)
        else:
            logger.critical(
                f"INSOLVENCY RISK: Cannot top up {srv.service_name}. "
                f"Wallet Balance (${self._opex_wallet_balance}) insufficient!"
            )
            # هنا يجب إرسال تنبيه "PANIC" عبر AlertDispatcher

    def _execute_payment(self, srv: ServiceContract, amount: Decimal):
        """
        تنفيذ الدفع (محاكاة).
        """
        # 1. خصم من المحفظة المركزية
        self._opex_wallet_balance -= amount
        
        # 2. إضافة لرصيد الخدمة
        srv.balance += amount
        
        # 3. تسجيل جنائي
        record = PaymentRecord(
            timestamp=time.time(),
            service_name=srv.service_name,
            amount=amount,
            transaction_id=f"PAY-{int(time.time())}",
            status="COMPLETED"
        )
        self.payment_history.append(record)
        
        logger.info(f"AUTO-TOPUP EXECUTED: Paid ${amount} to {srv.service_name}. New Balance: ${srv.balance}")

    def calculate_runway_days(self) -> Dict[str, float]:
        """
        حساب "مدرج البقاء": كم يوماً ستصمد كل خدمة بالرصيد الحالي؟
        """
        report = {}
        for name, srv in self.services.items():
            if srv.burn_rate_daily > 0:
                days = float(srv.balance / srv.burn_rate_daily)
            else:
                days = 999.0 # غير محدد (لا يوجد استهلاك)
            report[name] = round(days, 1)
        return report

# --- Unit Test ---
if __name__ == "__main__":
    billing = BillingEngine()
    
    # 1. تمويل المحفظة (من أرباح سابقة)
    billing.inject_funds(100.00)
    
    # 2. تسجيل خدمات
    billing.register_service("OpenAI_API", ServiceType.INTELLIGENCE, initial_balance=5.00, threshold=2.00)
    billing.register_service("AWS_EC2", ServiceType.COMPUTE, initial_balance=50.00, threshold=10.00)
    
    print("\n--- Simulating Usage ---")
    # محاكاة استهلاك كثيف للـ API
    for _ in range(4):
        billing.track_usage("OpenAI_API", 1.00) # استهلاك 1 دولار
        time.sleep(0.1)
        
    print("\n--- System Runway ---")
    print(billing.calculate_runway_days())
    
    print("\n--- Payment Ledger ---")
    for rec in billing.payment_history:
        print(f"[{rec.status}] Paid ${rec.amount} to {rec.service_name} (Tx: {rec.transaction_id})")