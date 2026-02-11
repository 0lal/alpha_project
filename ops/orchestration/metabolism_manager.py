# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DATA METABOLISM ORCHESTRATOR
# =================================================================
# Component Name: data/metabolism_manager.py
# Core Responsibility: المايسترو المركزي: المنسق الكلي لدورة حياة البيانات (Governance Pillar).
# Design Pattern: Orchestrator / Facade / Mediator
# Forensic Impact: نقطة التحكم المركزية. إذا توقف هذا الملف، يعتبر النظام "ميتاً سريرياً".
# =================================================================

import asyncio
import logging
from typing import Dict, Any, List

# --- [UPDATED IMPORTS] استيراد الأعضاء الحيوية من المواقع الجديدة ---

# 1. التوحيد (Ingestion Layer)
from data.ingestion.normalizer_service import NormalizerService

# 2. المخازن المؤقتة (Buffers Layer)
from data.buffers.raw_stream_buffer import RawStreamBuffer

# 3. التخزين المباشر (Storage Layers - Flattened)
from data.hot.cache_provider import CacheProvider
# ملاحظة: TSDBManager هنا يفترض وجود رابط Python (FFI) للملف Rust
# تأكد من بناء ملف Rust لاحقاً باستخدام maturin ليصبح مكتبة بايثون قابلة للاستيراد
from data.warm.ts_db_manager import TSDBManager, MarketTick 
from data.cold.parquet_archiver import ParquetArchiver

# 4. الذاكرة المتجهية (تم تحديث الاسم والمكان)
from data.vector_db_wrapper import AlphaQdrantClient

# --- استيراد طاقم الصيانة (Validation & Maintenance) ---
from data.maintenance.archive_manager import ArchiveManager
from data.maintenance.db_compactor import DBCompactor
from data.validation.integrity_checker import IntegrityChecker  # تم نقله من governance

class MetabolismManager:
    """
    مدير الأيض (التمثيل الغذائي) للبيانات.
    يدير تدفق البيانات من لحظة دخولها (Ingestion) حتى دفنها في الأرشيف (Archival).
    """

    def __init__(self, db_url: str, redis_host: str = "127.0.0.1"):
        self.logger = logging.getLogger("Alpha.Core.Metabolism")
        self.is_running = False
        
        # 1. طبقة المعالجة الأولية
        self.normalizer = NormalizerService()
        
        # 2. طبقة التخزين المؤقت (Buffers)
        # نضبط البفر ليفرغ كل 100 عنصر أو كل 0.05 ثانية (حسب الكود الجديد للبفر)
        self.stream_buffer = RawStreamBuffer(
            processor_callback=self._persist_batch, # تمرير الدالة مباشرة حسب التصميم الجديد للبفر
            batch_size=100, 
            flush_interval_seconds=0.05
        )
        
        # 3. طبقة التخزين (Storage Providers)
        self.hot_cache = CacheProvider(host=redis_host)
        self.warm_db = None # سيتم تهيئته لاحقاً لأن اتصاله async
        self.cold_archiver = ParquetArchiver()
        self.vector_memory = AlphaQdrantClient()
        
        # 4. إعدادات الاتصال (Connection Configs)
        self._db_url = db_url

        # 5. طاقم الصيانة (سيتم تهيئتهم بعد الاتصال بقاعدة البيانات)
        self.archiver_service = None
        self.compactor_service = None
        self.integrity_auditor = IntegrityChecker()

    async def ignite(self):
        """
        تشغيل النظام (System Boot Sequence).
        تشبه عملية إقلاع الطائرة: فحص الأنظمة، تشغيل المحركات، ثم الإقلاع.
        """
        self.logger.info("SYSTEM_IGNITION: بدء تشغيل نظام أيض البيانات...")

        try:
            # A. الاتصال بالذاكرة الحارة (Redis)
            if await self.hot_cache.connect():
                self.logger.info("   [OK] Hot Cache (Redis)")
            else:
                raise ConnectionError("فشل الاتصال بـ Redis")

            # B. الاتصال بالذاكرة الدافئة (TimescaleDB)
            # ملاحظة: TSDBManager.new هي دالة async
            self.warm_db = await TSDBManager.new(self._db_url)
            self.logger.info("   [OK] Warm DB (Timescale)")

            # C. تشغيل البفر (Stream Buffer)
            # التصميم الجديد للبفر يتطلب استدعاء start() لتشغيل مراقب الوقت
            await self.stream_buffer.start()
            self.logger.info("   [OK] Stream Buffer Active")

            # D. تهيئة خدمات الصيانة
            self.archiver_service = ArchiveManager(self.warm_db, self.cold_archiver)
            self.compactor_service = DBCompactor(self._db_url)
            
            # E. فحص النزاهة الأولي (Sanity Check)
            audit_report = self.integrity_auditor.run_full_audit()
            if audit_report["status"] == "FAIL":
                self.logger.warning(f"   [WARN] Integrity Issues Detected: {audit_report['corrupted_files']}")

            self.is_running = True
            self.logger.info("METABOLISM_ONLINE: النظام يعمل بكامل طاقته.")

            # تشغيل مهام الخلفية (Background Loops)
            asyncio.create_task(self._maintenance_loop())

        except Exception as e:
            self.logger.critical(f"IGNITION_FAIL: فشل إقلاع النظام! {e}")
            raise e

    async def ingest_tick(self, raw_data: Dict[str, Any]):
        """
        نقطة الدخول العامة للبيانات (The Mouth).
        يستقبل البيانات من الـ WebSocket، ينظفها، ويوزعها.
        """
        if not self.is_running:
            return

        # 1. التوحيد (Normalization)
        normalized_tick = self.normalizer.standardize_tick(raw_data)
        if not normalized_tick:
            return # بيانات تالفة تم رفضها

        # 2. التوزيع السريع (Hot Path) -> Redis
        # لتستخدمها الواجهة الرسومية والاستراتيجيات اللحظية
        symbol = normalized_tick['symbol']
        await self.hot_cache.set(f"LATEST_TICK:{symbol}", normalized_tick)

        # 3. التخزين الدائم (Warm Path) -> Buffer -> DB
        # نضيفها للبفر، وهو سيتكفل بحقنها في قاعدة البيانات عندما يمتلئ
        # لاحظ استخدام ingest بدلاً من add في الكود الجديد للبفر
        await self.stream_buffer.ingest(normalized_tick)

    async def _persist_batch(self, batch: List[Dict[str, Any]]):
        """
        الدالة الداخلية التي يستدعيها البفر لتفريغ الحمولة في قاعدة البيانات.
        """
        if not self.warm_db:
            return

        # تحويل القواميس إلى كائنات MarketTick (كما يتوقع TSDBManager)
        # هذا التحويل ضروري لضمان تطابق الأنواع (Type Safety)
        ticks_objects = []
        for item in batch:
            try:
                tick = MarketTick(
                    time=item['time'], # يجب أن يكون datetime object هنا
                    symbol=item['symbol'],
                    price=item['price'],
                    quantity=item['quantity'],
                    source=item['source'],
                    is_anomalous=item.get('is_anomalous', False)
                )
                ticks_objects.append(tick)
            except Exception as conversion_error:
                self.logger.error(f"CONVERSION_ERROR: فشل تحويل البيانات للتخزين: {conversion_error}")

        # الحفظ الجماعي
        if ticks_objects:
            await self.warm_db.insert_batch(ticks_objects)

    async def _maintenance_loop(self):
        """
        حلقة الصيانة الدورية (The Circadian Rhythm).
        """
        while self.is_running:
            # هنا نضع منطق الجدولة (مثلاً التحقق من الساعة)
            # للتبسيط، ننتظر ساعة ثم نقوم بالفحص
            await asyncio.sleep(3600) 
            
            # (في التطبيق الحقيقي، نتحقق من الوقت قبل التشغيل)
            # if self.archiver_service:
            #     await self.archiver_service.run_daily_cycle(['BTCUSDT', 'ETHUSDT'])

    async def shutdown(self):
        """
        بروتوكول الإغلاق الآمن (Graceful Shutdown).
        """
        self.logger.info("SHUTDOWN_INIT: بدء إجراءات الإغلاق...")
        self.is_running = False

        # 1. إيقاف وتفريغ البفر (أهم خطوة لعدم ضياع البيانات المعلقة في RAM)
        await self.stream_buffer.stop()
        
        # 2. إغلاق الاتصالات
        if self.hot_cache:
            await self.hot_cache.disconnect()
        
        if self.warm_db:
            await self.warm_db.close()

        self.logger.info("SHUTDOWN_COMPLETE: تم إغلاق النظام بأمان.")