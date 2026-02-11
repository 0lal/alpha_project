# Consensus Auditor

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - SWARM CONSENSUS & LOGIC VERIFIER
# =================================================================
# Component Name: brain/agents/critic/logic_verifier.py
# Core Responsibility: التأكد من عدم وجود تعارضات جوهرية بين الوكلاء (إجماع السرب) (Governance Pillar).
# Design Pattern: Mediator / Consensus Oracle
# Forensic Impact: يوثق "درجة التوافق" (Consensus Score). يفسر لماذا تم رفض صفقة رغم وجود إشارة شراء فنية (بسبب الفيتو الاقتصادي).
# =================================================================

import logging
import numpy as np
from typing import Dict, List, Any, Tuple

class LogicVerifier:
    """
    مدقق المنطق (حكم الساحة).
    يجمع مخرجات جميع الوكلاء ويتحقق من اتساقها (Consistency Check).
    يفرض الهرمية: الاقتصاد الكلي (Strategic) يغلب التحليل الفني (Tactical).
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Critic.Verifier")
        
        # أوزان الثقة لكل وكيل (Hierarchy of Truth)
        # الوكيل الاقتصادي هو "الجنرال"، والتقني هو "الجندي".
        self.agent_weights = {
            "EconomyAnalyst": 0.30,      # الأعلى وزناً (الاتجاه العام)
            "OrderFlowAgent": 0.25,      # الحقيقة اللحظية (السيولة لا تكذب)
            "SentimentProcessor": 0.15,  # النية السوقية
            "IndicatorsAgent": 0.15,     # التحليل الفني (يمكن أن يخطئ)
            "SocialAgent": 0.10,         # ضجيج عالٍ (وزن منخفض)
            "GeopoliticalAnalyst": 0.05  # تأثيره نادر ولكنه قوي (يتم التعامل معه كـ Override)
        }

        # عتبة الإجماع المطلوبة للموافقة
        self.consensus_threshold = 0.60 # نحتاج توافق 60% على الأقل

    def verify_swarm_consensus(self, agents_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        التحقق من إجماع السرب.
        
        Args:
            agents_outputs: قاموس يحتوي على مخرجات الوكلاء.
            Example: {
                "EconomyAnalyst": {"sentiment": "BEARISH", "score": -0.8},
                "IndicatorsAgent": {"sentiment": "BULLISH", "score": 0.7},
                ...
            }
            
        Returns:
            تقرير الإجماع {verified: bool, consensus_score: float, conflicts: List[str]}
        """
        normalized_signals = self._normalize_signals(agents_outputs)
        
        # 1. البحث عن التعارضات القاتلة (Fatal Conflicts)
        # تعارض بين "الجنرال" (Economy) و "الجندي" (Indicators)
        critical_conflicts = self._detect_critical_conflicts(normalized_signals)
        
        if critical_conflicts:
            self.logger.warning(f"CONSENSUS_FAIL: تعارض جوهري تم اكتشافه: {critical_conflicts}")
            return {
                "verified": False,
                "consensus_score": 0.0,
                "status": "DISSONANCE",
                "conflicts": critical_conflicts,
                "reason": "Strategic/Tactical Mismatch"
            }

        # 2. حساب درجة الإجماع الموزون (Weighted Consensus Score)
        weighted_score = 0.0
        total_weight = 0.0
        
        for agent_name, signal in normalized_signals.items():
            weight = self.agent_weights.get(agent_name, 0.1)
            
            # Signal is between -1.0 (Bearish) and 1.0 (Bullish)
            weighted_score += signal * weight
            total_weight += weight
            
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # 3. اتخاذ القرار
        # هل القوة المرجحة كافية لتجاوز التردد؟
        # نستخدم القيمة المطلقة لأننا نهتم بـ "قوة القناعة" سواء بيعاً أو شراءً
        conviction = abs(final_score)
        is_verified = conviction >= self.consensus_threshold

        return {
            "verified": is_verified,
            "consensus_score": round(final_score, 4), # -1 to 1
            "conviction": round(conviction, 4),       # 0 to 1
            "status": "CONSENSUS_REACHED" if is_verified else "WEAK_CONSENSUS",
            "conflicts": [],
            "contributing_agents": list(normalized_signals.keys())
        }

    def _normalize_signals(self, outputs: Dict[str, Any]) -> Dict[str, float]:
        """
        توحيد لغة الوكلاء إلى أرقام (-1.0 إلى 1.0).
        """
        signals = {}
        for agent, data in outputs.items():
            score = 0.0
            
            # محاولة استخراج النتيجة الرقمية أو النصية
            if "score" in data:
                score = float(data["score"])
            elif "sentiment" in data:
                sent = data["sentiment"]
                if sent in ["BULLISH", "STRONG_BUY"]: score = 0.8
                elif sent in ["BEARISH", "STRONG_SELL"]: score = -0.8
                elif sent == "NEUTRAL": score = 0.0
            
            # تصحيح الحدود
            score = max(-1.0, min(1.0, score))
            signals[agent] = score
            
        return signals

    def _detect_critical_conflicts(self, signals: Dict[str, float]) -> List[str]:
        """
        كشف التعارضات التي لا يمكن التسامح معها.
        """
        conflicts = []
        
        # A. تعارض الاقتصاد مع الفني (Macro vs Technical)
        # إذا الاقتصاد يقول ركود (-0.8) والفني يقول شراء قوي (+0.8) -> كارثة محتملة
        macro = signals.get("EconomyAnalyst", 0.0)
        tech = signals.get("IndicatorsAgent", 0.0)
        
        if (macro < -0.5 and tech > 0.5) or (macro > 0.5 and tech < -0.5):
            conflicts.append(f"MACRO_TECH_CONFLICT: Economy({macro}) vs Tech({tech})")

        # B. تعارض السيولة مع السعر (OrderFlow vs Price Action)
        # إذا كان السعر يصعد (Indicators +) لكن الحيتان يبيعون (OrderFlow -) -> مصيدة ثيران
        flow = signals.get("OrderFlowAgent", 0.0)
        
        if (tech > 0.6 and flow < -0.4):
            conflicts.append(f"DIVERGENCE_WARNING: Price rising but Flow is negative (Trap Risk)")

        return conflicts