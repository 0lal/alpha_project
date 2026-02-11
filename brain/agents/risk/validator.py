# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - CONSTITUTIONAL VALIDATOR (VERSION 5.0)
=================================================================
Component: brain/agents/risk/validator.py
Core Responsibility: المحكمة الدستورية العليا لكل أمر تداول.
Forensic Features:
  - Decimal Arithmetic (دقة مالية مطلقة لمنع أخطاء التقريب).
  - Smart Wash Trading Detection (كشف التلاعب الحقيقي وليس الظاهري).
  - Dynamic Rule Injection (قواعد مرنة لا تحتاج لإعادة تشغيل).
  - Verdict Traceability (توثيق جنائي لسبب الرفض).
=================================================================
"""

import logging
from decimal import Decimal, getcontext, ROUND_DOWN
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# ضبط دقة الحسابات المالية عالمياً داخل هذا المديول
getcontext().prec = 28

class TradeVerdict:
    """كبسولة الحكم النهائي على الأمر"""
    __slots__ = ('valid', 'code', 'reason', 'risk_score', 'timestamp')
    
    def __init__(self, valid: bool, code: str, reason: str, risk_score: float = 0.0):
        self.valid = valid
        self.code = code
        self.reason = reason
        self.risk_score = risk_score
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "code": self.code,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "timestamp": self.timestamp
        }

class ConstitutionalValidator:
    """
    المدقق الدستوري.
    لا يرحم في الأخطاء الحسابية، ولكنه مرن في التكتيكات الاستراتيجية.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Risk.Validator")
        
        # 1. الدستور الثابت (Hard Constraints)
        self.const_max_order_value = Decimal("5000.0")  # أقصى قيمة للأمر الواحد (حماية Fat Finger)
        self.const_min_notional = Decimal("10.0")       # الحد الأدنى للبورصة
        
        # 2. القوائم الديناميكية (يمكن تحديثها أثناء التشغيل)
        self.banned_assets = {"LUNA", "FTT", "UST"}
        self.restricted_modes = {"HFT_MANIPULATION", "PUMP_DUMP"}

    def validate_order(self, order: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        جلسة المحاكمة الفورية للأمر.
        
        Args:
            order: تفاصيل الأمر المراد تنفيذه.
            context: السياق المحيط (الأوامر المفتوحة، حالة السوق).
        """
        try:
            # تحويل الأرقام إلى Decimal فوراً لضمان الدقة
            try:
                qty = Decimal(str(order.get("quantity", 0)))
                price = Decimal(str(order.get("price", 0)))
                notional = qty * price if price > 0 else Decimal("0")
            except Exception:
                return TradeVerdict(False, "MALFORMED_NUMBERS", "Non-numeric values detected").to_dict()

            # ---------------------------------------------------------
            # المستوى 1: الفحص التقني (Technical Sanity)
            # ---------------------------------------------------------
            if qty <= 0:
                return TradeVerdict(False, "ZERO_QTY", "Quantity must be positive").to_dict()
            
            if order.get("type") == "LIMIT" and price <= 0:
                return TradeVerdict(False, "ZERO_PRICE", "Limit order must have positive price").to_dict()

            # ---------------------------------------------------------
            # المستوى 2: الفحص الجنائي (Asset Integrity)
            # ---------------------------------------------------------
            symbol = order.get("symbol", "").upper()
            if self._is_blacklisted(symbol):
                return TradeVerdict(False, "BANNED_ASSET", f"Symbol {symbol} contains blacklisted asset").to_dict()

            # ---------------------------------------------------------
            # المستوى 3: إدارة المخاطر المالية (Financial Risk)
            # ---------------------------------------------------------
            # فحص الغبار (Dust Check)
            if order.get("type") == "LIMIT" and notional < self.const_min_notional:
                return TradeVerdict(False, "DUST_ERROR", f"Order value {notional} < Min {self.const_min_notional}").to_dict()

            # فحص الإصبع السمين (Fat Finger)
            if notional > self.const_max_order_value:
                # إذا تجاوز الحد، نرفض فوراً لحماية الرصيد
                return TradeVerdict(False, "FAT_FINGER", f"Value {notional} exceeds safety cap {self.const_max_order_value}").to_dict()

            # ---------------------------------------------------------
            # المستوى 4: الامتثال القانوني (Legal Compliance)
            # ---------------------------------------------------------
            # فحص التداول الذاتي الذكي (Smart Wash Trading Check)
            open_orders = context.get("open_orders", [])
            if self._detect_smart_wash_trading(order, open_orders, price):
                return TradeVerdict(False, "WASH_TRADING_VIOLATION", "Order execution would result in self-trade").to_dict()

            # ---------------------------------------------------------
            # الحكم النهائي: براءة
            # ---------------------------------------------------------
            return TradeVerdict(True, "APPROVED", "Passed all constitutional checks").to_dict()

        except Exception as e:
            self.logger.critical(f"VALIDATOR_CRASH: {e}", exc_info=True)
            # في حالة الشك أو الخطأ البرمجي، نرفض الأمر دائماً (Fail-Safe)
            return TradeVerdict(False, "INTERNAL_ERROR", str(e)).to_dict()

    def _is_blacklisted(self, symbol: str) -> bool:
        """
        فحص ذكي للمنع.
        بدلاً من افتراض USDT، نفحص ما إذا كان الرمز يحتوي على أي أصل محظور.
        """
        for banned in self.banned_assets:
            # مثال: تمنع LUNA سواء كانت LUNAUSDT أو BTCLUNA
            if banned in symbol: 
                return True
        return False

    def _detect_smart_wash_trading(self, new_order: Dict, open_orders: List[Dict], new_price: Decimal) -> bool:
        """
        كشف التداول الذاتي الحقيقي (التنفيذ ضد النفس).
        يسمح بوجود أوامر شراء وبيع لنفس الأصل طالما لا تتقاطع الأسعار (Market Making).
        """
        symbol = new_order.get("symbol")
        side = new_order.get("side") # 0=BUY, 1=SELL (Assumption based on protocol)
        
        # إذا كان أمر سوق (Market Order)، فهو سيأكل أي شيء في طريقه، لذا نفحص إذا كان لدينا أي أمر مفتوح عكسي
        is_market = new_order.get("type") == "MARKET" or new_price == 0

        for existing in open_orders:
            if existing["symbol"] != symbol:
                continue
            
            # تخطي الأوامر الخاصة بنفس الاستراتيجية إذا كانت تعدل أمرها (اختياري)
            # لكن بحسب القانون الصارم، التنفيذ ضد النفس ممنوع حتى لنفس الاستراتيجية
            
            existing_side = existing["side"]
            
            # إذا كنا نشتري، ولدينا أمر بيع مفتوح
            if side == 0 and existing_side == 1: # BUY vs existing SELL
                existing_price = Decimal(str(existing["price"]))
                # إذا كان السعر الجديد >= سعر البيع الموجود، سيحدث تنفيذ فوراً -> Wash Trade
                if is_market or new_price >= existing_price:
                    return True
            
            # إذا كنا نبيع، ولدينا أمر شراء مفتوح
            elif side == 1 and existing_side == 0: # SELL vs existing BUY
                existing_price = Decimal(str(existing["price"]))
                # إذا كان السعر الجديد <= سعر الشراء الموجود، سيحدث تنفيذ فوراً -> Wash Trade
                if is_market or new_price <= existing_price:
                    return True
                    
        return False

    def update_constitution(self, updates: Dict[str, Any]):
        """تحديث القوانين دون إيقاف النظام (Hot-Reload)"""
        if "max_order_value" in updates:
            self.const_max_order_value = Decimal(str(updates["max_order_value"]))
            self.logger.warning(f"CONSTITUTION AMENDED: Max Order Value set to {self.const_max_order_value}")
        if "blacklist_add" in updates:
            self.banned_assets.add(updates["blacklist_add"])

# =================================================================
# Forensic Verification (اختبار ذاتي عند التشغيل المنفصل)
# =================================================================
if __name__ == "__main__":
    validator = ConstitutionalValidator()
    
    # حالة اختبار: تداول ذاتي
    # لدينا أمر بيع معلق عند سعر 100
    mock_context = {
        "open_orders": [
            {"symbol": "BTCUSDT", "side": 1, "price": 100.0, "quantity": 0.5} # Existing SELL
        ]
    }
    
    # نحاول الشراء بسعر 101 (أعلى من البيع -> سيحدث تنفيذ)
    bad_order = {"symbol": "BTCUSDT", "side": 0, "type": "LIMIT", "quantity": 0.1, "price": 101.0}
    
    result = validator.validate_order(bad_order, mock_context)
    print(f"Test 1 (Wash Trade): {result['valid']} -> {result['reason']}")
    
    # حالة اختبار: أمر سليم (Market Making)
    # نحاول الشراء بسعر 99 (أقل من البيع -> لن يحدث تنفيذ، سيصبح Order Book Entry)
    good_order = {"symbol": "BTCUSDT", "side": 0, "type": "LIMIT", "quantity": 0.1, "price": 99.0}
    
    result2 = validator.validate_order(good_order, mock_context)
    print(f"Test 2 (Valid Spread): {result2['valid']} -> {result2['reason']}")