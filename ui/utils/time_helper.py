import time
from datetime import datetime, timezone, timedelta
from typing import Union, Optional

class TimeUtils:
    """
    مراقب الزمن السيادي (Sovereign Timekeeper).
    
    المهمة الجنائية:
    1. توحيد الزمن: استخدام UTC Milliseconds كمعيار داخلي مطلق (Absolute Truth).
    2. كشف التأخير: حساب الفارق بين وقت البورصة ووقت الاستلام (Network Latency).
    3. العرض البشري: تحويل الأرقام الجامدة إلى توقيت محلي للمستخدم.
    
    تحذير:
    لا تستخدم datetime.now() بدون timezone في الكود الأساسي أبداً. 
    يجب دائماً استخدام الـ UTC للحسابات، والـ Local للعرض فقط.
    """

    # ثوابت التحويل
    MS_IN_SEC = 1000
    SEC_IN_MIN = 60
    MIN_IN_HOUR = 60
    
    @staticmethod
    def now_ms() -> int:
        """
        الحقيقة المطلقة: الوقت الحالي بتوقيت UTC بالمللي ثانية.
        يستخدم هذا الرقم في جميع الطوابع الزمنية للسجلات والأوامر.
        
        Why Integer?
        Float precision issues can cause micro-second drift. Int is exact.
        """
        return int(time.time() * TimeUtils.MS_IN_SEC)

    @staticmethod
    def get_local_now_str(fmt: str = "%H:%M:%S") -> str:
        """للعرض في شريط الحالة (الساعة التي يراها المستخدم)"""
        return datetime.now().strftime(fmt)

    @staticmethod
    def ts_to_str(ts_ms: Union[int, float, None], fmt: str = "%Y-%m-%d %H:%M:%S", local: bool = True) -> str:
        """
        تحويل الطابع الزمني (Unix Timestamp) إلى نص مقروء.
        
        الذكاء الجنائي:
        يكتشف تلقائياً ما إذا كان المدخل بالثواني (Seconds) أو الملي ثانية (Milliseconds).
        إذا كان الرقم صغيراً جداً (< 10 مليار)، فهو بالثواني ويتم تصحيحه.
        """
        if ts_ms is None or ts_ms == 0:
            return "--:--:--"

        try:
            val = float(ts_ms)
            
            # التصحيح التلقائي (Heuristic check for Seconds vs Milliseconds)
            # عام 2286 هو الحد الفاصل لـ 10 أرقام بالثواني، لذا هذا الفحص آمن لقرنين قادمين
            if val < 10_000_000_000: 
                val *= 1000  # Convert seconds to ms

            # إنشاء كائن الوقت (UTC Aware)
            dt_utc = datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)

            if local:
                # التحويل للتوقيت المحلي للمستخدم
                dt_local = dt_utc.astimezone()
                return dt_local.strftime(fmt)
            else:
                return dt_utc.strftime(fmt)

        except Exception:
            return "Invalid Time"

    @staticmethod
    def format_latency(server_ts: int) -> str:
        """
        حساب وعرض "عمر" البيانات (Data Age).
        
        أهمية جنائية:
        إذا كان الفارق كبيراً (مثلاً > 500ms)، فهذا يعني أن الشبكة بطيئة 
        أو أن البيانات قديمة، ويجب إيقاف التداول الآلي فوراً.
        """
        if not server_ts:
            return "N/A"
            
        now = TimeUtils.now_ms()
        diff = now - server_ts
        
        # تلوين التحذير (نصياً هنا، ويتم تلوينه في الواجهة)
        # Latency < 200ms : Excellent
        # Latency < 500ms : Good
        # Latency > 1000ms: DANGER
        
        if diff < 0:
            # حالة نادرة: ساعة السيرفر تسبق ساعة جهازك (Clock Skew)
            return f"Fut.{abs(diff)}ms" 
        
        return f"{diff}ms"

    @staticmethod
    def get_time_ago(ts_ms: int) -> str:
        """
        عرض الوقت بصيغة نسبية (Humanized).
        مثال: "Just now", "2m ago", "1h ago".
        """
        if not ts_ms: return ""
        
        now = TimeUtils.now_ms()
        diff_sec = (now - ts_ms) / 1000
        
        if diff_sec < 5:
            return "Just now"
        elif diff_sec < 60:
            return f"{int(diff_sec)}s ago"
        elif diff_sec < 3600:
            return f"{int(diff_sec // 60)}m ago"
        elif diff_sec < 86400:
            return f"{int(diff_sec // 3600)}h ago"
        else:
            return f"{int(diff_sec // 86400)}d ago"

    @staticmethod
    def is_fresh_data(ts_ms: int, tolerance_ms: int = 5000) -> bool:
        """
        فحص سلامة البيانات.
        هل البيانات حديثة بما يكفي لاتخاذ قرار تداول؟
        """
        if not ts_ms: return False
        return (TimeUtils.now_ms() - ts_ms) <= tolerance_ms

    @staticmethod
    def format_duration(seconds: int) -> str:
        """
        تنسيق المدة الزمنية (لعداد تشغيل البرنامج Uptime).
        125 -> 02:05
        3700 -> 01:01:40
        """
        if seconds is None: return "00:00"
        
        try:
            sec = int(seconds)
            h = sec // 3600
            m = (sec % 3600) // 60
            s = sec % 60
            
            if h > 0:
                return f"{h:02}:{m:02}:{s:02}"
            else:
                return f"{m:02}:{s:02}"
        except:
            return "00:00"

    @staticmethod
    def get_market_session() -> str:
        """
        تحديد جلسة السوق الحالية (اختياري للأسواق العالمية).
        (Asia, London, New York) بناءً على توقيت UTC.
        """
        current_hour = datetime.now(timezone.utc).hour
        
        # تقسيم تقريبي للجلسات (UTC)
        if 0 <= current_hour < 8:
            return "ASIA"
        elif 8 <= current_hour < 13:
            return "LONDON"
        elif 13 <= current_hour < 21:
            return "NY"
        else:
            return "CLOSE"