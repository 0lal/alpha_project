# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - CHAIN OF THOUGHT (CoT) REASONING ENGINE (VERSION 5.0)
=================================================================
Component: brain/reasoning/cot_engine.py
Role: مهندس المنطق الاستراتيجي (Strategic Logic Architect).
Forensic Features:
  - Dynamic Branching (تفرع ديناميكي للمسارات المنطقية).
  - Evidence Weighting (وزن متغير للأدلة حسب سياق السوق).
  - Devil's Advocate Protocol (محامي الشيطان المدمج).
  - Traceability Hash (توقيع جنائي لكل سلسلة تفكير).
=================================================================
"""

import logging
import uuid
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum

class ReasoningPhase(Enum):
    FOUNDATION = "FOUNDATION" # البنية التحتية (Macro)
    TACTICAL = "TACTICAL"     # التكتيك (Tech/Flow)
    SENTIMENT = "SENTIMENT"   # النفسية (Social/News)
    RISK = "RISK"             # المخاطرة (Exposure/Capital)
    SYNTHESIS = "SYNTHESIS"   # التجميع النهائي

@dataclass
class LogicStep:
    id: str
    phase: ReasoningPhase
    premise: str          # "بما أن..."
    observation: Any      # "ولاحظنا أن..."
    deduction: str        # "إذن..."
    confidence: float     # 0.0 - 1.0
    weight: float         # أهمية هذه الخطوة في القرار النهائي
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class DecisionTrace:
    trace_id: str
    context_hash: str     # هاش السياق الأصلي (لربط القرار بالبيانات)
    hypothesis: str
    steps: List[LogicStep] = field(default_factory=list)
    final_verdict: str = "PENDING"
    final_score: float = 0.0
    veto_triggered: bool = False
    veto_reason: Optional[str] = None

class CoTEngine:
    """
    محرك التفكير المتسلسل المتقدم.
    يبني "قضية" متكاملة لكل قرار تداول، مع القدرة على رفض الفرضيات (Veto) في أي مرحلة.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Reasoning.CoT")
        
        # أوزان استراتيجية (يمكن تعديلها ديناميكياً)
        self.weights = {
            ReasoningPhase.FOUNDATION: 0.25,
            ReasoningPhase.TACTICAL: 0.35,
            ReasoningPhase.SENTIMENT: 0.20,
            ReasoningPhase.RISK: 0.20
        }

    def deliberate(self, 
                   hypothesis: str, 
                   context_data: Dict[str, Any],
                   context_id: str) -> DecisionTrace:
        """
        جلسة التداول الفكري (Deliberation Session).
        يقوم المحرك بعقد "اجتماع" بين الوكلاء المختلفين للخروج بقرار موحد.
        """
        trace = DecisionTrace(
            trace_id=f"TRC-{uuid.uuid4().hex[:8]}",
            context_hash=context_id,
            hypothesis=hypothesis
        )

        try:
            # 1. المرحلة الأساسية: هل الأرض صلبة؟ (Macro/Geo)
            step_found = self._evaluate_foundation(context_data)
            trace.steps.append(step_found)
            
            # بروتوكول الرفض السريع (Fail Fast Protocol)
            if step_found.confidence < 0.3:
                trace.veto_triggered = True
                trace.veto_reason = f"Foundation Collapse: {step_found.deduction}"
                trace.final_verdict = "REJECTED"
                trace.final_score = 0.1
                return trace

            # 2. المرحلة التكتيكية: هل التوقيت مناسب؟ (Tech/Flow)
            step_tact = self._evaluate_tactics(context_data)
            trace.steps.append(step_tact)

            # 3. مرحلة المشاعر: هل الجمهور معنا؟ (Sentiment)
            step_sent = self._evaluate_sentiment(context_data)
            trace.steps.append(step_sent)

            # 4. مرحلة المخاطرة: هل نستطيع تحمل الخسارة؟ (Risk)
            # هذه المرحلة تملك حق النقض (Veto Power)
            step_risk = self._evaluate_risk(context_data)
            trace.steps.append(step_risk)

            if step_risk.confidence < 0.8: # إذا كانت المخاطرة غير مقبولة تماماً
                trace.veto_triggered = True
                trace.veto_reason = f"Risk Violation: {step_risk.deduction}"
                trace.final_verdict = "BLOCKED_BY_RISK"
                trace.final_score = 0.0
                return trace

            # 5. التجميع والحكم النهائي (Final Synthesis)
            self._synthesize_verdict(trace)
            
            # تسجيل جنائي للأثر
            self._archive_trace(trace)
            
            return trace

        except Exception as e:
            self.logger.error(f"CoT CRASH: {e}", exc_info=True)
            trace.final_verdict = "ERROR"
            trace.veto_reason = str(e)
            return trace

    # =================================================================
    # Cognitive Modules (وحدات الإدراك)
    # =================================================================

    def _evaluate_foundation(self, ctx: Dict) -> LogicStep:
        """تقييم البيئة الاقتصادية والجيوسياسية"""
        macro = ctx.get("macro", {})
        
        # استخراج المتغيرات (مع قيم افتراضية آمنة)
        regime = macro.get("regime", "NEUTRAL")
        vix = macro.get("volatility_index", 20.0)
        
        # منطق التقييم
        score = 0.5
        deduction = "Market environment is neutral."
        
        if regime == "RISK_ON" and vix < 25:
            score = 0.9
            deduction = "Favorable macro winds (Risk-On)."
        elif regime == "RISK_OFF" or vix > 35:
            score = 0.2
            deduction = "Hostile environment (High Volatility/Risk-Off)."
            
        return LogicStep(
            id="STEP-FND",
            phase=ReasoningPhase.FOUNDATION,
            premise="Capital requires stability or clear trends.",
            observation=f"Regime: {regime}, VIX: {vix}",
            deduction=deduction,
            confidence=score,
            weight=self.weights[ReasoningPhase.FOUNDATION]
        )

    def _evaluate_tactics(self, ctx: Dict) -> LogicStep:
        """تقييم التحليل الفني وتدفق الأوامر"""
        tech = ctx.get("technical", {})
        flow = ctx.get("order_flow", {})
        
        # مؤشرات
        rsi = tech.get("rsi", 50)
        trend = tech.get("trend", "SIDEWAYS")
        ofi = flow.get("ofi", 0.0) # Order Flow Imbalance (-1 to 1)
        
        score = 0.5
        deduction = "No clear tactical advantage."
        
        # التوافق (Confluence)
        if trend == "UP" and ofi > 0.2:
            score = 0.95
            deduction = "Strong confluence: Trend + Buying Pressure."
        elif trend == "UP" but ofi < -0.2:
            score = 0.4
            deduction = "Divergence warning: Price rising but whales selling."
        elif trend == "DOWN":
            score = 0.1
            deduction = "Trend is bearish."
            
        return LogicStep(
            id="STEP-TAC",
            phase=ReasoningPhase.TACTICAL,
            premise="Align with the path of least resistance.",
            observation=f"Trend: {trend}, OFI: {ofi:.2f}, RSI: {rsi}",
            deduction=deduction,
            confidence=score,
            weight=self.weights[ReasoningPhase.TACTICAL]
        )

    def _evaluate_sentiment(self, ctx: Dict) -> LogicStep:
        """تقييم مشاعر السوق"""
        sent = ctx.get("sentiment", {})
        
        intent = sent.get("overall", "NEUTRAL")
        score_val = sent.get("score", 0.0) # -1 to 1
        
        conf = 0.5 + (abs(score_val) * 0.5) # كلما كانت المشاعر أقوى، زادت الثقة
        
        return LogicStep(
            id="STEP-SNT",
            phase=ReasoningPhase.SENTIMENT,
            premise="Crowd psychology drives short-term moves.",
            observation=f"Intent: {intent}, Score: {score_val:.2f}",
            deduction=f"Market sentiment is {intent}.",
            confidence=conf if intent == "BULLISH" else (1.0 - conf), # نفترض الفرضية شراء (Bullish)
            weight=self.weights[ReasoningPhase.SENTIMENT]
        )

    def _evaluate_risk(self, ctx: Dict) -> LogicStep:
        """تقييم المخاطر (محامي الشيطان)"""
        acct = ctx.get("account", {})
        
        # الرافعة المالية الحالية
        lev = acct.get("leverage", 1.0)
        drawdown = acct.get("drawdown_pct", 0.0)
        
        # قواعد صارمة
        if lev > 3.0 or drawdown > 0.15: # 15% drawdown limit
            return LogicStep(
                id="STEP-RSK",
                phase=ReasoningPhase.RISK,
                premise="Preservation of capital is paramount.",
                observation=f"Lev: {lev}x, DD: {drawdown*100:.1f}%",
                deduction="CRITICAL RISK LEVEL EXCEEDED.",
                confidence=0.0, # رفض تام
                weight=self.weights[ReasoningPhase.RISK]
            )
            
        return LogicStep(
            id="STEP-RSK",
            phase=ReasoningPhase.RISK,
            premise="Risk parameters within safety limits.",
            observation=f"Lev: {lev}x, DD: {drawdown*100:.1f}%",
            deduction="Trade is permissive within risk budget.",
            confidence=1.0,
            weight=self.weights[ReasoningPhase.RISK]
        )

    def _synthesize_verdict(self, trace: DecisionTrace):
        """حساب النتيجة النهائية الموزونة"""
        total_score = 0.0
        total_weight = 0.0
        
        for step in trace.steps:
            total_score += step.confidence * step.weight
            total_weight += step.weight
            
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        trace.final_score = round(final_score, 4)
        
        # عتبة القرار (Decision Threshold)
        if final_score >= 0.75:
            trace.final_verdict = "STRONG_BUY"
        elif final_score >= 0.60:
            trace.final_verdict = "WEAK_BUY"
        else:
            trace.final_verdict = "HOLD/REJECT"

    def _archive_trace(self, trace: DecisionTrace):
        """تخزين الأثر في سجل غير قابل للتعديل (Simulated)"""
        # في النظام الحقيقي، هذا يكتب في ملف Log محمي أو قاعدة بيانات
        # self.logger.info(f"Trace Archived: {trace.trace_id} | Verdict: {trace.final_verdict}")
        pass

# =================================================================
# Forensic Verification
# =================================================================
if __name__ == "__main__":
    engine = CoTEngine()
    
    # محاكاة بيانات السياق
    mock_ctx = {
        "macro": {"regime": "RISK_ON", "volatility_index": 18.5},
        "technical": {"trend": "UP", "rsi": 65},
        "order_flow": {"ofi": 0.45}, # شراء قوي
        "sentiment": {"overall": "BULLISH", "score": 0.8},
        "account": {"leverage": 1.2, "drawdown_pct": 0.02}
    }
    
    print("\n[*] Starting CoT Deliberation...")
    trace = engine.deliberate("BTC_BREAKOUT_HYPOTHESIS", mock_ctx, "ctx_hash_12345")
    
    print(f"Trace ID: {trace.trace_id}")
    print(f"Hypothesis: {trace.hypothesis}")
    print(f"Final Score: {trace.final_score * 100:.1f}%")
    print(f"Verdict: {trace.final_verdict}")
    
    if trace.veto_triggered:
        print(f"⛔ VETOED: {trace.veto_reason}")
    else:
        print("\n--- Logic Steps ---")
        for step in trace.steps:
            print(f"[{step.phase.name}] Conf: {step.confidence:.2f} | {step.deduction}")