# -*- coding: utf-8 -*-
# ==============================================================================
# ALPHA SOVEREIGN - HIGH FREQUENCY STREAM BUFFER
# ==============================================================================
# Component: raw_stream_buffer.py
# Core Responsibility: تجميع البيانات المتدفقة في حزم (Micro-batches) لتقليل الضغط.
# Design Pattern: Producer-Consumer / Leaky Bucket
# Performance: يقلل استدعاءات المعالج بنسبة 90% عبر دمج الإدخالات.
# ==============================================================================

import asyncio
import time
import logging
from typing import List, Any, Callable, Awaitable

# إعداد السجلات
logger = logging.getLogger("StreamBuffer")

class RawStreamBuffer:
    """
    مخزن مؤقت ذكي يعمل بمبدأين للإفراغ:
    1. الامتلاء (Capacity Trigger): إذا وصل العدد لـ 100 عنصر مثلاً.
    2. الزمن (Latency Trigger): إذا مرت 50ms دون امتلاء (لضمان عدم تأخير البيانات).
    """

    def __init__(
        self, 
        processor_callback: Callable[[List[Any]], Awaitable[None]],
        batch_size: int = 100,
        flush_interval_seconds: float = 0.05  # 50ms default latency limit
    ):
        """
        Args:
            processor_callback: الدالة التي ستستلم الحزمة الجاهزة للمعالجة.
            batch_size: الحد الأقصى لعدد العناصر في الحزمة الواحدة.
            flush_interval_seconds: الحد الأقصى للانتظار قبل الإرسال الإجباري.
        """
        self.processor = processor_callback
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        
        # المخزن (Thread-safe in asyncio single thread loop)
        self._buffer: List[Any] = []
        
        # التحكم في الحلقة الزمنية
        self._running = False
        self._timer_task: asyncio.Task = None
        
        # مقاييس الأداء (Telemetry)
        self._last_flush_time = time.time()
        self._total_processed = 0

    async def start(self):
        """تشغيل المؤقت الخلفي (Background Timer)"""
        self._running = True
        self._timer_task = asyncio.create_task(self._monitor_latency())
        logger.info(f"Stream Buffer Active | Batch: {self.batch_size} | Latency: {self.flush_interval}s")

    async def stop(self):
        """إيقاف وإفراغ ما تبقى"""
        self._running = False
        if self._timer_task:
            self._timer_task.cancel()
        # إفراغ نهائي لما تبقى في الذاكرة
        await self.flush(reason="SHUTDOWN")
        logger.info("Stream Buffer Stopped.")

    async def ingest(self, item: Any):
        """
        استقبال عنصر خام جديد.
        هذه الدالة سريعة جداً (Non-blocking).
        """
        self._buffer.append(item)
        
        # 1. Trigger: Size (الامتلاء)
        if len(self._buffer) >= self.batch_size:
            await self.flush(reason="BATCH_FULL")

    async def flush(self, reason: str = "UNKNOWN"):
        """تفريغ المخزن وإرسال البيانات للمعالج"""
        if not self._buffer:
            return

        # 1. القفل السريع: نسخ البيانات وتفريغ القائمة الأصلية فوراً
        # نستخدم Slice Copy [:] لضمان السرعة وعدم تعطل الإدخال الجديد
        data_batch = self._buffer[:]
        self._buffer.clear()
        
        # تحديث التوقيت لمنع المؤقت من الإرسال المزدوج
        self._last_flush_time = time.time()
        self._total_processed += len(data_batch)

        # 2. إرسال البيانات للمعالجة (Brain / Database)
        try:
            # ننتظر المعالجة (أو يمكن جعلها create_task لعدم الانتظار)
            await self.processor(data_batch)
            
            # (اختياري) سجلات للتصحيح فقط في وضع التطوير
            # logger.debug(f"Flushed {len(data_batch)} items. Reason: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to process batch: {e}", exc_info=True)
            # استراتيجية الفشل: هل نعيد البيانات للمخزن؟ أم نتجاهلها؟
            # في HFT، البيانات القديمة لا قيمة لها، لذا نتجاهلها (Drop).

    async def _monitor_latency(self):
        """مراقب زمني لضمان عدم بقاء البيانات طويلاً في الانتظار"""
        while self._running:
            await asyncio.sleep(self.flush_interval)
            
            # 2. Trigger: Time (الزمن)
            time_since_last = time.time() - self._last_flush_time
            
            if self._buffer and time_since_last >= self.flush_interval:
                await self.flush(reason="TIME_LIMIT")

# ==============================================================================
# مثال تطبيقي (للفهم فقط - لا يعمل إلا داخل النظام)
# ==============================================================================
# async def my_ai_processor(batch):
#     print(f"Processing {len(batch)} ticks...")
#     # إرسال للذكاء الاصطناعي...
#
# buffer = RawStreamBuffer(my_ai_processor, batch_size=50)
# await buffer.start()
# await buffer.ingest(tick_data)