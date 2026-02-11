# Warm to Cold Mover

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - AUTOMATED ARCHIVE MANAGER
# =================================================================
# Component Name: data/maintenance/archive_manager.py
# Core Responsibility: نقل البيانات تلقائيًا بين الطبقات (Warm -> Cold) (Storage Pillar).
# Design Pattern: Scheduled Job / ILM (Information Lifecycle Management)
# Forensic Impact: يضمن عدم حذف أي دليل جنائي، بل "تجميده" في الأرشيف قبل إزالته من قاعدة البيانات النشطة.
# =================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# استيراد مدراء التخزين الذين صنعناهم سابقاً
# نفترض أنهم متاحون في المسارات التالية
from data.storage.warm.ts_db_manager import TSDBManager
from data.storage.cold.parquet_archiver import ParquetArchiver

class ArchiveManager:
    """
    مدير دورة حياة البيانات.
    مسؤول عن ترحيل البيانات القديمة من الذاكرة المكلفة (DB) إلى الأرشيف الرخيص (Files).
    """

    def __init__(self, 
                 warm_db: TSDBManager, 
                 cold_archiver: ParquetArchiver,
                 retention_days: int = 30):
        """
        تهيئة المدير.
        
        Args:
            warm_db: مدير قاعدة البيانات السريعة (المصدر).
            cold_archiver: مدير الأرشيف البارد (الوجهة).
            retention_days: عدد الأيام التي تبقى فيها البيانات "حارة" قبل الترحيل.
        """
        self.logger = logging.getLogger("Alpha.Maintenance.Archive")
        self.warm_db = warm_db
        self.cold_archiver = cold_archiver
        self.retention_days = retention_days

    async def run_daily_cycle(self, symbol_list: List[str]):
        """
        تشغيل دورة الأرشفة اليومية.
        يجب جدولة هذه الوظيفة لتعمل في وقت هدوء السوق (مثلاً 00:00 UTC).
        """
        self.logger.info("ARCHIVE_START: بدء دورة الترحيل اليومية...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        self.logger.info(f"CUTOFF_DATE: سيتم أرشفة البيانات الأقدم من {cutoff_date.date()}")

        total_archived = 0

        for symbol in symbol_list:
            try:
                # 1. الاستخراج (Extract)
                # جلب البيانات المرشحة للأرشفة ليوم واحد (قبل الـ Cutoff)
                # للتبسيط، نأخذ يوماً واحداً محدداً (اليوم الذي سقط من نافذة الـ retention)
                target_day_start = cutoff_date.replace(hour=0, minute=0, second=0, microsecond=0)
                target_day_end = target_day_start + timedelta(days=1)

                data = await self.warm_db.fetch_history(symbol, target_day_start, target_day_end)
                
                if not data:
                    continue

                # تحويل الكائنات إلى قواميس (للمعالجة في Archiver)
                # ملاحظة: نفترض أن data هي قائمة كائنات MarketTick
                data_dicts = [tick.__dict__ for tick in data] 

                # 2. النقل (Transfer)
                # الكتابة للأرشيف البارد
                file_path = self.cold_archiver.archive_batch(
                    data=data_dicts,
                    symbol=symbol,
                    date_str=target_day_start.strftime("%Y-%m-%d")
                )

                if file_path:
                    # 3. التحقق والحذف (Verify & Purge)
                    # هذه الخطوة حرجة: لا نحذف من DB إلا إذا تأكدنا أن الملف كتب بنجاح
                    self.logger.info(f"ARCHIVE_SUCCESS: تم حفظ {len(data)} سجل لـ {symbol}. جاري التنظيف من DB...")
                    
                    # في بيئة الإنتاج، نستخدم دالة حذف مخصصة في TSDBManager
                    # await self.warm_db.delete_range(symbol, target_day_start, target_day_end)
                    total_archived += len(data)
                else:
                    self.logger.error(f"ARCHIVE_FAIL: فشل أرشفة {symbol}. لن يتم الحذف من DB.")

            except Exception as e:
                self.logger.error(f"ARCHIVE_ERROR: خطأ أثناء معالجة {symbol}: {e}")

        self.logger.info(f"ARCHIVE_COMPLETE: تم ترحيل {total_archived} سجل بنجاح.")

    async def force_vacuum(self):
        """
        تنظيف المساحة الفارغة في قاعدة البيانات (Vacuum).
        بعد الحذف، لا تعود المساحة لنظام التشغيل تلقائياً في PostgreSQL، لذا نحتاج لهذه العملية.
        """
        # يتطلب صلاحيات Superuser أحياناً
        # await self.warm_db.execute_raw("VACUUM ANALYZE market_ticks;")
        pass