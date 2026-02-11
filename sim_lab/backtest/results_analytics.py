# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVANCED PERFORMANCE ANALYTICS ENGINE
=================================================================
Component: sim_lab/backtest/results_analytics.py
Core Responsibility: تحليل النتائج إحصائياً لكشف جودة الاستراتيجية (Explainability Pillar).
Design Pattern: Statistical Analyzer
Forensic Impact: يكشف الاستراتيجيات "المنحوتة" (Overfitted). إذا كانت الأرقام "أجمل من الواقع"، سيضع علامة حمراء.
=================================================================
"""

import numpy as np
import pandas as pd
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.analytics")

@dataclass
class TradeRecord:
    timestamp: float
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    commission: float

@dataclass
class PerformanceReport:
    total_return_pct: float
    net_profit: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration_sec: float
    integrity_flag: str  # CLEAN, SUSPICIOUS, UNREALISTIC

class ResultsAnalytics:
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def generate_report(self, 
                       equity_curve: List[float], 
                       trades: List[TradeRecord],
                       initial_capital: float) -> PerformanceReport:
        """
        إنشاء تقرير شامل بناءً على منحنى حقوق الملكية (Equity Curve) وسجل الصفقات.
        """
        if not equity_curve or not trades:
            logger.warning("ANALYTICS: Insufficient data to generate report.")
            return self._empty_report()

        # تحويل القائمة إلى Pandas Series للمعالجة السريعة
        equity_series = pd.Series(equity_curve)
        
        # 1. حساب العوائد (Returns)
        returns = equity_series.pct_change().dropna()
        
        # 2. المقاييس الأساسية
        final_equity = equity_curve[-1]
        net_profit = final_equity - initial_capital
        total_return_pct = (net_profit / initial_capital) * 100

        # 3. Max Drawdown (أقصى انخفاض من القمة)
        # نحسب قمة تراكمية، ثم الانخفاض منها
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown_pct = drawdown.min() * 100  # قيمة سالبة

        # 4. نسب المخاطرة (Sharpe & Sortino)
        sharpe = self._calculate_sharpe(returns)
        sortino = self._calculate_sortino(returns)

        # 5. إحصائيات الصفقات
        win_trades = [t for t in trades if t.pnl > 0]
        loss_trades = [t for t in trades if t.pnl <= 0]
        
        win_rate = (len(win_trades) / len(trades)) * 100 if trades else 0
        
        gross_profit = sum(t.pnl for t in win_trades)
        gross_loss = abs(sum(t.pnl for t in loss_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

        # 6. الفحص الجنائي (Forensic Integrity Check)
        integrity = self._check_integrity(sharpe, max_drawdown_pct, win_rate)

        report = PerformanceReport(
            total_return_pct=round(total_return_pct, 2),
            net_profit=round(net_profit, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            total_trades=len(trades),
            avg_trade_duration_sec=0.0, # (يمكن حسابه إذا توفرت التواقيت)
            integrity_flag=integrity
        )

        self._log_summary(report)
        return report

    def _calculate_sharpe(self, returns: pd.Series) -> float:
        """
        حساب نسبة شارب (السنوية المفترضة).
        Sharpe = (Mean Return - Risk Free) / Std Dev
        """
        if returns.std() == 0: return 0.0
        # نفترض 252 يوم تداول، أو 365 للكريبتو. 
        # إذا كانت البيانات بالدقائق، يجب التعديل. هنا نفترض بيانات يومية للتبسيط.
        annualized_return = returns.mean() * 365
        annualized_vol = returns.std() * np.sqrt(365)
        
        return (annualized_return - self.risk_free_rate) / annualized_vol

    def _calculate_sortino(self, returns: pd.Series) -> float:
        """
        حساب نسبة سورتينو (تركز فقط على الانحراف المعياري السلبي).
        مهمة جداً للكريبتو لأن الصعود القوي (Volatility) يعتبر جيداً.
        """
        negative_returns = returns[returns < 0]
        if negative_returns.std() == 0: return 0.0
        
        annualized_return = returns.mean() * 365
        downside_deviation = negative_returns.std() * np.sqrt(365)
        
        return (annualized_return - self.risk_free_rate) / downside_deviation

    def _check_integrity(self, sharpe: float, mdd: float, win_rate: float) -> str:
        """
        كشف الاحتيال الذاتي (Overfitting Detection).
        """
        # إذا كان شارب > 4.0، غالباً هناك خطأ برمجي أو Look-ahead Bias (استخدام بيانات المستقبل)
        if sharpe > 4.0:
            return "UNREALISTIC (Sharpe > 4)"
        
        # استراتيجية تربح 95% من الوقت ولكن تخسر 50% في صفقة واحدة (Martingale)
        if win_rate > 90.0 and mdd < -40.0:
            return "DANGEROUS (Martingale Pattern)"
        
        # استراتيجية لا تخسر أبداً (مستحيل إحصائياً)
        if win_rate == 100.0:
            return "SUSPICIOUS (100% Win Rate)"

        return "CLEAN"

    def _empty_report(self):
        return PerformanceReport(0,0,0,0,0,0,0,0,0, "NO_DATA")

    def _log_summary(self, r: PerformanceReport):
        logger.info("--- BACKTEST PERFORMANCE REPORT ---")
        logger.info(f"Integrity:    [{r.integrity_flag}]")
        logger.info(f"Net Profit:   ${r.net_profit:,.2f} ({r.total_return_pct}%)")
        logger.info(f"Sharpe Ratio: {r.sharpe_ratio} | Sortino: {r.sortino_ratio}")
        logger.info(f"Max Drawdown: {r.max_drawdown_pct}%")
        logger.info(f"Win Rate:     {r.win_rate}% (Pf: {r.profit_factor})")
        logger.info("-----------------------------------")

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    analytics = ResultsAnalytics()
    
    # 1. محاكاة منحنى حقوق ملكية (Equity Curve)
    # يبدأ بـ 1000، يرتفع، يهبط قليلاً، ثم يرتفع
    equity = [1000, 1020, 1050, 1040, 1030, 1060, 1100, 1090, 1150, 1200]
    
    # 2. محاكاة صفقات
    trades = [
        TradeRecord(0, "BTC", "BUY", 50000, 51000, 0.1, 100, 1), # Win
        TradeRecord(0, "BTC", "BUY", 51000, 52500, 0.1, 150, 1), # Win
        TradeRecord(0, "BTC", "BUY", 52500, 52000, 0.1, -50, 1), # Loss
    ]
    
    report = analytics.generate_report(equity, trades, 1000.0)