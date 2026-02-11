# Portfolio Balance Guardian

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - PORTFOLIO EXPOSURE MONITOR
# =================================================================
# Component Name: brain/agents/risk/exposure_agent.py
# Core Responsibility: مراقبة التعرض الكلي وتوزيع الأصول لمنع الانهيارات المتسلسلة (Risk Management Pillar).
# Design Pattern: Agent / Circuit Breaker
# Forensic Impact: يمنع "التدمير الذاتي" (Self-Immolation) الناتج عن الرافعة المالية المفرطة.
# =================================================================

import logging
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime

class ExposureAgent:
    """
    وكيل التعرض للمخاطر.
    يحسب المخاطر الهيكلية للمحفظة (Structural Risk).
    """

    def __init__(self, max_leverage: float = 2.0, max_concentration: float = 0.20):
        """
        Args:
            max_leverage: الحد الأقصى للرافعة المالية المسموح بها (مثلاً 2x).
            max_concentration: الحد الأقصى لحجم صفقة واحدة نسبةً لرأس المال (مثلاً 20%).
        """
        self.logger = logging.getLogger("Alpha.Brain.Risk.Exposure")
        self.max_leverage = max_leverage
        self.max_concentration = max_concentration
        
        # حدود القطاعات (لتجنب المخاطرة في قطاع واحد مثل DeFi أو Meme)
        self.sector_limits = {
            "L1_COINS": 0.50, # يسمح بـ 50% في العملات الأساسية (BTC, ETH)
            "DEFI": 0.25,
            "MEME": 0.05,     # لا تزيد عن 5% أبداً
            "STABLE": 1.00
        }

    def analyze_portfolio(self, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل صحة المحفظة ومستويات التعرض.
        
        Args:
            portfolio_state: {
                "total_equity": 10000.0,
                "positions": [
                    {"symbol": "BTCUSDT", "side": "LONG", "notional_value": 5000, "unrealized_pnl": 200, "category": "L1_COINS"},
                    {"symbol": "ETHUSDT", "side": "SHORT", "notional_value": 3000, "unrealized_pnl": -50, "category": "L1_COINS"}
                ]
            }
        """
        equity = portfolio_state.get("total_equity", 0.0)
        positions = portfolio_state.get("positions", [])
        
        if equity <= 0:
            return self._critical_alert("INSOLVENCY_RISK", "Equity is zero or negative!")

        # 1. حساب المقاييس الأساسية (Core Metrics)
        # Gross Exposure: مجموع القيمة المطلقة لكل الصفقات (يقيس المخاطرة الكلية)
        # Net Exposure: الفرق بين الشراء والبيع (يقيس الاتجاهية Directionality)
        gross_exposure = sum(p["notional_value"] for p in positions)
        net_exposure = sum(p["notional_value"] if p["side"] == "LONG" else -p["notional_value"] for p in positions)
        
        current_leverage = gross_exposure / equity
        net_exposure_ratio = net_exposure / equity

        # 2. فحص الحدود القصوى (Limit Checks)
        violations = []
        
        # A. فحص الرافعة المالية
        if current_leverage > self.max_leverage:
            violations.append(f"OVER_LEVERAGED: Current {current_leverage:.2f}x > Max {self.max_leverage}x")

        # B. فحص التركيز (Concentration Risk)
        concentration_warnings = self._check_concentrations(positions, equity)
        violations.extend(concentration_warnings)

        # C. فحص التعرض للقطاعات (Sector Exposure)
        sector_warnings = self._check_sector_limits(positions, equity)
        violations.extend(sector_warnings)

        # 3. القرار وتوصيات التخفيف (Mitigation)
        status = "HEALTHY"
        action = "NONE"
        
        if violations:
            status = "CRITICAL" if current_leverage > self.max_leverage * 1.2 else "WARNING"
            action = "REDUCE_EXPOSURE"
            self.logger.warning(f"EXPOSURE_ALERT: {violations}")

        return {
            "agent": "ExposureAgent",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "equity": equity,
                "gross_exposure": round(gross_exposure, 2),
                "net_exposure": round(net_exposure, 2),
                "current_leverage": round(current_leverage, 2),
                "net_exposure_ratio": round(net_exposure_ratio, 2)
            },
            "status": status,
            "violations": violations,
            "recommended_action": action,
            "allowed_new_exposure_usd": max(0, (equity * self.max_leverage) - gross_exposure)
        }

    def _check_concentrations(self, positions: List[Dict[str, Any]], equity: float) -> List[str]:
        """فحص ما إذا كانت عملة واحدة تسيطر على المحفظة."""
        warnings = []
        for p in positions:
            ratio = p["notional_value"] / equity
            if ratio > self.max_concentration:
                warnings.append(f"CONCENTRATION_RISK: {p['symbol']} is {ratio*100:.1f}% of equity (Max {self.max_concentration*100}%)")
        return warnings

    def _check_sector_limits(self, positions: List[Dict[str, Any]], equity: float) -> List[str]:
        """فحص التعرض للقطاعات."""
        sector_exposure = {}
        warnings = []
        
        # تجميع القيم حسب القطاع
        for p in positions:
            cat = p.get("category", "UNKNOWN")
            sector_exposure[cat] = sector_exposure.get(cat, 0.0) + p["notional_value"]
            
        # التحقق من الحدود
        for cat, value in sector_exposure.items():
            ratio = value / equity
            limit = self.sector_limits.get(cat, 0.20) # 20% default limit for unknown sectors
            if ratio > limit:
                warnings.append(f"SECTOR_RISK: {cat} exposure {ratio*100:.1f}% exceeds limit {limit*100}%")
                
        return warnings

    def _critical_alert(self, type_str: str, msg: str) -> Dict[str, Any]:
        self.logger.critical(f"{type_str}: {msg}")
        return {
            "status": "EMERGENCY",
            "violations": [msg],
            "recommended_action": "HALT_TRADING"
        }