import os
import json
import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

# --- استيراد البنية التحتية ---
from ui.core.config_provider import config
from ui.core.logger_sink import logger_sink
from ui.core.workers import task_manager
from ui.core.stream_handler import stream_handler # لاستخراج الصندوق الأسود

class AlphaDataManager(QObject):
    """
    The Custodian of Records.
    
    الوظيفة:
    1. إدارة البيانات التاريخية (Historical Data) لغرض الاختبار والمحاكاة.
    2. أرشفة سجلات الجلسات (Logs & Blackbox Dumps) للتحليل الجنائي.
    3. ضمان نزاهة البيانات (Data Integrity) ومنع تحميل ملفات تالفة.
    
    التحليل الجنائي:
    يفضل استخدام تنسيق Parquet لأنه يحفظ أنواع البيانات (Data Types) بدقة
    ويمنع أخطاء التحويل الشهيرة في CSV (مثل تحويل التواريخ إلى نصوص).
    """

    # إشارة عند انتهاء تحميل بيانات (ترسل DataFrame جاهز)
    data_loaded = pyqtSignal(str, object) # dataset_id, pandas DataFrame
    
    # إشارة عند فشل التحميل
    load_failed = pyqtSignal(str, str) # dataset_id, error_message
    
    # إشارة عند اكتمال تصدير التقرير
    export_completed = pyqtSignal(str) # file_path

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaDataManager._instance is not None:
            raise Exception("DataManager is a Singleton!")

        # تحديد مسارات البيانات بدقة من ConfigProvider
        self.data_root = config.project_root / "data"
        self.backtest_dir = self.data_root / "storage" / "backtest"
        self.logs_dir = self.data_root / "logs" / "sessions"
        
        # التأكد من وجود المجلدات
        self._ensure_directories()
        
        logger_sink.log_system_event("DataManager", "INFO", "📚 Archives & Records System Online.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaDataManager()
        return cls._instance

    def _ensure_directories(self):
        """إنشاء الهيكل التنظيمي للملفات إذا لم يكن موجوداً"""
        for path in [self.backtest_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. Historical Data Management (إدارة البيانات التاريخية)
    # =========================================================================
    def list_available_datasets(self) -> List[Dict[str, Any]]:
        """
        مسح المجلدات لعرض الملفات المتاحة للاختبار في الواجهة.
        """
        datasets = []
        # البحث عن ملفات Parquet و CSV
        extensions = ['*.parquet', '*.csv']
        files = []
        for ext in extensions:
            files.extend(self.backtest_dir.glob(ext))
            
        for f in files:
            stats = f.stat()
            datasets.append({
                "name": f.name,
                "path": str(f),
                "size_mb": round(stats.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "type": f.suffix.upper().replace('.', '')
            })
        return datasets

    def load_dataset_async(self, file_name: str):
        """
        تحميل ملف بيانات ضخم في الخلفية (لمنع تجميد الواجهة).
        """
        file_path = self.backtest_dir / file_name
        if not file_path.exists():
            self.load_failed.emit(file_name, "File not found")
            return

        logger_sink.log_system_event("DataManager", "INFO", f"⏳ Loading dataset: {file_name}...")

        # تفويض المهمة لمدير المهام (Workers)
        task_manager.start_task(
            self._worker_load_data,
            file_path,
            on_result=lambda df: self._on_data_loaded(file_name, df),
            on_error=lambda err: self._on_load_error(file_name, err)
        )

    def _worker_load_data(self, file_path: Path) -> pd.DataFrame:
        """
        الكود الذي يعمل داخل الخيط الخلفي (Worker Thread).
        """
        # Forensic Check: التحقق من الحجم قبل التحميل
        file_size = file_path.stat().st_size
        if file_size > 2 * 1024 * 1024 * 1024: # 2 GB Limit
            raise Exception("File too large for direct memory loading. Use chunking.")

        if file_path.suffix == '.parquet':
            df = pd.read_parquet(file_path)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path, parse_dates=True)
        else:
            raise Exception("Unsupported file format")

        # Forensic Check: التأكد من وجود الأعمدة الحيوية
        required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        # تحويل أسماء الأعمدة للصغيرة للمقارنة
        df.columns = [c.lower() for c in df.columns]
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise Exception(f"Corrupted Dataset. Missing critical columns: {missing}")

        return df

    def _on_data_loaded(self, name: str, df: pd.DataFrame):
        """استقبال النتيجة في الخيط الرئيسي"""
        logger_sink.log_system_event("DataManager", "SUCCESS", f"✅ Dataset loaded: {name} ({len(df)} rows)")
        self.data_loaded.emit(name, df)

    def _on_load_error(self, name: str, error_tuple: tuple):
        """معالجة الخطأ"""
        error_msg = str(error_tuple[1])
        logger_sink.log_system_event("DataManager", "ERROR", f"❌ Failed to load {name}: {error_msg}")
        self.load_failed.emit(name, error_msg)

    # =========================================================================
    # 2. Forensic Archiving (الأرشفة الجنائية)
    # =========================================================================
    def save_session_snapshot(self):
        """
        إنشاء "صورة نظام" (System Snapshot) فورية.
        تحفظ: السجلات، الصندوق الأسود من StreamHandler، وحالة StateStore.
        تستخدم عند الإغلاق أو عند حدوث خطأ كارثي.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = self.logs_dir / f"session_{timestamp}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        logger_sink.log_system_event("DataManager", "WARNING", f"💾 Creating Forensic Snapshot in: {snapshot_dir}")

        task_manager.start_task(
            self._worker_save_snapshot,
            snapshot_dir,
            on_finished=lambda: self.export_completed.emit(str(snapshot_dir))
        )

    def _worker_save_snapshot(self, folder: Path):
        """تنفيذ الحفظ في الخلفية"""
        
        # 1. تفريغ الصندوق الأسود (البيانات الخام الأخيرة)
        raw_data = stream_handler.dump_blackbox()
        raw_df = pd.DataFrame(raw_data, columns=['timestamp', 'ticker', 'price', 'volume'])
        raw_df.to_csv(folder / "blackbox_stream.csv", index=False)

        # 2. حفظ سجل الأحداث الجنائي (Audit Trail)
        # نحتاج الوصول لـ StateStore لجلب السجل (يجب استيراده داخل الدالة لتجنب Circular Import إذا أمكن، 
        # أو الاعتماد على الاستيراد العلوي)
        from ui.core.state_store import state_store 
        history = state_store.get_history()
        with open(folder / "state_audit.json", "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

        # 3. حفظ ملف checksum للأمان
        self._generate_checksum(folder / "blackbox_stream.csv")

    def _generate_checksum(self, file_path: Path):
        """إنشاء بصمة رقمية للملف لضمان عدم التلاعب به لاحقاً"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksum_file = file_path.with_suffix('.sha256')
        with open(checksum_file, "w") as f:
            f.write(sha256_hash.hexdigest())

# Global Accessor
data_manager = AlphaDataManager.get_instance()