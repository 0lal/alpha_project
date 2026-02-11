# Monte Carlo Simulator

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - REAL-TIME STRESS TESTING ENGINE
# =================================================================
# Component Name: brain/agents/risk/stress_tester.py
# Core Responsibility: تشغيل محاكاة "ماذا لو" لحظية لكل قرار (Risk Management Pillar).
# Design Pattern: Scenario Analysis / Monte Carlo Lite
# Forensic Impact: يوفر "شهادة البقاء" (Survival Certificate) لكل صفقة. إذا خسرت الصفقة لاحقاً، لدينا دليل أنها كانت سليمة وقت اتخاذ القرار.
# =================================================================

import logging
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class DoomScenario:
    name: str
    price_shock_pct: float    # صدمة السعر (مثلاً -0.20 لانهيار 20%)
    volatility_mult: float    # مضاعف التقلب (لتوسيع الـ Spread)
    correlation_break: bool   # هل تفشل علاقات التحوط؟

class StressTester:
    """
    مختبر الإجهاد.
    يطبق مصفوفة من سيناريوهات الكوارث التاريخية والافتراضية على المحفظة + الصفقة المقترحة.
    """

    def __init__(self, risk_aversion_level: float = 0.95):
        self.logger = logging.getLogger("Alpha.Brain.Risk.StressTest")
        self.confidence_level = risk_aversion_level
        
        # تعريف سيناريوهات الكوارث (The Doom Matrix)
        # هذه السيناريوهات مستوحاة من أحداث حقيقية (مثل انهيار مارس 2020، وانهيار FTX)
        self.scenarios = [
            # السيناريو 1: انهيار خاطف (Flash Crash)
            DoomScenario("FLASH_CRASH", price_shock_pct=-0.15, volatility_mult=3.0, correlation_break=False),
            
            # السيناريو 2: ضغط شراء (Short Squeeze) - خطير لصفقات البيع
            DoomScenario("SUPER_PUMP", price_shock_pct=0.20, volatility_mult=2.5, correlation_break=False),
            
            # السيناريو 3: أزمة سيولة شاملة (Liquidity Crunch)
            DoomScenario("LIQUIDITY_DEATH", price_shock_pct=-0.05, volatility_mult=10.0, correlation_break=True),
        ]

    def simulate_proposal(self, proposal: Dict[str, Any], current_portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        تشغيل المحاكاة على الصفقة المقترحة.
        
        Args:
            proposal: {symbol, side, quantity, current_price}
            current_portfolio: {equity, positions: [...]}
            
        Returns:
            نتيجة الاختبار (PASS/FAIL) مع تقرير التأثير.
        """
        equity = current_portfolio.get("total_equity", 1.0)
        if equity <= 0:
            return self._reject("Portfolio already insolvent")

        # 1. دمج الصفقة المقترحة مع المحفظة الحالية (Virtual Portfolio)
        # لنسأل: كيف سيبدو شكلنا بعد هذه الصفقة؟
        simulated_positions = self._merge_proposal(proposal, current_portfolio["positions"])
        
        worst_case_drawdown = 0.0
        failed_scenarios = []
        survival_score = 100.0

        # 2. حلقة التعذيب: تطبيق السيناريوهات
        for scenario in self.scenarios:
            simulated_equity = self._calculate_scenario_equity(
                equity, simulated_positions, scenario, proposal["symbol"]
            )
            
            drawdown_pct = (equity - simulated_equity) / equity
            
            # إذا كان الانهيار يتجاوز حد التصفية (مثلاً خسارة 50% من رأس المال في لحظة)
            # أو إذا أصبح الرصيد سالباً (الإفلاس)
            if simulated_equity <= 0 or drawdown_pct > 0.40: # 40% Max Drawdown allowed per event
                failed_scenarios.append(f"{scenario.name} (DD: {drawdown_pct*100:.1f}%)")
                survival_score -= 33.0 # خصم كبير من درجة النجاة
                
                # تحديث أسوأ حالة
                if drawdown_pct > worst_case_drawdown:
                    worst_case_drawdown = drawdown_pct

        # 3. الحكم النهائي
        is_safe = len(failed_scenarios) == 0
        
        result = {
            "agent": "StressTester",
            "passed": is_safe,
            "survival_score": max(0.0, round(survival_score, 1)),
            "worst_case_drawdown_pct": round(worst_case_drawdown * 100, 2),
            "failed_scenarios": failed_scenarios,
            "forensic_audit": f"Tested {len(self.scenarios)} extreme scenarios."
        }
        
        if not is_safe:
            self.logger.warning(f"STRESS_FAIL: Proposal {proposal['side']} {proposal['symbol']} rejected. Failed: {failed_scenarios}")

        return result

    def _calculate_scenario_equity(self, 
                                   start_equity: float, 
                                   positions: List[Dict[str, Any]], 
                                   scenario: DoomScenario,
                                   target_symbol: str) -> float:
        """
        حساب قيمة رأس المال في ظل السيناريو المحدد.
        """
        pnl_shock = 0.0
        
        for pos in positions:
            symbol = pos["symbol"]
            side = pos["side"] # LONG or SHORT
            size = pos["quantity"]
            price = pos["entry_price"] # أو السعر الحالي للتبسيط
            
            # تحديد حركة السعر بناءً على السيناريو
            # في سيناريوهات "كسر الارتباط"، كل شيء ينهار معاً
            # في السيناريوهات العادية، قد نستخدم بيتا (Beta) للأصل، لكن هنا نفترض الأسوأ (صدمة كاملة)
            
            shock = scenario.price_shock_pct
            
            # إذا كان السيناريو "انهيار ارتباط"، فالأصول التي نعتبرها تحوطاً (Hedges) قد تفشل وتتحرك ضدنا
            # للتبسيط والتحوط الأقصى: نفترض أن السعر يتحرك *دائماً* ضد مركزنا في اختبار الإجهاد
            if side == "LONG":
                # السعر ينخفض
                price_move = -abs(shock) 
            else: # SHORT
                # السعر يرتفع
                price_move = abs(shock)
            
            # تطبيق مضاعف التقلب على الانزلاق (Slippage)
            # تكلفة الخروج تزيد في الأزمات
            liquidity_cost = (price * 0.001) * scenario.volatility_mult * size # 0.1% base slippage
            
            # حساب الربح/الخسارة
            # PnL = Size * Price * %Move
            position_pnl = (size * price * price_move) - liquidity_cost
            pnl_shock += position_pnl

        return start_equity + pnl_shock

    def _merge_proposal(self, proposal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        إنشاء قائمة مراكز افتراضية (Deep Copy + Proposal).
        """
        # نسخ القائمة لتجنب تعديل البيانات الأصلية (Side Effect Free)
        simulated = [p.copy() for p in current_positions]
        
        # إضافة المقترح
        # (في الواقع يجب دمج المراكز المتشابهة، لكن الإضافة كعنصر جديد تكفي للاختبار)
        simulated.append({
            "symbol": proposal["symbol"],
            "side": proposal["side"],
            "quantity": proposal["quantity"],
            "entry_price": proposal.get("current_price", 0.0)
        })
        
        return simulated

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {"passed": False, "survival_score": 0.0, "reason": reason}