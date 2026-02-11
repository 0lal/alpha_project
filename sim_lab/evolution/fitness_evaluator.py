# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - STRATEGY FITNESS EVALUATOR
=================================================================
Component: sim_lab/evolution/fitness_evaluator.py
Core Responsibility: ترجمة الأداء المعقد إلى درجة لياقة واحدة (Adaptability Pillar).
Design Pattern: Weighted Scoring Model
Forensic Impact: يمنع "خداع" النظام. الاستراتيجيات التي تعتمد على الحظ (عدد صفقات قليل) أو المخاطرة العالية يتم معاقبتها بشدة في النتيجة النهائية.
=================================================================
"""

import logging
import numpy as np
from dataclasses import dataclass
from sim_lab.backtest.results_analytics import PerformanceReport

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.evolution.fitness")

@dataclass
class FitnessWeights:
    """أوزان عوامل التقييم (يجب أن يكون المجموع تقريباً منطقياً للتوازن)"""
    sharpe: float = 2.0         # التركيز على العائد المعدل للمخاطرة
    sortino: float = 1.5        # تفضيل الصعود النظيف
    total_return: float = 1.0   # الربح الخام مهم، لكن ليس الأهم
    win_rate: float = 0.5       # معدل الفوز
    
    # عقوبات
    drawdown_penalty: float = 5.0  # عقوبة قاسية لكل 1% انخفاض
    min_trades_threshold: int = 50 # الحد الأدنى للصفقات لاعتبار النتيجة موثوقة

class FitnessEvaluator:
    def __init__(self, weights: FitnessWeights = None):
        self.weights = weights if weights else FitnessWeights()

    def calculate_fitness(self, report: PerformanceReport) -> float:
        """
        حساب درجة اللياقة (Fitness Score).
        كلما زادت الدرجة، زادت فرصة الاستراتيجية في البقاء.
        """
        # 1. الفحص الجنائي السريع (Disqualifiers)
        # إذا كانت الاستراتيجية مفلسة أو لم تتداول، لياقتها صفر
        if report.net_profit <= 0 or report.total_trades == 0:
            return 0.0

        # 2. حساب النقاط الإيجابية (Rewards)
        score = 0.0
        
        # أ) نسبة شارب (القلب النابض للياقة)
        # نستخدم sigmoid لتقييد القيم المتطرفة (Cap extreme values)
        # شارب 3.0 ممتاز، شارب 10.0 مشبوه ولكنه جيد رياضياً
        score += report.sharpe_ratio * self.weights.sharpe
        
        # ب) نسبة سورتينو
        score += report.sortino_ratio * self.weights.sortino
        
        # ج) العائد الكلي (Logarithmic)
        # نستخدم اللوغاريتم لأن الفرق بين 10% و 20% أهم من الفرق بين 1000% و 1010%
        if report.total_return_pct > 0:
            score += np.log1p(report.total_return_pct) * self.weights.total_return

        # 3. تطبيق العقوبات (Penalties)
        
        # أ) عقوبة الانخفاض (Max Drawdown Punishment)
        # Drawdown هو رقم سالب (مثلاً -15.0).
        # المعادلة: كلما زاد الانخفاض، خصمنا نقاطاً بشكل أسي (Exponential)
        dd_penalty = abs(report.max_drawdown_pct) * self.weights.drawdown_penalty
        
        # إذا تجاوز الانخفاض 25%، نضاعف العقوبة (Kill Zone)
        if report.max_drawdown_pct < -25.0:
            dd_penalty *= 2.0
            
        score -= dd_penalty

        # ب) عقوبة قلة البيانات (Statistical Insignificance)
        # استراتيجية قامت بـ 5 صفقات وربحت لا يمكن الوثوق بها مثل واحدة قامت بـ 100 صفقة
        if report.total_trades < self.weights.min_trades_threshold:
            # عامل تخفيض: 5 صفقات من أصل 50 = 0.1 (تخفيض 90% من السكور)
            significance_factor = report.total_trades / self.weights.min_trades_threshold
            score *= significance_factor
            logger.debug(f"FITNESS: Penalized for low trade count ({report.total_trades}). Factor: {significance_factor:.2f}")

        # 4. التنعيم النهائي (Normalization)
        # نضمن أن النتيجة لا تقل عن صفر
        final_score = max(0.0, score)
        
        return final_score

    def explain_score(self, report: PerformanceReport) -> str:
        """تفسير بشري لسبب النتيجة (للـ Dashboard)"""
        raw_score = self.calculate_fitness(report)
        explanation = []
        
        if report.net_profit <= 0:
            return "Zero Fitness: Strategy lost money."
            
        explanation.append(f"Base Score: {raw_score:.2f}")
        
        if report.sharpe_ratio > 2.0:
            explanation.append("High Sharpe Bonus (+)")
        
        if abs(report.max_drawdown_pct) > 20.0:
            explanation.append("Heavy Drawdown Penalty (-)")
            
        if report.total_trades < self.weights.min_trades_threshold:
            explanation.append("Low Sample Size Penalty (-)")
            
        return " | ".join(explanation)

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    evaluator = FitnessEvaluator()
    
    # الحالة 1: استراتيجية قوية ومستقرة (Alpha Candidate)
    report_alpha = PerformanceReport(
        total_return_pct=50.0, net_profit=5000,
        sharpe_ratio=3.5, sortino_ratio=4.2,
        max_drawdown_pct=-8.0, win_rate=65.0, profit_factor=2.5,
        total_trades=150, avg_trade_duration_sec=3600, integrity_flag="CLEAN"
    )
    
    # الحالة 2: استراتيجية مقامرة (Gambler) - ربح عالٍ ولكن مخاطرة كارثية
    report_gambler = PerformanceReport(
        total_return_pct=150.0, net_profit=15000,
        sharpe_ratio=1.2, sortino_ratio=1.5,
        max_drawdown_pct=-45.0, win_rate=40.0, profit_factor=1.1,
        total_trades=200, avg_trade_duration_sec=3600, integrity_flag="CLEAN"
    )

    # الحالة 3: استراتيجية محظوظة (Lucky) - صفقات قليلة جداً
    report_lucky = PerformanceReport(
        total_return_pct=20.0, net_profit=2000,
        sharpe_ratio=4.0, sortino_ratio=5.0, # أرقام ممتازة نظرياً
        max_drawdown_pct=-2.0, win_rate=100.0, profit_factor=99.0,
        total_trades=5, # لكن 5 صفقات فقط!
        avg_trade_duration_sec=3600, integrity_flag="SUSPICIOUS"
    )

    print(f"Alpha Score:   {evaluator.calculate_fitness(report_alpha):.2f} [{evaluator.explain_score(report_alpha)}]")
    print(f"Gambler Score: {evaluator.calculate_fitness(report_gambler):.2f} [{evaluator.explain_score(report_gambler)}]")
    print(f"Lucky Score:   {evaluator.calculate_fitness(report_lucky):.2f}   [{evaluator.explain_score(report_lucky)}]")
    
    # النتيجة المتوقعة: Alpha يجب أن تفوز رغم أن Gambler ربحت أموالاً أكثر.
    # Lucky يجب أن تعاقب بشدة لأنها لم تثبت جدارتها إحصائياً.