# Interest Rates & GDP Logic

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - MACROECONOMIC REGIME ANALYZER
# =================================================================
# Component Name: brain/agents/macro/economy_analyst.py
# Core Responsibility: ربط معدلات الفائدة، التضخم، والناتج المحلي بالتحركات السعرية للأصول (Intelligence Pillar).
# Design Pattern: Agent / State Machine
# Forensic Impact: يوفر "ذريعة منطقية" لتقليل المخاطر. يوثق أن "النظام انسحب لأن الاقتصاد ينهار"، وليس بسبب خطأ برمجي.
# =================================================================

import logging
from typing import Dict, Any, Tuple
from datetime import datetime

class EconomyAnalyst:
    """
    محلل الاقتصاد الكلي.
    يحدد "النظام الاقتصادي" (Economic Regime) الحالي:
    (Growth, Stagflation, Recession, Goldilocks).
    يتحكم في "صنبور السيولة" العام للنظام.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Macro.Economy")
        
        # العتبات المرجعية (يجب تحديثها دورياً بناءً على الحقبة الاقتصادية)
        self.thresholds = {
            "high_inflation": 3.0,      # CPI > 3%
            "high_interest_rate": 4.0,  # Fed Funds Rate > 4%
            "strong_dxy": 105.0,        # Dollar Index > 105
            "recession_gdp": 0.0        # GDP Growth < 0%
        }

    def evaluate_macro_landscape(self, macro_data: Dict[str, float]) -> Dict[str, Any]:
        """
        تقييم المشهد الاقتصادي العام.
        
        Args:
            macro_data: {
                'cpi_yoy': 3.5,          # التضخم
                'fed_funds_rate': 5.25,  # الفائدة
                'gdp_growth': 1.2,       # النمو
                'unemployment': 4.1,     # البطالة
                'dxy_index': 103.5,      # قوة الدولار
                'm2_supply_growth': -2.0 # السيولة النقدية
            }
        """
        # 1. التحقق من اكتمال البيانات
        # الاقتصاد الكلي بطيء التحديث، لذا قد نستخدم بيانات الشهر الماضي
        if not macro_data:
            return self._neutral_outlook("NO_DATA")

        try:
            # 2. تحديد المرحلة الاقتصادية (The Cycle)
            regime = self._determine_regime(macro_data)
            
            # 3. تحليل السيولة (Liquidity Analysis)
            # هل البنك المركزي يضخ أم يسحب الأموال؟
            liquidity_status = self._analyze_liquidity(macro_data)
            
            # 4. عامل تخصيص رأس المال (Allocation Multiplier)
            # هذا هو الرقم الأهم: كم نسبة المحفظة التي يجب المخاطرة بها؟
            # 1.0 = مخاطرة كاملة، 0.0 = كاش بالكامل
            allocation_factor = self._calculate_allocation_factor(regime, liquidity_status, macro_data)

            return {
                "agent": "EconomyAnalyst",
                "timestamp": datetime.utcnow().isoformat(),
                "macro_regime": regime, # e.g., "STAGFLATION"
                "liquidity_condition": liquidity_status, # e.g., "TIGHTENING"
                "key_metrics": {
                    "inflation_gap": macro_data.get('cpi_yoy', 0) - 2.0, # البعد عن هدف 2%
                    "real_yield": macro_data.get('fed_funds_rate', 0) - macro_data.get('cpi_yoy', 0)
                },
                "risk_management": {
                    "allocation_multiplier": round(allocation_factor, 2),
                    "recommended_asset_class": self._recommend_assets(regime)
                },
                "forensic_reasoning": f"Regime is {regime} with {liquidity_status} liquidity. Allocation adjusted to {allocation_factor}x."
            }

        except Exception as e:
            self.logger.error(f"MACRO_ERROR: فشل التحليل الاقتصادي: {e}")
            return self._neutral_outlook(str(e))

    def _determine_regime(self, data: Dict[str, float]) -> str:
        """تحديد المربع الاقتصادي."""
        cpi = data.get('cpi_yoy', 2.0)
        gdp = data.get('gdp_growth', 1.5)
        
        high_inf = cpi > self.thresholds['high_inflation']
        growth = gdp > 0.5 # نمو إيجابي
        
        if growth and not high_inf:
            return "GOLDILOCKS" # الحالة المثالية: نمو بلا تضخم (شراء قوي)
        elif growth and high_inf:
            return "INFLATIONARY_BOOM" # نمو مع تضخم (شراء سلع/كريبتو)
        elif not growth and high_inf:
            return "STAGFLATION" # الركود التضخمي (أسوأ حالة - كاش)
        else: # not growth and not high_inf
            return "RECESSION" # ركود انكماشي (شراء سندات)

    def _analyze_liquidity(self, data: Dict[str, float]) -> str:
        """تحليل ظروف السيولة النقدية."""
        m2 = data.get('m2_supply_growth', 0)
        rate = data.get('fed_funds_rate', 0)
        dxy = data.get('dxy_index', 100)
        
        # الدولار القوي يمتص السيولة من الأسواق العالمية
        strong_dollar = dxy > self.thresholds['strong_dxy']
        
        if m2 > 0 and not strong_dollar:
            return "EXPANDING" # طباعة أموال
        elif m2 < 0 or strong_dollar:
            return "CONTRACTING" # سحب سيولة
        else:
            return "NEUTRAL"

    def _calculate_allocation_factor(self, regime: str, liquidity: str, data: Dict[str, float]) -> float:
        """
        حساب معامل المخاطرة المسموح به (0.0 إلى 1.0).
        هذا المنطق يحمي المحفظة من الانهيار في الأوقات الصعبة.
        """
        base_factor = 0.5 # البداية من المنتصف
        
        # تعديل بناءً على النظام الاقتصادي
        if regime == "GOLDILOCKS": base_factor = 1.0
        elif regime == "INFLATIONARY_BOOM": base_factor = 0.8
        elif regime == "RECESSION": base_factor = 0.3
        elif regime == "STAGFLATION": base_factor = 0.1 # اهرب فوراً
        
        # تعديل بناءً على السيولة
        if liquidity == "CONTRACTING":
            base_factor *= 0.7 # خفض المخاطرة 30% إذا كانت السيولة تشح
            
        # تعديل خاص بالكريبتو: الكريبتو يكره الفائدة المرتفعة
        real_rate = data.get('fed_funds_rate', 0) - data.get('cpi_yoy', 0)
        if real_rate > 2.0: # فائدة حقيقية موجبة جداً
            base_factor *= 0.8
            
        return min(max(base_factor, 0.0), 1.0) # حصر النتيجة بين 0 و 1

    def _recommend_assets(self, regime: str) -> List[str]:
        mapping = {
            "GOLDILOCKS": ["STOCKS", "CRYPTO", "TECH"],
            "INFLATIONARY_BOOM": ["COMMODITIES", "REAL_ESTATE", "BITCOIN"],
            "STAGFLATION": ["CASH", "GOLD", "DEFENSIVE_STOCKS"],
            "RECESSION": ["BONDS", "GOV_DEBT"]
        }
        return mapping.get(regime, ["CASH"])

    def _neutral_outlook(self, reason: str) -> Dict[str, Any]:
        return {
            "agent": "EconomyAnalyst",
            "macro_regime": "UNKNOWN",
            "risk_management": {"allocation_multiplier": 0.5},
            "error": reason
        }