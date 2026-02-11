# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - WEIGHTED CONSENSUS ENGINE (v2.0)
=================================================================
Component: brain/weighted_voter.py
Core Responsibility: المحكمة العليا لاتخاذ القرار (The Supreme Court).
Forensic Features:
  - Dynamic Weighting (تغيير الأوزان بناءً على ملف الإعدادات).
  - Volatility-Awareness (زيادة وزن المخاطر في أوقات الذعر).
  - Veto Traceability (معرفة من أوقف الصفقة ولماذا).
  - Audit Trail Generation (إصدار شهادة ميلاد لكل قرار).
=================================================================
"""

import logging
import math
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

# محاولة استيراد مدير الإعدادات
try:
    from brain.core.strategy_manager import StrategyConfigManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

@dataclass
class VoteReceipt:
    """إيصال التصويت النهائي (شهادة القرار)"""
    id: str
    timestamp: str
    final_verdict: str      # BUY / SELL / HOLD
    net_score: float        # -1.0 to 1.0
    confidence: float       # 0.0 to 1.0
    consensus_mode: str     # UNANIMOUS / MAJORITY / SPLIT
    veto_active: bool
    veto_reason: Optional[str]
    votes: Dict[str, float] # تفاصيل أصوات الوكلاء

class WeightedVoter:
    """
    محرك التصويت السيادي.
    يجمع الأصوات، يزنها، ويطبق الفيتو، ثم يصدر الحكم.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Voter")
        
        # الاتصال بمدير الإعدادات
        self.config_mgr = StrategyConfigManager() if CONFIG_AVAILABLE else None
        
        # الأوزان الافتراضية (Fallback)
        self.default_weights = {
            "quant": 1.0,
            "sentiment": 0.8,
            "hybrid": 1.5,
            "risk": 2.0  # المخاطر دائماً لها وزن مضاعف (أو فيتو)
        }

    def _get_active_weights(self) -> Dict[str, float]:
        """جلب الأوزان الحالية من ملف الإعدادات"""
        if not self.config_mgr:
            return self.default_weights
            
        profile = self.config_mgr.load_profile()
        modules = profile.get("modules", {})
        
        weights = {}
        for name, cfg in modules.items():
            if cfg.get("enabled", False):
                # تحويل الاسم من config (quant_analysis) إلى الاسم الداخلي (quant)
                short_name = name.split("_")[0] 
                weights[short_name] = cfg.get("weight", 1.0)
        
        # إضافة وزن المخاطر (ثابت أو من الإعدادات)
        weights["risk"] = 2.0 
        
        return weights

    def cast_vote(self, 
                  context_id: str,
                  quant_signal: Dict,
                  sentiment_signal: Dict,
                  hybrid_signal: Dict,
                  risk_signal: Dict,
                  market_volatility: float = 0.0) -> VoteReceipt:
        """
        جلسة التصويت الرئيسية.
        """
        weights = self._get_active_weights()
        
        # 1. التكيف مع التقلب (Volatility Adjustment)
        # في أوقات الخوف، نخفض وزن المشاعر ونرفع وزن المخاطر والتحليل الكمي
        if market_volatility > 0.05: # 5% volatility is high
            weights["sentiment"] *= 0.5
            weights["risk"] *= 1.5
            self.logger.info("⚠️ High Volatility Detected: Risk weight increased.")

        # 2. فحص الفيتو (The Veto)
        # إذا قال مدير المخاطر "لا"، ينتهي النقاش.
        if risk_signal.get("status") == "BLOCK":
            return self._generate_receipt(
                context_id, "HOLD", 0.0, 1.0, "VETOED", 
                veto=True, reason=f"Risk: {risk_signal.get('reason')}"
            )

        # 3. تجميع النقاط (Score Aggregation)
        total_score = 0.0
        total_weight = 0.0
        details = {}

        # -- Quant Vote --
        if "quant" in weights:
            s_val = self._normalize_signal(quant_signal.get("signal", "NEUTRAL"))
            w = weights["quant"]
            total_score += s_val * w
            total_weight += w
            details["quant"] = s_val

        # -- Sentiment Vote --
        if "sentiment" in weights:
            # Sentiment score is usually -1 to 1 directly
            s_val = float(sentiment_signal.get("score", 0.0))
            # تعديل حسب الثقة
            if sentiment_signal.get("sentiment") == "BEARISH": s_val = -abs(s_val)
            elif sentiment_signal.get("sentiment") == "BULLISH": s_val = abs(s_val)
            
            w = weights["sentiment"]
            total_score += s_val * w
            total_weight += w
            details["sentiment"] = s_val

        # -- Hybrid Vote (The Tie-Breaker) --
        if "hybrid" in weights:
            # Hybrid usually gives a decision text
            h_dec = hybrid_signal.get("final_verdict", "HOLD")
            s_val = self._normalize_signal(h_dec)
            # نأخذ الثقة في الحسبان
            conf = float(hybrid_signal.get("final_score", 0.5))
            
            w = weights["hybrid"]
            total_score += s_val * conf * w
            total_weight += w
            details["hybrid"] = s_val * conf

        # 4. الحساب النهائي
        final_net = total_score / total_weight if total_weight > 0 else 0.0
        
        # تحديد الحكم
        verdict = "HOLD"
        mode = "SPLIT"
        
        if final_net > 0.6: verdict = "BUY"
        elif final_net < -0.6: verdict = "SELL"
        
        # تحديد نمط الإجماع
        # إذا كان الجميع متفقين في الإشارة (كلهم موجب أو كلهم سالب)
        signals = [v for v in details.values() if v != 0]
        if all(s > 0 for s in signals) or all(s < 0 for s in signals):
            mode = "UNANIMOUS"
        elif abs(final_net) > 0.5:
            mode = "MAJORITY"

        return self._generate_receipt(
            context_id, verdict, final_net, abs(final_net), mode, 
            veto=False, reason=None, votes=details
        )

    def _normalize_signal(self, text_signal: str) -> float:
        """ترجمة الكلمات (-1 إلى 1)"""
        s = text_signal.upper()
        if "STRONG_BUY" in s: return 1.0
        if "BUY" in s: return 0.6
        if "STRONG_SELL" in s: return -1.0
        if "SELL" in s: return -0.6
        return 0.0

    def _generate_receipt(self, uid, verdict, score, conf, mode, veto, reason, votes=None):
        return VoteReceipt(
            id=f"VOTE-{uid[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            final_verdict=verdict,
            net_score=round(score, 4),
            confidence=round(conf, 2),
            consensus_mode=mode,
            veto_active=veto,
            veto_reason=reason,
            votes=votes or {}
        )

# =================================================================
# Forensic Verification
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    voter = WeightedVoter()
    
    print("[*] Voter Initialized.")
    
    # محاكاة إشارات
    mock_quant = {"signal": "BUY"}
    mock_sent = {"sentiment": "BEARISH", "score": 0.4} # تعارض!
    mock_hybrid = {"final_verdict": "WEAK_BUY", "final_score": 0.6}
    mock_risk = {"status": "OK"}
    
    print("\n[1] Casting Vote (Conflict Scenario)...")
    receipt = voter.cast_vote(
        "CTX-123", mock_quant, mock_sent, mock_hybrid, mock_risk
    )
    
    print(f"    Verdict: {receipt.final_verdict}")
    print(f"    Score:   {receipt.net_score}")
    print(f"    Mode:    {receipt.consensus_mode}")
    print(f"    Details: {receipt.votes}")
    
    # محاكاة فيتو
    print("\n[2] Casting Vote (Risk Veto)...")
    mock_risk_bad = {"status": "BLOCK", "reason": "High Leverage"}
    receipt_veto = voter.cast_vote(
        "CTX-456", mock_quant, mock_sent, mock_hybrid, mock_risk_bad
    )
    print(f"    Verdict: {receipt_veto.final_verdict}")
    print(f"    Reason:  {receipt_veto.veto_reason}")