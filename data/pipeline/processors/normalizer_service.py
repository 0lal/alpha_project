# Data Standardization

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DATA NORMALIZATION SERVICE
# =================================================================
# Component Name: data/ingestion/normalizer_service.py
# Core Responsibility: توحيد صيغ البيانات العالمية وتحويل العملات والمناطق الزمنية (Integration Pillar).
# Design Pattern: Service / Transformer
# Forensic Impact: يضمن "وحدة المعيار" (Standard of Truth) لجميع البيانات، مما يمنع أخطاء المقارنة الكارثية.
# =================================================================

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
import re

class NormalizerService:
    """
    خدمة التطبيع المركزية.
    تحول البيانات الفوضوية من المصادر الخارجية إلى "نسق ألفا القياسي" (Alpha Standard Format).
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Ingestion.Normalizer")
        
        # التنسيق القياسي للرموز (مثلاً: إزالة الشرطات والمسافات)
        # الهدف: توحيد BTC-USDT و BTC/USDT و BTC_USDT ليصبحوا جميعاً BTCUSDT
        self.symbol_pattern = re.compile(r"[^A-Z0-9]") 

    def standardize_tick(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        نقطة الدخول الرئيسية لتوحيد نبضات السوق.
        
        Args:
            raw_data: البيانات القادمة من المجمعات (Collectors).
            
        Returns:
            Dict: بيانات نظيفة وموحدة، أو None في حال الفشل.
        """
        try:
            # 1. توحيد الرمز (Symbol Normalization)
            symbol = self._normalize_symbol(raw_data.get('symbol'))
            if not symbol:
                raise ValueError("MISSING_SYMBOL")

            # 2. توحيد الأرقام (Numerical Normalization)
            # التأكد من أن الأسعار أرقام عشرية (Float) وليست نصوصاً
            price = self._to_float(raw_data.get('price'))
            quantity = self._to_float(raw_data.get('quantity'))

            # 3. توحيد الوقت (Time Synchronization)
            # تحويل كل التوقيتات إلى UTC Timestamp (ثواني بدقة ميكروثانية)
            exchange_ts = self._normalize_timestamp(raw_data.get('exchange_timestamp'))
            ingestion_ts = self._normalize_timestamp(raw_data.get('ingestion_timestamp'))

            # بناء الحزمة النهائية الموحدة
            normalized_tick = {
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "side": raw_data.get('side', 'UNKNOWN').upper(), # توحيد جانب الصفقة (BUY/SELL)
                "source": raw_data.get('source', 'UNKNOWN'),
                "exchange_ts": exchange_ts,
                "ingestion_ts": ingestion_ts,
                "meta": {
                    "is_normalized": True,
                    "original_currency": raw_data.get('currency', 'USD') # افتراض الدولار كمعيار عالمي
                }
            }
            
            return normalized_tick

        except Exception as e:
            # تسجيل الخطأ جنائياً ولكن عدم إيقاف النظام (Fail Safe)
            self.logger.error(f"NORMALIZATION_ERROR: فشل معالجة البيانات: {e} | Raw: {raw_data}")
            return None

    def _normalize_symbol(self, raw_symbol: Any) -> Optional[str]:
        """
        تنظيف الرموز: إزالة أي فواصل وتحويل الأحرف لكبيرة.
        Example: 'btc-usdt' -> 'BTCUSDT'
        """
        if not raw_symbol:
            return None
        
        # تحويل للنص ثم للأحرف الكبيرة
        s = str(raw_symbol).upper()
        # إزالة الرموز غير الأبجدية الرقمية
        return self.symbol_pattern.sub("", s)

    def _to_float(self, value: Any) -> float:
        """
        تحويل آمن للأرقام. يعالج النصوص التي تحتوي على فواصل (مثل '1,000.00').
        """
        if value is None:
            return 0.0
        try:
            if isinstance(value, str):
                # إزالة فواصل الآلاف إذا وجدت
                value = value.replace(",", "")
            return float(value)
        except ValueError:
            self.logger.warning(f"NUMERIC_ERROR: تعذر تحويل القيمة '{value}' إلى رقم.")
            return 0.0

    def _normalize_timestamp(self, ts: Any) -> float:
        """
        توحيد الزمن إلى UTC Unix Timestamp (Float).
        يدعم المدخلات: (Milliseconds Int, ISO String, datetime object).
        """
        if ts is None:
            return datetime.now(timezone.utc).timestamp()

        try:
            # الحالة 1: رقم (Timestamp)
            if isinstance(ts, (int, float)):
                # إذا كان الرقم ضخماً (بالميلي ثانية)، حوله لثواني
                if ts > 1e11:  # مثلاً سنة 3000+ بالثواني، يعني أنه ميلي ثانية
                    return ts / 1000.0
                return float(ts)

            # الحالة 2: كائن datetime
            if isinstance(ts, datetime):
                return ts.replace(tzinfo=timezone.utc).timestamp()

            # الحالة 3: نص (ISO Format String)
            if isinstance(ts, str):
                # محاولة قراءة ISO Format (2026-02-01T12:00:00Z)
                # استخدام replace لضمان توافق Python 3.7+ مع الـ Z
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.timestamp()

        except Exception:
            self.logger.warning(f"TIME_ERROR: صيغة وقت غير مدعومة '{ts}'. استخدام الوقت الحالي.")
            return datetime.now(timezone.utc).timestamp()