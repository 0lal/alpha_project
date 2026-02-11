# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - ANOMALY DETECTION GATEKEEPER
# =================================================================
# Component Name: data/ingestion/filters/anomaly_gate.py
# Core Responsibility: كشف البيانات الشاذة أو المتلاعبة (Pillar: Data Integrity).
# Design Pattern: Gatekeeper / Chain of Responsibility
# Forensic Impact: يمنع "تسمم البيانات" (Data Poisoning) من تضليل الشبكات العصبية.
# =================================================================

import logging
from typing import Dict, Optional, Any
from datetime import datetime

class AnomalyGate:
    """
    بوابة الأمان المتقدمة.
    تفحص سياق السوق للكشف عن التلاعب المتعمد أو الانهيارات الهيكلية.
    """

    def __init__(self):
        # إعداد السجلات الجنائية
        self.logger = logging.getLogger("Alpha.Filter.AnomalyGate")
        
        # --- ثوابت الفيزياء المالية (Financial Physics Constants) ---
        
        # الحد الأقصى لتغير السعر في النبضة الواحدة (5%)
        # أي تغير أكبر من هذا في ملي ثانية يعتبر مستحيلاً فيزيائياً في سوق طبيعي (Flash Crash).
        self.MAX_SINGLE_TICK_CHANGE_PERCENT = 5.0
        
        # الحد الأدنى للسيولة المقبولة (بالدولار التقريبي)
        # إذا كانت الصفقة قيمتها 1 دولار وحركت السعر 1%، فهذا تلاعب (Thin Market).
        self.MIN_NOTIONAL_VALUE_FOR_IMPACT = 10.0 
        
        # ذاكرة الحالة السابقة لكل رمز (لحساب التغيرات النسبية)
        self.last_known_state: Dict[str, Dict[str, float]] = {}

    def inspect(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        نقطة التفتيش الرئيسية.
        
        Args:
            tick: البيانات النظيفة القادمة من TickCleanser.
            
        Returns:
            Dict: البيانات المعتمدة، أو None إذا تم رفضها كبيانات مشبوهة.
        """
        if not tick or not tick.get('is_cleansed'):
            return None # رفض أي بيانات لم تمر بمرحلة التنظيف الأولية

        symbol = tick['symbol']
        current_price = tick['price']
        quantity = tick.get('quantity', 0.0)
        
        # استرجاع الحالة السابقة للمقارنة
        prev_state = self.last_known_state.get(symbol)

        # إذا كانت هذه أول نبضة نراها، نعتمدها ونخزنها
        if not prev_state:
            self._update_state(symbol, current_price, quantity)
            return tick

        # --- تنفيذ بروتوكولات الكشف (Detection Protocols) ---

        # 1. كشف السرعة المستحيلة (Velocity Check)
        if self._is_impossible_move(current_price, prev_state['price']):
            self.logger.critical(f"ANOMALY_DETECTED: {symbol} قفزة سعرية مستحيلة! (Flash Crash Blocked).")
            return None

        # 2. كشف التلاعب بالسيولة (Liquidity Trap)
        # إذا تحرك السعر بقوة ولكن بحجم تداول تافه
        if self._is_liquidity_illusion(current_price, prev_state['price'], quantity):
            self.logger.warning(f"MANIPULATION_ATTEMPT: {symbol} حركة سعرية بدون حجم حقيقي.")
            return None

        # تحديث الحالة وتمرير البيانات
        self._update_state(symbol, current_price, quantity)
        
        # إضافة ختم الأمان النهائي
        tick['integrity_verified'] = True
        return tick

    def _update_state(self, symbol: str, price: float, qty: float):
        """تحديث الذاكرة بآخر بيانات صحيحة."""
        self.last_known_state[symbol] = {
            'price': price,
            'quantity': qty,
            'timestamp': datetime.utcnow().timestamp()
        }

    def _is_impossible_move(self, current_price: float, prev_price: float) -> bool:
        """
        التحقق مما إذا كان التغير السعري يتجاوز الحدود الفيزيائية للسوق.
        """
        if prev_price == 0: return False
        
        percent_change = abs((current_price - prev_price) / prev_price) * 100
        
        if percent_change > self.MAX_SINGLE_TICK_CHANGE_PERCENT:
            return True
        return False

    def _is_liquidity_illusion(self, current_price: float, prev_price: float, qty: float) -> bool:
        """
        كشف الوهم: هل التغير السعري مدعوم بمال حقيقي؟
        """
        percent_change = abs((current_price - prev_price) / prev_price) * 100
        
        # قيمة الصفقة (Notional Value) = السعر * الكمية
        trade_value = current_price * qty

        # القاعدة: إذا تحرك السعر أكثر من 0.5% ولكن بقيمة تداول أقل من 10 دولار
        # فهذا يعني أن دفتر الأوامر (Orderbook) فارغ، وهذه الحركة وهمية ستختفي فوراً.
        if percent_change > 0.5 and trade_value < self.MIN_NOTIONAL_VALUE_FOR_IMPACT:
            return True
            
        return False