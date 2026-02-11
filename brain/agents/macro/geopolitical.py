# Conflict & Stability Analysis

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - GEOPOLITICAL RISK ANALYZER
# =================================================================
# Component Name: brain/agents/macro/geopolitical.py
# Core Responsibility: تحليل أثر النزاعات والأحداث الجيوسياسية على استقرار الأصول (Intelligence Pillar).
# Design Pattern: Agent / Impact Mapper
# Forensic Impact: يبرر التحوط المفاجئ (Sudden Hedging). يوثق أن "بيع الأسهم لم يكن خطأً، بل رد فعل لتهديد عسكري".
# =================================================================

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class GeopoliticalAnalyst:
    """
    محلل المخاطر الجيوسياسية.
    يقوم بتحويل الأخبار السياسية (حروب، انتخابات، عقوبات) إلى معاملات رياضية تؤثر على المحفظة.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Macro.Geo")
        
        # 1. خريطة الأهمية الاقتصادية للمناطق (Regional Economic Weights)
        # ماذا يحدث لو اشتعلت هذه المنطقة؟
        self.regional_impact_map = {
            "MIDDLE_EAST":  {"assets": ["OIL", "GOLD"], "weight": 0.9, "risk_type": "ENERGY_SHOCK"},
            "EAST_ASIA":    {"assets": ["TECH", "SEMICONDUCTORS", "BTC"], "weight": 0.8, "risk_type": "SUPPLY_CHAIN"},
            "EAST_EUROPE":  {"assets": ["WHEAT", "GAS", "EUR"], "weight": 0.7, "risk_type": "COMMODITY_SHOCK"},
            "USA":          {"assets": ["USD", "ALL_MARKETS"], "weight": 1.0, "risk_type": "SYSTEMIC"},
        }

        # 2. مصفوفة الارتباط (Correlation Matrix) في أوقات الأزمات
        # كيف تتصرف الأصول عند الخوف؟ (Flight to Safety)
        self.crisis_correlations = {
            "WAR":          {"GOLD": 1.0, "OIL": 0.8, "STOCKS": -0.8, "CRYPTO": 0.2}, # الكريبتو متذبذب في الحروب
            "SANCTIONS":    {"GOLD": 0.5, "USD": -0.2, "CRYPTO": 0.9}, # العقوبات ترفع الكريبتو (أداة هروب)
            "PANDEMIC":     {"GOLD": 0.8, "TECH": 0.5, "TRAVEL": -1.0},
            "ELECTION":     {"VOLATILITY": 1.0} # الانتخابات تزيد التقلب بغض النظر عن الاتجاه
        }

    def assess_event_impact(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل حدث جيوسياسي وتقدير تأثيره.
        
        Args:
            event: {
                "type": "CONFLICT",      # WAR, ELECTION, SANCTIONS, TREATY
                "region": "MIDDLE_EAST",
                "severity": 0.8,         # 0.0 to 1.0 (NLP Sentiment Intensity)
                "description": "Naval blockade reported in Strait of Hormuz"
            }
        """
        try:
            event_type = event.get("type", "UNKNOWN")
            region = event.get("region", "GLOBAL")
            severity = event.get("severity", 0.5)
            
            # 1. تحديد مستوى التهديد العالمي (Global Tension Index)
            # المعادلة: أهمية المنطقة * شدة الحدث
            region_info = self.regional_impact_map.get(region, {"weight": 0.3, "assets": []})
            impact_score = region_info["weight"] * severity

            # 2. تحديد الأصول المتأثرة
            affected_assets = region_info.get("assets", [])
            
            # 3. صياغة استراتيجية الدفاع (Defensive Strategy)
            defense_mode = "NONE"
            if impact_score > 0.7:
                defense_mode = "MAX_HEDGE" # تحوط كامل (شراء ذهب/دولار، تسييل الأسهم)
            elif impact_score > 0.4:
                defense_mode = "REDUCE_EXPOSURE" # تقليل حجم الصفقات
            
            # 4. تحليل خاص للكريبتو (Crypto Specific Logic)
            # هل الحدث يدعم سردية "الذهب الرقمي" أم يدعم سردية "الأصول الخطرة"؟
            crypto_outlook = self._analyze_crypto_impact(event_type, impact_score)

            result = {
                "agent": "GeopoliticalAnalyst",
                "timestamp": datetime.utcnow().isoformat(),
                "event_id": event.get("id"),
                "analysis": {
                    "global_impact_score": round(impact_score, 2), # 0.0 - 1.0
                    "primary_risk": region_info.get("risk_type", "UNKNOWN"),
                    "affected_sectors": affected_assets,
                    "defense_protocol": defense_mode
                },
                "asset_adjustments": {
                    "GOLD": self._get_adjustment(event_type, "GOLD", severity),
                    "OIL": self._get_adjustment(event_type, "OIL", severity),
                    "CRYPTO": crypto_outlook
                },
                "forensic_note": f"Detected {event_type} in {region} with severity {severity}. Triggering {defense_mode}."
            }
            
            # إنذار عالي المستوى إذا كان التهديد وجودياً
            if impact_score > 0.85:
                self.logger.critical(f"GEOPOLITICAL_DEFCON_1: {event.get('description')} - EXECUTE EMERGENCY PROTOCOLS.")

            return result

        except Exception as e:
            self.logger.error(f"GEO_ANALYSIS_FAIL: {e}")
            return {"error": str(e)}

    def _analyze_crypto_impact(self, event_type: str, impact_score: float) -> str:
        """
        تحديد موقف الكريبتو: هل هو ملاذ آمن أم أصل خطر؟
        """
        # في حالة العقوبات أو انهيار العملات الورقية -> الكريبتو ملاذ آمن (Bullish)
        if event_type in ["SANCTIONS", "CURRENCY_CRISIS", "CAPITAL_CONTROLS"]:
            return "STRONG_BUY (Censorship Resistance)"
        
        # في حالة الحرب العالمية أو أزمة السيولة -> الكريبتو يباع كأصل خطر (Bearish)
        # لأن الناس يبيعون كل شيء للحصول على الدولار (Cash is King)
        if event_type == "CONFLICT" and impact_score > 0.7:
            return "SELL (Liquidity Crunch Risk)"
            
        return "NEUTRAL"

    def _get_adjustment(self, event_type: str, asset_class: str, severity: float) -> float:
        """حساب معامل التعديل المقترح للمحفظة (+1.0 شراء قوي، -1.0 بيع قوي)."""
        correlation = self.crisis_correlations.get(event_type, {}).get(asset_class, 0.0)
        return round(correlation * severity, 2)