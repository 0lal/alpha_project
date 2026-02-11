import time
import logging
from typing import Optional, Tuple, Dict
from datetime import datetime

# استيراد التبعيات التي بنيناها سابقاً
try:
    from cache.redis_buffer import redis_client
    from inventory.key_loader import key_loader
    from audit.logger_service import audit_logger
except ImportError:
    # وضعية الطوارئ (للتشغيل المنفصل)
    redis_client = None
    key_loader = None
    audit_logger = None

# إعداد السجل
logger = logging.getLogger("Alpha.Core.RateLimiter")

class TrafficController:
    """
    مراقب حركة المرور (Rate Limiting Enforcer).
    
    الهدف الجنائي:
    1. تطبيق قوانين الاستهلاك بصرامة (بالثانية، بالدقيقة، باليوم).
    2. منع "هجوم الحرمان من الخدمة الذاتي" (Self-DoS) عن طريق تنظيم التزامن.
    3. إدارة العقوبات (Cooldowns) للمفاتيح التي تتجاوز الحدود.
    """

    def __init__(self):
        """
        تهيئة المراقب.
        """
        # ذاكرة محلية احتياطية في حال فشل Redis (Fail-over Memory)
        self._local_memory: Dict[str, float] = {}

    def check_eligibility(self, provider: str, key_alias: str = "default") -> Tuple[bool, str]:
        """
        هل يُسمح لهذا المفتاح بالمرور الآن؟ (The Gatekeeper).
        
        المعاملات:
        - provider: اسم الخدمة (مثال: 'alpha_vantage').
        - key_alias: المعرف الداخلي للمفتاح (في حال التدوير).
        
        الإرجاع:
        - (True, "OK"): مسموح.
        - (False, "Reason"): ممنوع، مع ذكر السبب للسجل الجنائي.
        """
        # 1. جلب القوانين من ملف التكوين (Load Rules)
        config = self._get_provider_config(provider)
        if not config:
            # إذا لم نجد تكويناً، نفترض الأسوأ ونسمح بحد أدنى للأمان
            return True, "NO_CONFIG_FOUND_DEFAULT_PASS"

        limits = config.get("tier_limits", {}) or config.get("usage_limits", {}) or config.get("rate_limits", {})
        
        # 2. فحص الحظر المؤقت (Penalty Box Check)
        if self._is_in_penalty_box(provider, key_alias):
            return False, "IN_PENALTY_BOX"

        # 3. فحص التزامن اللحظي (Burst / Concurrency Check)
        # مثال: CryptoPanic يسمح بـ 2 طلب في الثانية فقط
        rps_limit = limits.get("requests_per_second", limits.get("requests_per_second_burst", 0))
        if rps_limit > 0:
            allowed = self._check_window(provider, key_alias, "sec", rps_limit, 1)
            if not allowed:
                return False, "RPS_LIMIT_EXCEEDED"

        # 4. فحص الحد الدقيقي (RPM Check)
        rpm_limit = limits.get("requests_per_minute", 0)
        if rpm_limit > 0:
            allowed = self._check_window(provider, key_alias, "min", rpm_limit, 60)
            if not allowed:
                return False, "RPM_LIMIT_EXCEEDED"

        # 5. فحص الحد اليومي (Daily Quota Check)
        rpd_limit = limits.get("requests_per_day", 0)
        if rpd_limit > 0:
            allowed = self._check_window(provider, key_alias, "day", rpd_limit, 86400)
            if not allowed:
                return False, "DAILY_QUOTA_EXCEEDED"

        return True, "GRANTED"

    def report_violation(self, provider: str, error_code: int):
        """
        الإبلاغ عن مخالفة (مثال: تلقينا 429 من المزود رغم أننا حسبنا صح).
        هذا يعني أن حساباتنا غير متزامنة مع المصدر، ويجب تفعيل عقوبة.
        """
        if error_code == 429:
            self._activate_penalty(provider, duration_sec=60)
            if audit_logger:
                audit_logger.log_security_event("RATE_LIMIT_VIOLATION", f"Provider {provider} returned 429. Penalty activated.")

    def _check_window(self, provider: str, key: str, window_type: str, limit: int, window_sec: int) -> bool:
        """
        فحص نافذة زمنية محددة باستخدام Redis Atomic Counter.
        """
        # تكوين مفتاح فريد: ALPHA:RATE:alpha_vantage:default:min
        redis_key = f"ALPHA:RATE:{provider}:{key}:{window_type}"
        
        if redis_client and redis_client._is_connected:
            # استخدام Redis (الدقيق والمشترك بين العمليات)
            return redis_client.check_and_increment_rate_limit(key_id=redis_key, limit=limit, window_seconds=window_sec)
        else:
            # استخدام الذاكرة المحلية (أقل دقة لكن يفي بالغرض في الطوارئ)
            return self._check_local_window(redis_key, limit, window_sec)

    def _check_local_window(self, unique_id: str, limit: int, window_sec: int) -> bool:
        """
        خوارزمية Token Bucket مبسطة للذاكرة المحلية.
        """
        now = time.time()
        # الهيكل: { unique_id: [timestamp_1, timestamp_2, ...] }
        history = self._local_memory.get(unique_id, [])
        
        # تنظيف السجلات القديمة التي خرجت من النافذة الزمنية
        valid_history = [t for t in history if now - t < window_sec]
        
        if len(valid_history) >= limit:
            return False
        
        # تسجيل الطلب الجديد
        valid_history.append(now)
        self._local_memory[unique_id] = valid_history
        return True

    def _get_provider_config(self, provider: str) -> dict:
        """
        جلب الإعدادات من KeyLoader.
        """
        if key_loader:
            return key_loader.get_config(provider) or {}
        return {}

    def _is_in_penalty_box(self, provider: str, key: str) -> bool:
        """
        هل المفتاح معاقب حالياً؟
        """
        penalty_key = f"ALPHA:PENALTY:{provider}:{key}"
        if redis_client and redis_client._is_connected:
            return redis_client.client.exists(penalty_key) > 0
        return False

    def _activate_penalty(self, provider: str, duration_sec: int):
        """
        تفعيل وضع العقوبة (Sinner's Bench).
        """
        penalty_key = f"ALPHA:PENALTY:{provider}:default"
        if redis_client and redis_client._is_connected:
            redis_client.client.setex(penalty_key, duration_sec, "BANNED")
            logger.warning(f"🚫 {provider} is placed in PENALTY BOX for {duration_sec}s")

# نسخة مفردة (Singleton)
rate_limiter = TrafficController()