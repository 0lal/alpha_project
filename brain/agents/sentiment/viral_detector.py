# Trend Spotter

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - VIRAL TREND & BUBBLE DETECTOR
# =================================================================
# Component Name: brain/agents/sentiment/viral_detector.py
# Core Responsibility: كشف بداية الاتجاهات الفيروسية (Trending) والفقاعات السعرية (Intelligence Pillar).
# Design Pattern: Anomaly Detection / Sliding Window
# Forensic Impact: يفرق بين "الهوس الجماعي" (Mass Hysteria) وبين "الضخ المنسق" (Pump & Dump) عبر تحليل التنوع.
# =================================================================

import logging
import numpy as np
from collections import deque, Counter
from typing import Dict, List, Any, Optional
from datetime import datetime

class ViralDetector:
    """
    كاشف الفيروسية.
    يراقب معدل تسارع الحديث عن عملة معينة للكشف عن الانفجارات الاجتماعية قبل انعكاسها على السعر.
    """

    def __init__(self, window_size: int = 60):
        """
        Args:
            window_size: حجم النافذة الزمنية (بالدقائق) لحساب المتوسط المتحرك.
        """
        self.logger = logging.getLogger("Alpha.Brain.Sentiment.Viral")
        
        # تخزين بيانات السلاسل الزمنية لكل عملة
        # Structure: { 'BTC': deque([count_t1, count_t2, ...], maxlen=60) }
        self.mention_velocity = {} 
        self.user_entropy = {} # لتخزين تنوع المستخدمين
        
        # العتبات الإحصائية (Z-Score Thresholds)
        self.viral_threshold_z = 3.0  # 3 انحرافات معيارية (99.7% احتمال شذوذ)
        self.fomo_acceleration_limit = 2.0 # معدل تضاعف السرعة

    def ingest_stream_stats(self, symbol: str, volume_count: int, unique_users: int):
        """
        تغذية الكاشف بإحصائيات الدقيقة الحالية.
        """
        if symbol not in self.mention_velocity:
            self.mention_velocity[symbol] = deque(maxlen=60) # ساعة من التاريخ
            self.user_entropy[symbol] = deque(maxlen=60)

        # تسجيل السرعة (Mentions per minute)
        self.mention_velocity[symbol].append(volume_count)
        
        # تسجيل كثافة المستخدمين (Unique Users / Volume)
        # نسبة 1.0 تعني كل منشور من مستخدم مختلف (عضوي)
        # نسبة 0.1 تعني كل مستخدم نشر 10 مرات (بوتات/سبام)
        density = unique_users / max(1, volume_count)
        self.user_entropy[symbol].append(density)

    def check_viral_status(self, symbol: str) -> Dict[str, Any]:
        """
        فحص هل العملة تدخل في حالة فيروسية الآن؟
        """
        history = list(self.mention_velocity.get(symbol, []))
        entropy_hist = list(self.user_entropy.get(symbol, []))

        if len(history) < 10:
            return {"status": "WARMUP"} # نحتاج بيانات أكثر

        # 1. حساب Z-Score للحجم الحالي (Anomaly Detection)
        current_vol = history[-1]
        baseline_mean = np.mean(history[:-1]) # المتوسط بدون القيمة الحالية
        baseline_std = np.std(history[:-1])   # الانحراف المعياري
        
        if baseline_std == 0:
            z_score = 0
        else:
            z_score = (current_vol - baseline_mean) / baseline_std

        # 2. حساب التسارع (Acceleration)
        # المشتقة الأولى للحجم بالنسبة للزمن
        velocity_now = current_vol
        velocity_prev = history[-2]
        acceleration = velocity_now - velocity_prev

        # 3. الفحص الجنائي: هل هو ضخ وهمي؟ (Fake Pump Check)
        current_entropy = entropy_hist[-1]
        is_organic = current_entropy > 0.6 # يجب أن يكون 60% من المنشورات من مستخدمين فريدين

        # 4. القرار النهائي
        status = "NORMAL"
        risk_level = "LOW"
        
        if z_score > self.viral_threshold_z:
            if is_organic:
                status = "VIRAL_BREAKOUT" # انفجار حقيقي
                risk_level = "HIGH_VOLATILITY"
                self.logger.info(f"VIRAL_ALERT: {symbol} Z-Score: {z_score:.2f} (Organic)")
            else:
                status = "COORDINATED_PUMP" # هجوم بوتات
                risk_level = "MANIPULATION_RISK"
                self.logger.warning(f"FAKE_PUMP_ALERT: {symbol} High Vol but Low Entropy ({current_entropy:.2f})")

        elif z_score > 1.5 and acceleration > 0:
            status = "HEATING_UP" # بداية الصعود
            risk_level = "MEDIUM"

        return {
            "agent": "ViralDetector",
            "symbol": symbol,
            "metrics": {
                "current_velocity": current_vol,
                "acceleration": acceleration,
                "z_score": round(z_score, 2),
                "entropy_score": round(current_entropy, 2)
            },
            "diagnosis": {
                "status": status,
                "is_organic": is_organic,
                "risk_level": risk_level
            }
        }

    def detect_bubble_burst(self, symbol: str, price_action: float) -> bool:
        """
        كشف انفجار الفقاعة.
        الشرط: الزخم الاجتماعي ينخفض بسرعة بينما السعر لا يزال مرتفعاً (Divergence).
        """
        history = list(self.mention_velocity.get(symbol, []))
        if len(history) < 20: return False

        # متوسط آخر 5 دقائق vs متوسط ما قبل 20 دقيقة
        recent_avg = np.mean(history[-5:])
        past_peak = np.max(history[:-5])

        # إذا انهار النقاش الاجتماعي بنسبة 50% من القمة
        social_crash = recent_avg < (past_peak * 0.5)
        
        # والسعر لا يزال يصعد (أو ثابت)
        price_high = price_action > 0 # (تبسيط: نحتاج مقارنة السعر بالقمة)

        if social_crash and price_high:
            self.logger.warning(f"BUBBLE_WARNING: {symbol} social interest collapsed while price is high.")
            return True
            
        return False