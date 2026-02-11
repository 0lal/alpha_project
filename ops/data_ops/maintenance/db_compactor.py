# Storage Optimizer

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DATABASE COMPACTOR & OPTIMIZER
# =================================================================
# Component Name: data/maintenance/db_compactor.py
# Core Responsibility: تحسين مساحة التخزين وضغط البيانات التاريخية (Storage Pillar).
# Design Pattern: Maintenance Job / Vacuum Cleaner
# Forensic Impact: يحافظ على سرعة استرجاع الأدلة الجنائية عن طريق إزالة "الضوضاء الرقمية" (Dead Tuples).
# =================================================================

import asyncio
import logging
import asyncpg
from typing import List, Optional

class DBCompactor:
    """
    ضاغط قاعدة البيانات.
    مسؤول عن صحة "القرص الصلب" وأداء الاستعلامات.
    """

    def __init__(self, db_url: str):
        """
        تهيئة الضاغط.
        
        Args:
            db_url: رابط الاتصال (postgres://user:pass@host:port/db)
        """
        self.logger = logging.getLogger("Alpha.Maintenance.Compactor")
        self.db_url = db_url

    async def run_maintenance_cycle(self):
        """
        تشغيل دورة الصيانة الكاملة.
        يفضل تشغيلها أسبوعياً أو في أوقات انخفاض السيولة (عطلة نهاية الأسبوع).
        """
        self.logger.info("COMPACTION_START: بدء عملية صيانة وتحسين قاعدة البيانات...")
        
        conn = await asyncpg.connect(self.db_url)
        try:
            # 1. تحليل الإحصائيات (Analyze)
            # تحديث إحصائيات الجداول ليتمكن المخطط (Query Planner) من اختيار أسرع مسار.
            await self._analyze_tables(conn)

            # 2. تنظيف الفراغات (Vacuum)
            # استعادة المساحة المهدورة من الصفوف المحذوفة.
            await self._vacuum_tables(conn)

            # 3. ضغط التايم-سكيل (TimescaleDB Compression)
            # التأكد من أن السياسات تعمل، وضغط أي قطع (Chunks) فوتتها السياسة التلقائية.
            await self._enforce_compression_policies(conn)

            # 4. إعادة الفهرسة (Reindex) - عملية ثقيلة
            # نقوم بها فقط للجداول الحيوية التي تتعرض لكتابة كثيفة
            await self._reindex_critical_indices(conn)

            self.logger.info("COMPACTION_COMPLETE: اكتملت الصيانة بنجاح.")

        except Exception as e:
            self.logger.error(f"COMPACTION_FAIL: فشل عملية الصيانة: {e}")
        finally:
            await conn.close()

    async def _analyze_tables(self, conn):
        """تحديث إحصائيات توزيع البيانات."""
        self.logger.info("STEP 1: تحديث إحصائيات الاستعلام (ANALYZE)...")
        tables = ['market_ticks', 'trade_orders', 'system_audit_log']
        for table in tables:
            try:
                await conn.execute(f"ANALYZE {table};")
                # self.logger.debug(f"ANALYZED: {table}")
            except Exception as e:
                self.logger.warning(f"SKIP_ANALYZE: تعذر تحليل {table}: {e}")

    async def _vacuum_tables(self, conn):
        """تنظيف الجداول (بدون قفل كامل - VACUUM العادي)."""
        self.logger.info("STEP 2: تنظيف المساحات الميتة (VACUUM)...")
        # ملاحظة: لا يمكن تشغيل VACUUM داخل كتلة معاملات (Transaction Block)
        # asyncpg يدير هذا تلقائياً في الغالب، لكن يجب الحذر.
        # هنا نفترض التنفيذ المباشر.
        try:
            # تنظيف جدول السجلات لأنه يمتلئ بسرعة
            await conn.execute("VACUUM api_access_logs;")
            await conn.execute("VACUUM trade_orders;")
        except Exception as e:
            self.logger.warning(f"VACUUM_ERROR: {e}")

    async def _enforce_compression_policies(self, conn):
        """
        إجبار ضغط البيانات القديمة.
        TimescaleDB لديها سياسات تلقائية، لكن هذا "تدخل يدوي" لضمان التنفيذ.
        """
        self.logger.info("STEP 3: التحقق من ضغط القطع الزمنية (Chunks)...")
        
        # استعلام لمعرفة القطع غير المضغوطة التي يجب أن تضغط (أقدم من 7 أيام مثلاً)
        query = """
            SELECT show_chunks('market_ticks', older_than => INTERVAL '7 days')
            EXCEPT
            SELECT show_chunks('market_ticks', older_than => INTERVAL '7 days') 
            FROM timescaledb_information.chunks WHERE is_compressed = True;
        """
        # (هذا الاستعلام تبسيطي، التنفيذ الفعلي يتطلب التعامل مع مخرجات الوظائف)
        
        # بدلاً من التعقيد، نطلب من Timescale تنفيذ السياسات فوراً
        try:
            # تشغيل وظيفة الضغط يدوياً
            await conn.execute("SELECT run_job(job_id) FROM timescaledb_information.jobs WHERE proc_name = 'policy_compression';")
            self.logger.info("COMPRESSION_TRIGGERED: تم تفعيل وظائف الضغط الخلفية.")
        except Exception as e:
            # قد لا توجد وظائف معلقة
            pass

    async def _reindex_critical_indices(self, conn):
        """
        إصلاح الفهارس المتضخمة.
        تحذير: هذا قد يسبب قفلاً (Lock) للجداول للحظات.
        """
        self.logger.info("STEP 4: صيانة الفهارس (REINDEX CONCURRENTLY)...")
        # نستخدم CONCURRENTLY لعدم إيقاف النظام أثناء العمل
        indices = ['idx_orders_status', 'idx_market_ticks_symbol']
        
        for idx in indices:
            try:
                await conn.execute(f"REINDEX INDEX CONCURRENTLY {idx};")
                self.logger.info(f"REINDEXED: {idx}")
            except Exception as e:
                self.logger.warning(f"REINDEX_FAIL: {idx} - {e}")

# مثال للاستخدام (لا يعمل إلا بوجود قاعدة بيانات حقيقية)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # db = DBCompactor("postgresql://postgres:password@localhost:5432/alpha_db")
    # asyncio.run(db.run_maintenance_cycle())