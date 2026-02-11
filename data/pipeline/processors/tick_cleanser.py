# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DATA INTEGRITY FILTER
# =================================================================
# Component Name: data/ingestion/filters/tick_cleanser.py
# Core Responsibility: تصفية الضجيج الإحصائي وفخاخ السيولة (Data Integrity Pillar).
# Design Pattern: Filter / Pipe
# Forensic Impact: يمنع "التسمم السعري" (Price Poisoning) ويحمي المحرك من اتخاذ قرارات بناءً على أوهام.
# =================================================================

import logging
from collections import deque, defaultdict
from typing import Dict, Optional, Any
import math

class TickCleanser:
    """
    مصفاة البيانات اللحظية.
    تطبق قواعد فيزيائية وإحصائية للتحقق من سلامة كل نبضة سعرية (Tick) قبل دخولها للنظام.
    """

    def __init__(self):
        # إعداد سجلات جنائية خاصة بالفلترة
        self.logger = logging.getLogger("Alpha.Filter.Cleanser")
        
        # إعدادات الذاكرة الإحصائية (Rolling Window)
        # نحتفظ بآخر 20 سعر لكل عملة لحساب المتوسط والانحراف المعياري
        self.window_size = 20
        self.price_history = defaultdict(lambda: deque(maxlen=20))
        
        # حدود الأمان (Safety Thresholds)
        self.max_z_score = 3.0       # أي انحراف يتجاوز 3 أضعاف الانحراف المعياري يعتبر شذوذاً (Anomaly)
        self.max_latency_ms = 400    # رفض البيانات القديمة جداً (Stale Data)

    def process_tick(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        نقطة الدخول الرئيسية.
        
        Args:
            tick: قاموس البيانات الخام القادم من المجمع (Collector).
            
        Returns:
            Dict: البيانات النظيفة، أو None إذا تم رفض النبضة.
        """
        symbol = tick.get('symbol')
        price = tick.get('price')

        # 1. الفحص الهيكلي (Structural Integrity)
        if not symbol or not price:
            return None # بيانات تالفة هيكلياً

        # 2. الفحص الفيزيائي (Physical Constraints)
        if not self._is_physically_valid(tick):
            self.logger.warning(f"PHYSICAL_REJECT: {symbol} بيانات غير منطقية فيزيائياً.")
            return None

        # 3. فحص الكمون (Latency Check)
        # نرفض البيانات التي تأخرت في الطريق لأنها لم تعد تمثل الواقع
        if tick.get('alpha_latency_ms', 0) > self.max_latency_ms:
            # نسجل هذا الحدث كتحذير خفيف (قد يكون مجرد بطء نت)
            # self.logger.debug(f"LATENCY_REJECT: {symbol} تأخير {tick['alpha_latency_ms']}ms")
            return None 

        # 4. الفحص الإحصائي (Statistical Anomaly Detection)
        # هذا هو الجزء الأهم: كشف الـ Flash Crashes والـ Fat Fingers
        if not self._is_statistically_sound(symbol, price):
            self.logger.warning(f"STATISTICAL_REJECT: {symbol} سعر شاذ ({price}) تم كبحه.")
            return None

        # 5. تحديث الذاكرة والموافقة
        self.price_history[symbol].append(price)
        
        # إضافة ختم الموافقة (Filter Signature)
        tick['is_cleansed'] = True
        return tick

    def _is_physically_valid(self, tick: Dict[str, Any]) -> bool:
        """
        التحقق من بديهيات السوق.
        """
        price = tick['price']
        qty = tick.get('quantity', 0)

        # السعر لا يمكن أن يكون سالباً أو صفراً (في الأسواق الفورية)
        if price <= 0:
            return False
            
        # الكمية لا يمكن أن تكون سالبة
        if qty < 0:
            return False
            
        return True

    def _is_statistically_sound(self, symbol: str, current_price: float) -> bool:
        """
        حساب الـ Z-Score لتحديد ما إذا كان السعر يمثل "حركة طبيعية" أم "خطأ كارثي".
        """
        history = self.price_history[symbol]

        # في بداية التشغيل (البيانات قليلة)، نقبل كل شيء حتى نملأ الذاكرة
        if len(history) < 5:
            return True

        # 1. حساب المتوسط (Mean)
        mean = sum(history) / len(history)

        # 2. حساب التباين (Variance)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        
        # 3. حساب الانحراف المعياري (Standard Deviation)
        std_dev = math.sqrt(variance)

        # إذا كان السوق هادئاً جداً (std_dev قريب من الصفر)، أي حركة صغيرة ستبدو كشذوذ.
        # لذا نضع حداً أدنى للانحراف لتجنب الحساسية المفرطة.
        if std_dev < (mean * 0.0001): # 0.01% تقريباً
            return True

        # 4. حساب درجة الشذوذ (Z-Score)
        # المعادلة: (السعر الحالي - المتوسط) / الانحراف المعياري
        z_score = abs(current_price - mean) / std_dev

        # إذا كانت الدرجة أكبر من 3 (قاعدة 3-Sigma)، فهذا يعني أن الاحتمالية أقل من 0.3%
        # غالباً هذا خطأ في البيانات أو تلاعب لحظي (Wick) لا يجب التداول عليه.
        if z_score > self.max_z_score:
            return False
            
        return True