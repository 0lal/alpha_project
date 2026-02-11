# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - MONTE CARLO PATH VISUALIZER
=================================================================
Component: sim_lab/monte_carlo/path_visualizer.py
Core Responsibility: تحويل بيانات المحاكاة الإحصائية إلى رسوم بيانية بديهية (Explainability Pillar).
Design Pattern: View Helper / Plotter
Forensic Impact: يوفر "شهادة بصرية" للمخاطر المحتملة. يمكن استخدامه لاحقاً لمقارنة "ما توقعناه" بـ "ما حدث فعلاً".
=================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import logging
from typing import List, Optional
import os

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.visualizer")

class PathVisualizer:
    def __init__(self, output_dir: str = "logs/sim_plots"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

    def visualize_equity_curves(self, 
                              paths: np.ndarray, 
                              initial_equity: float,
                              title: str = "Monte Carlo Simulation - Equity Paths",
                              filename: str = "mc_equity_paths.png"):
        """
        رسم مسارات حقوق الملكية.
        paths: مصفوفة ثنائية الأبعاد [عدد المحاكات، عدد الخطوات الزمنية]
        """
        if paths.size == 0:
            logger.warning("VISUALIZER: No data to plot.")
            return

        num_sims, num_steps = paths.shape
        logger.info(f"VISUALIZER: Plotting {num_sims} paths over {num_steps} steps...")

        # إعداد اللوحة
        plt.figure(figsize=(12, 7))
        
        # 1. رسم عينة من المسارات الفردية (شفافة)
        # لا نرسم كل المسارات إذا كانت كثيرة جداً لتجنب تجميد الصورة
        sample_size = min(num_sims, 500) 
        indices = np.random.choice(num_sims, sample_size, replace=False)
        
        # نضرب العوائد التراكمية في رأس المال الأولي
        # نفترض أن المدخلات هي Equity Curves جاهزة أو عوائد تراكمية
        # للتبسيط، سنفترض أن paths تحتوي على قيم Equity مباشرة
        
        for i in indices:
            plt.plot(paths[i], color='gray', alpha=0.1, linewidth=0.5)

        # 2. حساب الإحصائيات (الحدود)
        mean_path = np.mean(paths, axis=0)
        p05_path = np.percentile(paths, 5, axis=0)  # أسوأ 5% (تشاؤمي)
        p50_path = np.percentile(paths, 50, axis=0) # الوسيط
        p95_path = np.percentile(paths, 95, axis=0) # أفضل 5% (تفاؤلي)

        # 3. رسم الخطوط الإحصائية
        x_axis = range(num_steps)
        plt.plot(x_axis, mean_path, color='blue', linewidth=2, label='Mean Expectation')
        plt.plot(x_axis, p50_path, color='green', linestyle='--', linewidth=1.5, label='Median')
        
        plt.plot(x_axis, p05_path, color='red', linestyle='--', linewidth=2, label='5th Percentile (Risk Floor)')
        plt.plot(x_axis, p95_path, color='purple', linestyle='--', linewidth=2, label='95th Percentile')

        # تظليل منطقة الثقة (بين 5% و 95%)
        plt.fill_between(x_axis, p05_path, p95_path, color='blue', alpha=0.05)

        # 4. التنسيق والتسميات
        plt.title(title, fontsize=14)
        plt.xlabel("Time Steps (Trades/Days)", fontsize=12)
        plt.ylabel("Equity ($)", fontsize=12)
        plt.axhline(y=initial_equity, color='black', linestyle=':', label='Initial Capital')
        
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.3)

        # 5. الحفظ
        full_path = os.path.join(self.output_dir, filename)
        try:
            plt.savefig(full_path, dpi=150)
            plt.close() # تحرير الذاكرة
            logger.info(f"VISUALIZER: Plot saved to {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"VISUALIZER_ERR: Failed to save plot: {e}")
            return None

    def visualize_final_distribution(self, 
                                   final_values: np.ndarray, 
                                   initial_equity: float,
                                   filename: str = "mc_distribution.png"):
        """
        رسم المدرج التكراري (Histogram) للنتائج النهائية.
        هذا يوضح احتمال الربح والخسارة.
        """
        plt.figure(figsize=(10, 6))
        
        # رسم الهيستوجرام
        n, bins, patches = plt.hist(final_values, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        
        # تلوين الخسارة باللون الأحمر والربح باللون الأخضر
        for i in range(len(patches)):
            if bins[i] < initial_equity:
                patches[i].set_facecolor('salmon')
            else:
                patches[i].set_facecolor('lightgreen')

        # خط رأس المال الأولي
        plt.axvline(initial_equity, color='black', linestyle='dashed', linewidth=2, label='Break-even')
        
        # خط القيمة المعرضة للخطر (VaR 95%)
        var_95 = np.percentile(final_values, 5)
        plt.axvline(var_95, color='red', linestyle='solid', linewidth=2, label=f'VaR 95% (${var_95:,.0f})')

        plt.title("Distribution of Final Equity Outcomes", fontsize=14)
        plt.xlabel("Final Equity ($)", fontsize=12)
        plt.ylabel("Frequency (Likelihood)", fontsize=12)
        plt.legend()
        plt.grid(axis='y', alpha=0.3)

        full_path = os.path.join(self.output_dir, filename)
        plt.savefig(full_path, dpi=150)
        plt.close()
        logger.info(f"VISUALIZER: Distribution plot saved to {full_path}")

# =================================================================
# اختبار المحاكاة (Demo)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    viz = PathVisualizer()
    
    # 1. توليد بيانات وهمية (Random Walk Simulation)
    # محاكاة 1000 مسار، كل مسار 100 خطوة
    num_sims = 1000
    num_steps = 252 # سنة تداول
    initial_equity = 10000.0
    
    # العوائد اليومية (متوسط 0.05% يومياً، انحراف 2%)
    daily_returns = np.random.normal(0.0005, 0.02, (num_sims, num_steps))
    
    # حساب المسارات التراكمية
    equity_paths = np.zeros((num_sims, num_steps))
    equity_paths[:, 0] = initial_equity
    
    for t in range(1, num_steps):
        equity_paths[:, t] = equity_paths[:, t-1] * (1 + daily_returns[:, t])

    # 2. رسم المسارات
    print("--- Generating Path Visualization ---")
    viz.visualize_equity_curves(equity_paths, initial_equity)
    
    # 3. رسم التوزيع النهائي
    print("--- Generating Distribution Visualization ---")
    final_values = equity_paths[:, -1]
    viz.visualize_final_distribution(final_values, initial_equity)
    
    print("Check logs/sim_plots/ for the generated images.")