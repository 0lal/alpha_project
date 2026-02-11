# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - COLD STORAGE ARCHIVER (PARQUET)
# =================================================================
# Component Name: data/storage/cold/parquet_archiver.py
# Core Responsibility: تحويل البيانات القديمة إلى صيغة Parquet المضغوطة للأرشفة والتدريب.
# Design Pattern: Archiver / Strategy
# Forensic Impact: ينشئ "لقطات مجمدة" (Frozen Snapshots) من التاريخ، غير قابلة للتعديل وسهلة القراءة للذكاء الاصطناعي.
# =================================================================

import os
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class ParquetArchiver:
    """
    أمين الأرشيف البارد.
    يحول البيانات المتطايرة إلى ملفات Parquet صلبة ومضغوطة.
    """

    def __init__(self, archive_root: str = "data/lake"):
        """
        تهيئة الأرشيف.
        
        Args:
            archive_root: المسار الأساسي لبحيرة البيانات (Data Lake).
        """
        self.logger = logging.getLogger("Alpha.Storage.Cold")
        self.archive_path = Path(archive_root)
        
        # التأكد من وجود المجلد
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def archive_batch(self, data: List[Dict[str, Any]], symbol: str, date_str: str) -> Optional[str]:
        """
        ضغط وحفظ دفعة من البيانات.
        
        Args:
            data: قائمة قواميس البيانات (Rows).
            symbol: رمز العملة (للتصنيف).
            date_str: تاريخ البيانات (YYYY-MM-DD).
            
        Returns:
            str: مسار الملف المحفوظ، أو None في حال الفشل.
        """
        if not data:
            self.logger.warning(f"ARCHIVE_SKIP: محاولة أرشفة بيانات فارغة لـ {symbol}.")
            return None

        try:
            # 1. التحويل إلى Pandas DataFrame
            # هذه الخطوة توحد أنواع البيانات (Schema Enforcement)
            df = pd.DataFrame(data)

            # التأكد من صحة الأعمدة الأساسية للتدريب
            required_cols = ['exchange_ts', 'price', 'quantity']
            if not all(col in df.columns for col in required_cols):
                self.logger.error("ARCHIVE_ERROR: البيانات تفتقد أعمدة أساسية للتدريب.")
                return None

            # 2. بناء مسار الملف الهرمي (Partitioning)
            # الهيكلة: data/lake/BTCUSDT/2023/10/
            # هذا يسهل عملية البحث (Querying) لاحقاً
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            year_dir = self.archive_path / symbol / str(target_date.year) / f"{target_date.month:02d}"
            year_dir.mkdir(parents=True, exist_ok=True)

            file_name = f"{symbol}_{date_str}.parquet"
            full_path = year_dir / file_name

            # 3. الكتابة بصيغة Parquet مع ضغط Snappy
            # Snappy: توازن ممتاز بين السرعة وحجم الضغط
            df.to_parquet(full_path, index=False, engine='pyarrow', compression='snappy')

            self.logger.info(f"ARCHIVED: تم حفظ {len(df)} صف في {full_path}")
            return str(full_path)

        except Exception as e:
            self.logger.error(f"ARCHIVE_FAIL: فشل كتابة ملف Parquet: {e}")
            return None

    def load_for_training(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        استرجاع البيانات لتدريب الذكاء الاصطناعي.
        يقوم بدمج عدة ملفات يومية في DataFrame واحد ضخم.
        """
        try:
            # في التطبيق الحقيقي، هنا نستخدم منطق بحث أكثر تعقيداً
            # للتبسيط، نفترض مسح المجلدات (Scan)
            symbol_path = self.archive_path / symbol
            if not symbol_path.exists():
                return pd.DataFrame()

            files = list(symbol_path.rglob("*.parquet"))
            # فلترة الملفات حسب التاريخ (يمكن تحسينه)
            relevant_files = [f for f in files if start_date <= f.name.split('_')[1] <= end_date]

            if not relevant_files:
                self.logger.warning("TRAINING_LOAD: لم يتم العثور على ملفات للفترة المحددة.")
                return pd.DataFrame()

            # قراءة ودمج البيانات (Parquet سريع جداً هنا)
            df_list = [pd.read_parquet(f) for f in relevant_files]
            full_df = pd.concat(df_list, ignore_index=True)
            
            self.logger.info(f"TRAINING_READY: تم تحميل {len(full_df)} صف للتدريب.")
            return full_df

        except Exception as e:
            self.logger.error(f"LOAD_FAIL: فشل تحميل بيانات التدريب: {e}")
            return pd.DataFrame()