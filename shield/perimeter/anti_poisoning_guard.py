# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - DATA POISONING DETECTION GUARD
=================================================================
Component: shield/perimeter/anti_poisoning_guard.py
Core Responsibility: كشف هجمات تسميم البيانات والأمثلة العدائية (Adversarial Attacks) (Security Pillar).
Design Pattern: Filter Chain / Statistical Sentinel
Forensic Impact: يمنع "الدماغ" من التعلم من بيانات مزيفة. يسجل محاولات التلاعب بالسوق كأدلة جنائية.
=================================================================
"""

import numpy as np
import logging
from typing import List, Dict, Union, Tuple
from dataclasses import dataclass

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.poison_guard")

@dataclass
class GuardReport:
    is_clean: bool
    reason: str = "OK"
    severity: float = 0.0 # 0.0 (Clean) -> 1.0 (Toxic)

class AntiPoisoningGuard:
    """
    درع حماية ضد البيانات الخبيثة.
    يفحص تدفق البيانات (Data Stream) قبل وصوله لنماذج الذكاء الاصطناعي.
    """
    
    def __init__(self, sensitivity: float = 3.0):
        # حساسية الكشف (عدد الانحرافات المعيارية Z-Score)
        self.z_score_threshold = sensitivity
        
        # الذاكرة القصيرة لحساب المتوسط المتحرك (Baseline)
        self.history_window: List[float] = []
        self.max_history_len = 1000

    def validate_stream(self, data_point: float) -> GuardReport:
        """
        فحص نقطة بيانات جديدة (سعر أو حجم) مقابل التاريخ الحديث.
        """
        # 1. تحديث الذاكرة
        self.history_window.append(data_point)
        if len(self.history_window) > self.max_history_len:
            self.history_window.pop(0)
            
        # نحتاج بيانات كافية للحكم
        if len(self.history_window) < 50:
            return GuardReport(is_clean=True, reason="WARMING_UP")

        # 2. الفحوصات الإحصائية
        
        # أ) فحص الانحراف المعياري (Z-Score) - لكشف الارتفاعات الحادة غير الطبيعية
        z_score_report = self._check_z_score(data_point)
        if not z_score_report.is_clean:
            return z_score_report
            
        # ب) فحص التكرار المشبوه (Repeated Values) - لكشف تجميد الأسعار
        # (بعض البوتات ترسل نفس السعر آلاف المرات لإرباك النظام)
        if self._check_suspicious_repetition():
            return GuardReport(is_clean=False, reason="PATTERN_FREEZE_DETECTED", severity=0.8)

        # ج) فحص المنطق (Integrity)
        if data_point < 0:
            return GuardReport(is_clean=False, reason="LOGIC_VIOLATION_NEGATIVE_VALUE", severity=1.0)

        return GuardReport(is_clean=True)

    def validate_batch(self, batch: np.ndarray) -> GuardReport:
        """
        فحص حزمة بيانات تدريب كاملة (Training Batch).
        يستخدم لكشف "حقن البيانات" (Injection) في مجموعة التدريب.
        """
        # 1. كشف القيم المتطرفة (Outliers) باستخدام IQR
        # البيانات المسمومة غالباً ما تكون بعيدة جداً عن التوزيع الطبيعي
        q1 = np.percentile(batch, 25)
        q3 = np.percentile(batch, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)
        
        outliers = batch[(batch < lower_bound) | (batch > upper_bound)]
        outlier_ratio = len(outliers) / len(batch)

        # إذا كانت نسبة القيم الشاذة عالية جداً (مثلاً > 5%)، فهذا تسميم محتمل
        if outlier_ratio > 0.05:
            logger.warning(f"POISON_GUARD: High outlier ratio detected: {outlier_ratio:.2%}")
            return GuardReport(
                is_clean=False, 
                reason=f"STATISTICAL_POISONING_DETECTED (Outliers: {len(outliers)})", 
                severity=outlier_ratio
            )
            
        return GuardReport(is_clean=True)

    def _check_z_score(self, value: float) -> GuardReport:
        """حساب Z-Score محلياً"""
        history = np.array(self.history_window[:-1]) # استثناء القيمة الحالية من الحساب
        mean = np.mean(history)
        std = np.std(history)
        
        if std == 0: return GuardReport(is_clean=True) # تجنب القسمة على صفر
        
        z = abs((value - mean) / std)
        
        if z > self.z_score_threshold:
            logger.warning(f"POISON_GUARD: Z-Score Violation! Val: {value}, Mean: {mean:.2f}, Z: {z:.2f}")
            # في الأسواق المالية، 6 سيجما تحدث، لكن 20 سيجما تعني تلاعباً أو خطأ بيانات
            if z > 20: 
                return GuardReport(is_clean=False, reason="IMPOSSIBLE_SPIKE", severity=1.0)
            # بين 3 و 20 نعتبرها مشبوهة لكن قد تكون حقيقية (Flash Crash)
            return GuardReport(is_clean=False, reason="EXTREME_VOLATILITY_ANOMALY", severity=z/20.0)
            
        return GuardReport(is_clean=True)

    def _check_suspicious_repetition(self) -> bool:
        """هل آخر 10 قيم متطابقة تماماً؟"""
        if len(self.history_window) < 10: return False
        last_10 = self.history_window[-10:]
        # إذا كان الانحراف المعياري لآخر 10 قيم هو صفر، فهي متطابقة
        return np.std(last_10) == 0

# =================================================================
# اختبار المحاكاة (Adversarial Simulation)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    guard = AntiPoisoningGuard(sensitivity=3.0)
    
    print("--- 1. Normal Market Data ---")
    # توليد بيانات عادية (Random Walk)
    price = 100.0
    for _ in range(60):
        price += np.random.normal(0, 0.5)
        report = guard.validate_stream(price)
        if not report.is_clean:
            print(f"ALERT: {report.reason}")
    print("System stable.")

    print("\n--- 2. Poisoning Attack (Sudden Spike) ---")
    # هجوم: حقن قيمة ضخمة فجأة
    poisoned_price = price * 1.5 # قفزة 50%
    report = guard.validate_stream(poisoned_price)
    print(f"Attack Result: {report.reason} | Severity: {report.severity:.2f}")

    print("\n--- 3. Batch Poisoning (Training Data) ---")
    # إنشاء حزمة بيانات وتلويث 10% منها بقيم عشوائية عالية
    clean_data = np.random.normal(100, 5, 1000)
    toxic_noise = np.random.normal(500, 50, 100) # بيانات مسمومة بعيدة جداً
    mixed_batch = np.concatenate([clean_data, toxic_noise])
    
    batch_report = guard.validate_batch(mixed_batch)
    print(f"Batch Analysis: {batch_report.reason}")