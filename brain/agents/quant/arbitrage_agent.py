# Price Discrepancy Hunter

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - ARBITRAGE HUNTER AGENT
# =================================================================
# Component Name: brain/agents/quant/arbitrage_agent.py
# Core Responsibility: البحث عن فرص المراجحة السعرية والزمنية بين البورصات المختلفة (Profitability Pillar).
# Design Pattern: Agent / Opportunity Scanner
# Forensic Impact: يوثق الفرص "شبه المؤكدة". إذا فشلت صفقة مراجحة، فالسبب غالباً هو "انزلاق التنفيذ" (Execution Slippage).
# =================================================================

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class ArbitrageAgent:
    """
    وكيل المراجحة (Arbitrageur).
    يقوم بمسح الأسواق المتعددة بحثاً عن فروق سعرية تغطي تكاليف التداول والنقل.
    """

    def __init__(self, min_profit_threshold: float = 0.002):
        """
        تهيئة الوكيل.
        
        Args:
            min_profit_threshold: الحد الأدنى للربح الصافي (0.2% افتراضياً).
        """
        self.logger = logging.getLogger("Alpha.Brain.Quant.Arbitrage")
        
        # إعدادات الرسوم الافتراضية (يجب تحديثها ديناميكياً من API البورصة)
        # Taker Fee: الرسوم التي تدفعها عند الأخذ من السيولة (Market Order)
        self.exchange_fees = {
            "BINANCE": 0.00075, # 0.075% (BNB Burn)
            "KRAKEN": 0.0026,   # 0.26%
            "COINBASE": 0.0060, # 0.60%
            "DYDX": 0.0005      # 0.05%
        }
        
        self.min_profit = min_profit_threshold

    def scan_spatial_arbitrage(self, market_snapshot: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        البحث عن المراجحة المكانية (Spatial Arbitrage).
        شراء من بورصة A وبيع في بورصة B.
        
        Args:
            market_snapshot: قاموس يحتوي الأسعار لكل بورصة لنفس العملة.
            Structure: {
                'BINANCE': {'bid': 50000, 'ask': 50001},
                'KRAKEN': {'bid': 50100, 'ask': 50110}
            }
            
        Returns:
            قائمة بالفرص المتاحة.
        """
        opportunities = []
        exchanges = list(market_snapshot.keys())
        
        # مقارنة كل بورصة بالأخرى (Pairwise Comparison)
        for i in range(len(exchanges)):
            for j in range(len(exchanges)):
                if i == j: continue
                
                ex_buy = exchanges[i]
                ex_sell = exchanges[j]
                
                data_buy = market_snapshot[ex_buy]
                data_sell = market_snapshot[ex_sell]
                
                # التحقق من صحة البيانات
                if not self._is_valid_quote(data_buy) or not self._is_valid_quote(data_sell):
                    continue

                # المعادلة: نشتري من Ask (المعروض) ونبيع للـ Bid (المطلوب)
                buy_price = data_buy['ask']
                sell_price = data_sell['bid']
                
                # حساب هامش الربح الخام (Gross Spread)
                if sell_price > buy_price:
                    gross_spread = (sell_price - buy_price) / buy_price
                    
                    # حساب صافي الربح بعد الرسوم (Net Profit)
                    net_profit = self._calculate_net_profit(gross_spread, ex_buy, ex_sell)
                    
                    if net_profit >= self.min_profit:
                        # تم العثور على فرصة ذهبية!
                        opp = {
                            "type": "SPATIAL_ARB",
                            "timestamp": datetime.utcnow().isoformat(),
                            "asset": data_buy.get('symbol', 'UNKNOWN'),
                            "buy_exchange": ex_buy,
                            "sell_exchange": ex_sell,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "gross_spread_pct": round(gross_spread * 100, 4),
                            "net_profit_pct": round(net_profit * 100, 4),
                            "estimated_fees": round((gross_spread - net_profit) * 100, 4)
                        }
                        opportunities.append(opp)
                        
                        # تسجيل جنائي للتوثيق
                        self.logger.info(f"ARB_FOUND: {ex_buy}->{ex_sell} | Net: {opp['net_profit_pct']}%")

        return opportunities

    def scan_triangular_arbitrage(self, rates: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        البحث عن المراجحة المثلثية (Triangular Arbitrage) داخل نفس البورصة.
        مثال: BTC -> ETH -> USDT -> BTC.
        """
        # (يتطلب منطقاً خاصاً بالرسم البياني للأزواج، نضعه هنا كإطار عمل)
        # TODO: Implement graph cycle detection for triangular arb
        return None

    def _calculate_net_profit(self, gross_spread: float, ex_buy: str, ex_sell: str) -> float:
        """
        حساب الربح الصافي بخصم رسوم التداول في البورصتين.
        """
        fee_buy = self.exchange_fees.get(ex_buy, 0.001) # 0.1% default
        fee_sell = self.exchange_fees.get(ex_sell, 0.001)
        
        # الربح الصافي تقريباً = الهامش - مجموع الرسوم
        # (المعادلة الدقيقة: (1+spread) * (1-fee_sell) * (1-fee_buy) - 1)
        # لكن للسرعة نستخدم الطرح التقريبي للنسب الصغيرة
        net_profit = gross_spread - (fee_buy + fee_sell)
        
        return net_profit

    def _is_valid_quote(self, quote: Dict[str, Any]) -> bool:
        """التحقق من سلامة التسعير (لتجنب البيانات الفاسدة)."""
        return (
            quote.get('ask', 0) > 0 and 
            quote.get('bid', 0) > 0 and 
            quote.get('ask') > quote.get('bid') # منطقياً Ask دائماً أعلى من Bid
        )