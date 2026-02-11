# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - DISTRIBUTED TRACER
===========================================
Component Name: ops/observability/distributed_tracer.py
Core Responsibility: تتبع مسار القرار عبر اللغات والعمليات المختلفة (Pillar: Explainability).
Creation Date: 2026-02-03
Version: 1.0.0 (The Golden Thread Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يحل مشكلة "الصندوق الأسود" في الأنظمة الموزعة.
يعتمد على تقنية Context Propagation. عندما يرسل Python أمراً إلى Rust، 
يتم إرفاق `trace_id` في ترويسة الرسالة (ZMQ Header).
وبذلك، عندما يسجل Rust خطأً، نعرف بالضبط أي قرار في Python تسبب فيه.
"""

import uuid
import time
import logging
import threading
import contextvars
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from contextlib import contextmanager

# إعداد السجلات
logger = logging.getLogger("AlphaTracer")

# متغيرات السياق (ContextVars) ضرورية جداً في البرمجة غير المتزامنة (Asyncio)
# لضمان عدم تداخل التتبعات بين الطلبات المتزامنة.
_current_trace_id = contextvars.ContextVar("trace_id", default=None)
_current_span_id = contextvars.ContextVar("span_id", default=None)

@dataclass
class Span:
    """
    الامتداد (Span) يمثل وحدة عمل واحدة (مثلاً: "RiskCheck" أو "DBQuery").
    """
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time == 0.0:
            return 0.0
        return (self.end_time - self.start_time) * 1000.0

class DistributedTracer:
    """
    مدير التتبع الموزع.
    مسؤول عن بدء التتبعات، إنشاء الامتدادات، وتجميع البيانات للتصدير.
    """

    def __init__(self):
        # في بيئة الإنتاج، نرسل هذا إلى نظام مثل Jaeger أو Zipkin
        # هنا سنخزنه في الذاكرة مؤقتاً للتصدير للملفات
        self._completed_spans: List[Span] = []
        self._lock = threading.Lock()

    def start_trace(self, trace_id: str = None) -> str:
        """
        بدء تتبع جديد لعملية كاملة (مثلاً: استقبال إشارة سوق).
        """
        tid = trace_id or str(uuid.uuid4())
        _current_trace_id.set(tid)
        _current_span_id.set(None) # تصفير الامتداد الأب
        return tid

    @contextmanager
    def start_span(self, name: str, tags: Dict[str, str] = None):
        """
        سياق لإنشاء Span وقياس وقته تلقائياً.
        Usage:
            with tracer.start_span("CalculateRisk"):
                ... logic ...
        """
        trace_id = _current_trace_id.get()
        if not trace_id:
            # إذا لم يكن هناك تتبع نشط، نبدأ واحداً تلقائياً (Orphan Trace)
            trace_id = self.start_trace()

        parent_span_id = _current_span_id.get()
        new_span_id = str(uuid.uuid4())[:8] # استخدام ID قصير لتوفير المساحة

        # إنشاء الكائن
        span = Span(
            trace_id=trace_id,
            span_id=new_span_id,
            parent_id=parent_span_id,
            name=name,
            start_time=time.perf_counter(), # استخدام دقة عالية
            tags=tags or {}
        )

        # تحديث السياق الحالي ليكون هذا الـ Span هو الأب للعمليات القادمة
        token = _current_span_id.set(new_span_id)

        try:
            yield span
        except Exception as e:
            span.tags["error"] = "true"
            span.tags["error.message"] = str(e)
            raise e
        finally:
            # إنهاء القياس
            span.end_time = time.perf_counter()
            
            # استعادة السياق السابق (الأب)
            _current_span_id.reset(token)
            
            # حفظ الـ Span
            self._record_span(span)

    def _record_span(self, span: Span):
        """حفظ الامتداد المكتمل."""
        with self._lock:
            self._completed_spans.append(span)
            
            # تنظيف الذاكرة إذا امتلأت
            if len(self._completed_spans) > 10000:
                self._flush_spans()

    def get_current_context_headers(self) -> Dict[str, str]:
        """
        تجهيز الترويسات لإرسالها عبر ZMQ إلى Rust.
        هذا هو "تسليم الشعلة" للمحرك.
        """
        return {
            "x-trace-id": _current_trace_id.get() or "",
            "x-parent-span-id": _current_span_id.get() or ""
        }

    def _flush_spans(self):
        """تصدير الامتدادات إلى ملف JSON للتحليل لاحقاً."""
        if not self._completed_spans:
            return

        export_file = "data/logs/traces.jsonl"
        try:
            with open(export_file, "a", encoding="utf-8") as f:
                for span in self._completed_spans:
                    f.write(json.dumps(asdict(span)) + "\n")
            self._completed_spans.clear()
        except Exception as e:
            logger.error(f"Failed to flush traces: {e}")

# --- Global Instance ---
tracer = DistributedTracer()

# --- Unit Test ---
if __name__ == "__main__":
    import random
    
    print("--- Tracing Simulation ---")
    
    # محاكاة دورة حياة صفقة
    # 1. بداية التتبع (استقبال بيانات السوق)
    tid = tracer.start_trace()
    print(f"Trace ID: {tid}")

    with tracer.start_span("MarketDataIngestion", {"symbol": "BTCUSDT"}):
        time.sleep(0.05) # محاكاة معالجة
        
        # 2. عملية فرعية (التحليل)
        with tracer.start_span("NeuralAnalysis"):
            time.sleep(0.1)
            
            # 3. محاكاة إرسال للمحرك
            headers = tracer.get_current_context_headers()
            print(f"Sending to Rust with headers: {headers}")
            
            # 4. عملية فرعية (فحص المخاطر)
            with tracer.start_span("RiskCheck", {"level": "strict"}):
                time.sleep(0.02)

    # طباعة النتائج
    print("\nRecorded Spans:")
    for span in tracer._completed_spans:
        indent = "  " if span.parent_id else ""
        if span.parent_id: indent += "  "
        print(f"{indent}[{span.name}] took {span.duration_ms:.2f}ms (Parent: {span.parent_id})")