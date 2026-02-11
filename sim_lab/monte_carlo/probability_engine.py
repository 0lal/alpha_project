# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - MONTE CARLO PROBABILITY ENGINE
=================================================================
Component: sim_lab/monte_carlo/probability_engine.py
Core Responsibility: تقييم احتمالي للقرارات عبر توليد آلاف السيناريوهات العشوائية (Decision Support Pillar).
Design Pattern: Monte Carlo Simulation (Vectorized)
Forensic Impact: يوفر "مبرراً رياضياً" لكل قرار. إذا خسر النظام، نعود هنا لنرى هل كانت الاحتمالات في صالحنا (Bad Luck) أم أننا خاطرنا بغباء (Bad Math).
=================================================================
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Tuple, List

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.monte_carlo")

@dataclass
class TradeSetup:
    """تفاصيل الصفقة المقترحة"""
    current_price: float
    stop_loss: float
    take_profit: float
    volatility_hourly: float  # الانحراف المعياري للساعة (من ATR)
    duration_hours: int       # المدى الزمني المتوقع للصفقة

@dataclass
class SimulationResult:
    """نتيجة التحليل الاحتمالي"""
    win_probability: float    # نسبة نجاح الصفقة (Hit TP before SL)
    loss_probability: float   # نسبة فشل الصفقة (Hit SL before TP)
    expected_value: float     # القيمة المتوقعة (EV) لكل دولار مخاطرة
    worst_case_scenario: float # أسوأ سيناريو (ضمن فترة الثقة 99%)
    recommendation: str       # GO / NO_GO

class ProbabilityEngine:
    def __init__(self, num_simulations: int = 10000):
        self.num_sims = num_simulations
        self.dt = 1.0 / 24.0  # الخطوة الزمنية (ساعة واحدة) - نفترض 24 ساعة تداول

    def evaluate_trade(self, setup: TradeSetup) -> SimulationResult:
        """
        تشغيل المحاكاة لتقييم صفقة معينة.
        """
        if setup.volatility_hourly <= 0:
            logger.error("MONTE_CARLO: Volatility must be positive.")
            return self._empty_result()

        # 1. توليد المسارات السعرية (Vectorized GBM)
        # نستخدم مصفوفات NumPy للسرعة بدلاً من الحلقات
        price_paths = self._generate_paths(setup)

        # 2. تحليل المسارات (هل ضربنا الهدف أم الوقف؟)
        wins, losses, time_outs = self._analyze_paths(price_paths, setup)

        # 3. حساب الإحصائيات
        win_prob = wins / self.num_sims
        loss_prob = losses / self.num_sims
        
        # حساب نسبة العائد للمخاطرة (R:R)
        potential_profit = abs(setup.take_profit - setup.current_price)
        potential_loss = abs(setup.current_price - setup.stop_loss)
        risk_reward_ratio = potential_profit / potential_loss if potential_loss > 0 else 0

        # معادلة القيمة المتوقعة: (Win% * Reward) - (Loss% * Risk)
        # هنا نحسبها كوحدات مخاطرة (R-Multiples)
        ev = (win_prob * risk_reward_ratio) - (loss_prob * 1.0)

        # 4. التوصية
        # نقبل الصفقة فقط إذا كانت الاحتمالات في صالحنا والقيمة المتوقعة إيجابية
        recommendation = "GO" if ev > 0.2 and win_prob > 0.4 else "NO_GO"

        # أسوأ سيناريو (99% VaR) في نهاية المدة (للصفقات التي انتهى وقتها دون ضرب وقف أو هدف)
        final_prices = price_paths[:, -1]
        worst_case = np.percentile(final_prices, 1)

        result = SimulationResult(
            win_probability=round(win_prob * 100, 2),
            loss_probability=round(loss_prob * 100, 2),
            expected_value=round(ev, 3),
            worst_case_scenario=round(worst_case, 2),
            recommendation=recommendation
        )
        
        self._log_analysis(setup, result)
        return result

    def _generate_paths(self, setup: TradeSetup) -> np.ndarray:
        """
        توليد مسارات باستخدام Geometric Brownian Motion (GBM).
        S_t = S_0 * exp((mu - 0.5*sigma^2)*t + sigma*W_t)
        """
        steps = setup.duration_hours
        
        # نفترض "Drift" صفري (mu=0) لنكون محافظين (Conservative).
        # لا نفترض أن السعر سيصعد، بل نترك الصدفة والتقلب يقرران.
        mu = 0.0
        sigma = setup.volatility_hourly

        # توليد صدمات عشوائية (Z-Scores) لجميع المسارات والخطوات دفعة واحدة
        # Shape: (10000, steps)
        random_shocks = np.random.normal(0, 1, (self.num_sims, steps))
        
        # تراكم الصدمات (Brownian Motion)
        brownian_motion = np.cumsum(random_shocks * np.sqrt(self.dt), axis=1)
        
        # حساب عامل الوقت (Drift Term)
        time_grid = np.linspace(self.dt, steps * self.dt, steps)
        drift_term = (mu - 0.5 * sigma**2) * time_grid
        
        # تطبيق المعادلة الأسية
        # Broadcasting drift_term across all simulations
        log_returns = drift_term + (sigma * brownian_motion)
        
        # تحويل العوائد اللوغاريتمية إلى أسعار
        price_paths = setup.current_price * np.exp(log_returns)
        
        return price_paths

    def _analyze_paths(self, paths: np.ndarray, setup: TradeSetup) -> Tuple[int, int, int]:
        """
        فحص كل مسار لمعرفة مصيره (Win/Loss/TimeOut).
        """
        # نستخدم منطق المصفوفات للسرعة العالية
        # True إذا وصل السعر للهدف في أي نقطة
        hit_tp = np.any(paths >= setup.take_profit, axis=1)
        
        # True إذا وصل السعر للوقف في أي نقطة
        hit_sl = np.any(paths <= setup.stop_loss, axis=1)
        
        # المعضلة: ماذا لو ضرب الهدف والوقف في نفس المسار؟
        # يجب أن نعرف "أيهما حدث أولاً".
        
        # العثور على مؤشر (index) أول مرة تحقق فيها الشرط
        # argmax يعيد 0 إذا لم يتحقق الشرط، لذا نحتاج لمعالجة ذلك
        tp_indices = np.argmax(paths >= setup.take_profit, axis=1)
        sl_indices = np.argmax(paths <= setup.stop_loss, axis=1)
        
        # تصحيح المؤشرات للحالات التي لم يتحقق فيها الشرط (نجعلها infinity)
        steps = paths.shape[1]
        tp_indices = np.where(hit_tp, tp_indices, steps + 1)
        sl_indices = np.where(hit_sl, sl_indices, steps + 1)
        
        # الفائزون: ضربوا الهدف، ولم يضربوا الوقف، أو ضربوا الهدف قبل الوقف
        wins = np.sum((tp_indices < sl_indices) & (tp_indices <= steps))
        
        # الخاسرون: ضربوا الوقف قبل الهدف
        losses = np.sum((sl_indices < tp_indices) & (sl_indices <= steps))
        
        # انتهى الوقت: لم يضربوا أياً منهما
        time_outs = self.num_sims - wins - losses
        
        return wins, losses, time_outs

    def _empty_result(self):
        return SimulationResult(0, 0, 0, 0, "ERROR")

    def _log_analysis(self, setup: TradeSetup, res: SimulationResult):
        logger.info(f"MONTE_CARLO: Evaluated {setup.current_price} -> TP:{setup.take_profit}/SL:{setup.stop_loss}")
        logger.info(f"             Sims: {self.num_sims} | Win: {res.win_probability}% | EV: {res.expected_value}")
        logger.info(f"             Verdict: [{res.recommendation}]")

# =================================================================
# اختبار المحاكاة (Unit Test)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = ProbabilityEngine(num_simulations=10000)
    
    # سيناريو 1: صفقة منطقية (Trend Following)
    # السعر 100، الهدف 105 (5%)، الوقف 98 (2%)، تقلب منخفض
    setup_good = TradeSetup(
        current_price=100.0,
        stop_loss=98.0,
        take_profit=105.0,
        volatility_hourly=0.005, # 0.5% per hour
        duration_hours=24
    )
    
    print("--- Scenario 1: High Prob Setup ---")
    engine.evaluate_trade(setup_good)
    
    # سيناريو 2: صفقة انتحارية (High Risk)
    # السعر 100، الهدف 120 (20%!)، الوقف 99 (1%)، تقلب عالي
    # الاحتمال أن يضرب الوقف قبل الهدف شبه مؤكد بسبب التذبذب
    setup_bad = TradeSetup(
        current_price=100.0,
        stop_loss=99.0,
        take_profit=120.0,
        volatility_hourly=0.02, # 2% per hour
        duration_hours=48
    )
    
    print("\n--- Scenario 2: Suicide Setup ---")
    engine.evaluate_trade(setup_bad)