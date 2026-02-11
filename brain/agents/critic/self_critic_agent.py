# Devil's Advocate

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - COGNITIVE BIAS DETECTOR & LOGIC CRITIC
# =================================================================
# Component Name: brain/agents/critic/self_critic_agent.py
# Core Responsibility: مراجعة "أسباب" دخول الصفقة للبحث عن عيوب منطقية أو انحيازات معرفية (Explainability Pillar).
# Design Pattern: Adversarial Agent / Heuristic Checker
# Forensic Impact: يمنع "التداول العاطفي" (حتى للذكاء الاصطناعي) ويجبر النظام على تبرير قراراته منطقياً.
# =================================================================

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class SelfCriticAgent:
    """
    الناقد الذاتي.
    يقوم بتحليل "مذكرة التبرير" (Rationale) المرفقة بكل صفقة مقترحة.
    يبحث عن التناقضات، الثقة المفرطة، أو تجاهل الإشارات المعاكسة.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Critic")
        
        # قائمة الانحيازات المعرفية التي نبحث عنها
        self.biases_definitions = {
            "CONFIRMATION_BIAS": "Ignoring contradictory macro signals.",
            "RECENCY_BIAS": "Over-weighting immediate price action vs trend.",
            "GAMBLER_FALLACY": "Assuming reversal just because price moved far.",
            "FOMO_INDICATOR": "Entering on high volatility without structural support."
        }

    def critique_proposal(self, proposal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        جلسة استجواب للصفقة المقترحة.
        
        Args:
            proposal: الصفقة المقترحة {symbol, side, reason, confidence, strategy_ref}
            market_context: السياق العام {macro_regime, volatility, daily_trend}
            
        Returns:
            تقرير النقد {approved: bool, score: float, critiques: List[str]}
        """
        critique_score = 100.0
        flags = []
        
        # 1. فحص انحياز التأكيد (Confirmation Bias)
        # هل تحاول الشراء بينما الاتجاه العام (Macro) هابط؟
        if not self._check_confluence(proposal, market_context):
            penalty = 20.0
            critique_score -= penalty
            flags.append(f"CONFIRMATION_BIAS: Fighting the {market_context.get('daily_trend')} trend (-{penalty})")

        # 2. فحص انحياز الحداثة (Recency Bias)
        # هل تعتمد فقط على شمعة الدقيقة وتتجاهل الساعة؟
        # (يتم استنتاجه من اسم الاستراتيجية أو الإطار الزمني)
        if self._detect_tunnel_vision(proposal):
            penalty = 15.0
            critique_score -= penalty
            flags.append(f"TUNNEL_VISION: Strategy {proposal.get('strategy_ref')} lacks multi-timeframe confirmation (-{penalty})")

        # 3. فحص "مغالطة المقامر" (Gambler's Fallacy)
        # هل السبب هو "السعر انخفض كثيراً ويجب أن يصعد"؟ (بدون إشارة انعكاس حقيقية)
        rationale_text = proposal.get("reason", {}).get("desc", "").lower()
        if "oversold" in rationale_text and "reversal" not in rationale_text:
            # الاعتماد على "التشبع البيعي" وحده خطأ قاتل في الترند القوي
            penalty = 25.0
            critique_score -= penalty
            flags.append(f"FALLACY_RISK: Catching a falling knife based solely on RSI (-{penalty})")

        # 4. فحص التناقض المنطقي (Logical Consistency)
        # هل الهدف (Take Profit) أصغر من المخاطرة (Stop Loss)؟
        tp_dist = abs(proposal.get("tp_price", 0) - proposal.get("entry_price", 0))
        sl_dist = abs(proposal.get("entry_price", 0) - proposal.get("sl_price", 0))
        
        if sl_dist > 0 and tp_dist > 0:
            rr_ratio = tp_dist / sl_dist
            if rr_ratio < 1.0: # المخاطرة أكبر من الربح
                penalty = 30.0
                critique_score -= penalty
                flags.append(f"BAD_MATH: Risk/Reward ratio ({rr_ratio:.2f}) is negative expectancy (-{penalty})")

        # 5. الحكم النهائي
        # نقبل الصفقة فقط إذا كان منطقها قوياً (Score > 70)
        is_approved = critique_score >= 70.0
        
        report = {
            "agent": "SelfCriticAgent",
            "timestamp": datetime.utcnow().isoformat(),
            "target_proposal": proposal.get("id", "UNKNOWN"),
            "critique_score": round(critique_score, 1),
            "verdict": "APPROVED" if is_approved else "REJECTED",
            "detected_flaws": flags,
            "forensic_note": f"Proposal scored {critique_score}/100. Logic check complete."
        }
        
        if not is_approved:
            self.logger.warning(f"CRITIC_VETO: Blocked trade on {proposal.get('symbol')}. Reasons: {flags}")

        return report

    def _check_confluence(self, proposal: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """هل تسبح الصفقة مع التيار أم ضده؟"""
        side = proposal.get("side") # LONG/SHORT
        trend = context.get("daily_trend", "NEUTRAL") # BULLISH/BEARISH
        
        # السماح بالتداول العكسي (Contrarian) فقط إذا كانت الاستراتيجية مصممة لذلك صراحة
        strategy_type = proposal.get("strategy_type", "TREND_FOLLOWING")
        
        if strategy_type == "MEAN_REVERSION":
            return True # الاستراتيجية تتوقع الانعكاس، فلا بأس من مخالفة الترند
            
        if side == "LONG" and trend == "BEARISH":
            return False
        if side == "SHORT" and trend == "BULLISH":
            return False
            
        return True

    def _detect_tunnel_vision(self, proposal: Dict[str, Any]) -> bool:
        """هل القرار مبني على بيانات ضيقة جداً؟"""
        # هذا يعتمد على البيانات الوصفية المرفقة بالصفقة
        timeframes = proposal.get("reason", {}).get("confirmed_timeframes", [])
        
        # إذا كانت القائمة تحتوي على إطار زمني واحد فقط وهو صغير (1m أو 5m)
        if len(timeframes) == 1 and timeframes[0] in ["1m", "5m"]:
            return True
            
        return False