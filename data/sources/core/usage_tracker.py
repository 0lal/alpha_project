import os
import sqlite3
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any

# استيراد مدير المفاتيح لمعرفة الحدود القصوى
try:
    from inventory.key_loader import key_loader
    from audit.logger_service import audit_logger
except ImportError:
    key_loader = None
    audit_logger = None

# إعداد السجل
logger = logging.getLogger("Alpha.Core.UsageTracker")

class APIUsageTracker:
    """
    المحاسب المالي للموارد (Resource Accountant).
    
    المهام الجنائية:
    1. تتبع دقيق لكل "توكن" أو "طلب" يخرج من النظام.
    2. الحفاظ على سجل دائم (Persistent State) لا يمحى بإعادة التشغيل.
    3. تطبيق منطق "التصفير" (Reset Logic) بناءً على توقيت المزود (ليس توقيت جهازك).
    """

    DB_PATH = "audit/api_state.db"

    def __init__(self):
        """
        تهيئة المحاسب وبناء قاعدة البيانات إذا لم تكن موجودة.
        """
        self._lock = threading.Lock()
        self._ensure_db_ready()

    def check_quota_status(self, provider: str, key_alias: str = "default") -> Tuple[str, float, str]:
        """
        فحص الحالة المالية للمفتاح قبل استخدامه.
        
        الإرجاع:
        - Status: 'OK', 'WARNING', 'CRITICAL', 'BLOCKED'
        - Usage Percent: 0.0 to 1.0
        - Message: رسالة توضيحية للواجهة.
        """
        # 1. جلب الحدود القصوى من ملف التكوين
        config = self._get_config(provider)
        if not config:
            return "OK", 0.0, "Unlimited (No Config)"

        # البحث عن الحدود (يومية أو شهرية)
        limits = config.get("tier_limits", {}) or config.get("usage_limits", {})
        
        limit_day = limits.get("requests_per_day", 0)
        limit_month = limits.get("requests_per_month", 0)
        limit_month_hard = limits.get("requests_per_month_hard_limit", 0)
        
        # نستخدم الحد الأكبر الموجود (الأولوية للشهري إذا وجد، ثم اليومي)
        max_limit = limit_month_hard or limit_month or limit_day
        
        if max_limit == 0:
            return "OK", 0.0, "Unlimited"

        # 2. جلب الاستهلاك الحالي من قاعدة البيانات
        current_usage, last_reset = self._get_db_usage(provider, key_alias)

        # 3. هل حان وقت التصفير؟ (Reset Logic)
        reset_strategy = limits.get("reset_strategy", "utc_midnight")
        if self._should_reset(last_reset, reset_strategy):
            self._reset_usage(provider, key_alias)
            current_usage = 0

        # 4. حساب النسبة واتخاذ القرار
        usage_pct = current_usage / max_limit
        
        if usage_pct >= 1.0:
            return "BLOCKED", usage_pct, f"Quota Exceeded ({current_usage}/{max_limit})"
        elif usage_pct >= 0.95:
            return "CRITICAL", usage_pct, f"Quota Critical ({current_usage}/{max_limit})"
        elif usage_pct >= 0.80:
            return "WARNING", usage_pct, f"Quota Low ({current_usage}/{max_limit})"
        
        return "OK", usage_pct, f"Healthy ({current_usage}/{max_limit})"

    def increment_usage(self, provider: str, key_alias: str = "default", cost: int = 1):
        """
        خصم الرصيد. يتم استدعاؤها بعد نجاح الطلب.
        """
        with self._lock:
            try:
                with sqlite3.connect(self.DB_PATH) as conn:
                    cursor = conn.cursor()
                    # التأكد من وجود السجل أو إنشاؤه
                    cursor.execute("""
                        INSERT OR IGNORE INTO usage_ledger (provider, key_alias, current_usage, last_updated, last_reset)
                        VALUES (?, ?, 0, ?, ?)
                    """, (provider, key_alias, datetime.utcnow(), datetime.utcnow()))
                    
                    # تحديث العداد
                    cursor.execute("""
                        UPDATE usage_ledger 
                        SET current_usage = current_usage + ?, 
                            last_updated = ?
                        WHERE provider = ? AND key_alias = ?
                    """, (cost, datetime.utcnow(), provider, key_alias))
                    conn.commit()
            except Exception as e:
                logger.error(f"❌ Failed to update ledger: {e}")

    def get_all_stats(self) -> Dict[str, Any]:
        """
        تقرير شامل للواجهة (Dashboard API).
        يعيد حالة كل المفاتيح لعرضها في UI.
        """
        stats = {}
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM usage_ledger")
                rows = cursor.fetchall()
                for row in rows:
                    stats[f"{row['provider']}_{row['key_alias']}"] = dict(row)
        except Exception:
            pass
        return stats

    def _should_reset(self, last_reset_str: str, strategy: str) -> bool:
        """
        منطق التصفير الذكي.
        """
        if not last_reset_str:
            return True
            
        last_reset = datetime.fromisoformat(last_reset_str)
        now = datetime.utcnow()

        if strategy == "utc_midnight":
            # هل نحن في يوم جديد مقارنة بآخر تصفير؟
            return now.date() > last_reset.date()
            
        elif strategy == "monthly_billing_date" or strategy == "monthly_first_day":
            # هل نحن في شهر جديد؟
            return (now.year > last_reset.year) or (now.month > last_reset.month)
            
        elif strategy == "rolling_24h":
            # هل مرت 24 ساعة؟
            return (now - last_reset) > timedelta(hours=24)

        return False

    def _reset_usage(self, provider: str, key_alias: str):
        """
        تصفير العداد لبداية دورة جديدة.
        """
        with self._lock:
            try:
                with sqlite3.connect(self.DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE usage_ledger 
                        SET current_usage = 0, 
                            last_reset = ?
                        WHERE provider = ? AND key_alias = ?
                    """, (datetime.utcnow(), provider, key_alias))
                    conn.commit()
                
                if audit_logger:
                    audit_logger.log_decision(
                        "USAGE_TRACKER", "QUOTA_RESET", f"Reset quota for {provider}", 
                        confidence=1.0
                    )
            except Exception as e:
                logger.error(f"❌ Failed to reset quota: {e}")

    def _get_db_usage(self, provider: str, key_alias: str) -> Tuple[int, str]:
        """
        قراءة مباشرة من قاعدة البيانات.
        """
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT current_usage, last_reset FROM usage_ledger
                    WHERE provider = ? AND key_alias = ?
                """, (provider, key_alias))
                row = cursor.fetchone()
                if row:
                    return row[0], row[1]
        except Exception:
            pass
        return 0, datetime.utcnow().isoformat()

    def _get_config(self, provider: str) -> dict:
        if key_loader:
            return key_loader.get_config(provider) or {}
        return {}

    def _ensure_db_ready(self):
        """
        إنشاء جدول المحاسبة إذا لم يكن موجوداً.
        """
        try:
            os.makedirs("audit", exist_ok=True)
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usage_ledger (
                        provider TEXT NOT NULL,
                        key_alias TEXT NOT NULL DEFAULT 'default',
                        current_usage INTEGER DEFAULT 0,
                        last_updated TIMESTAMP,
                        last_reset TIMESTAMP,
                        PRIMARY KEY (provider, key_alias)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.critical(f"❌ FATAL: Cannot initialize Usage DB: {e}")

# نسخة مفردة (Singleton)
usage_tracker = APIUsageTracker()