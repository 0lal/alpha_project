import os
import sys
import logging

# --- المكتبة الخارجية (نقطة الفشل المحتملة) ---
# التنبؤ بالمشكلة: المستخدم قد لا يملك مكتبة psutil مثبتة.
# الحل: استخدام try-import لمنع انهيار البرنامج، والعمل بوضع "العمى الجزئي" (Dummy Mode).
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

class HardwareUtils:
    """
    مراقب الصحة الحيوية للنظام (System Vitals Monitor).
    
    المهمة الجنائية:
    1. الكشف المبكر عن تسريب الذاكرة (Memory Leaks) داخل البرنامج نفسه.
    2. مراقبة ضغط النظام العام (System Load) لتجنب التنفيذ في بيئة مخنوقة.
    3. توفير بيانات آمنة حتى في حال غياب المكتبات المساعدة.
    """

    # تهيئة المتغيرات لمرة واحدة (Singleton-like access via static methods)
    _process = None
    
    @staticmethod
    def _get_process():
        """
        الحصول على مقبض العملية الحالية (Current Process Handle).
        يتم استدعاؤه مرة واحدة فقط لتحسين الأداء (Lazy Initialization).
        """
        if HardwareUtils._process is None and _HAS_PSUTIL:
            try:
                HardwareUtils._process = psutil.Process(os.getpid())
            except Exception as e:
                logging.error(f"Failed to attach to process: {e}")
        return HardwareUtils._process

    @staticmethod
    def is_supported() -> bool:
        """هل المراقبة الحقيقية متاحة؟"""
        return _HAS_PSUTIL

    @staticmethod
    def get_cpu_usage() -> float:
        """
        نسبة استهلاك المعالج الكلية (System-wide CPU %).
        
        خدعة برمجية:
        استخدام interval=None يجعل الدالة غير حاصرة (Non-blocking).
        هي تعيد الاستهلاك منذ آخر استدعاء، مما يجعلها مثالية لتحديث الواجهة (GUI)
        دون التسبب في تجميدها.
        """
        if not _HAS_PSUTIL:
            return 0.0
        
        try:
            # interval=None is crucial here to prevent UI freezing
            return psutil.cpu_percent(interval=None)
        except Exception:
            return 0.0

    @staticmethod
    def get_ram_usage_percent() -> float:
        """
        نسبة استهلاك الذاكرة الكلية للنظام.
        """
        if not _HAS_PSUTIL:
            return 0.0
        
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    @staticmethod
    def get_app_ram_usage_mb() -> float:
        """
        التدقيق الجنائي: كم يستهلك *هذا البرنامج* تحديداً من الذاكرة؟
        
        الأهمية:
        إذا كان هذا الرقم يزداد باستمرار دون توقف (مثلاً بدأ 50MB وأصبح 2GB)،
        فهذا دليل قاطع على وجود Memory Leak في الكود ويجب إعادة تشغيل البوت.
        """
        proc = HardwareUtils._get_process()
        if not proc:
            return 0.0
        
        try:
            # RSS (Resident Set Size) هو الذاكرة الفيزيائية الحقيقية المستخدمة
            mem_info = proc.memory_info()
            return mem_info.rss / (1024 * 1024) # التحويل من بايت إلى ميجابايت
        except Exception:
            return 0.0

    @staticmethod
    def get_network_io() -> tuple[float, float]:
        """
        مراقبة نشاط الشبكة (اختياري).
        Returns: (bytes_sent, bytes_recv)
        """
        if not _HAS_PSUTIL:
            return (0.0, 0.0)
        
        try:
            net = psutil.net_io_counters()
            return (net.bytes_sent, net.bytes_recv)
        except Exception:
            return (0.0, 0.0)

    @staticmethod
    def check_health_status() -> tuple[str, str]:
        """
        تشخيص حالة النظام (Health Check).
        يعيد: (الحالة, اللون المقترح)
        
        القواعد:
        - CPU > 90% -> خطر (أحمر)
        - RAM > 90% -> خطر (أحمر)
        - CPU/RAM > 70% -> تحذير (أصفر)
        - أقل من ذلك -> ممتاز (أخضر)
        """
        cpu = HardwareUtils.get_cpu_usage()
        ram = HardwareUtils.get_ram_usage_percent()
        
        if cpu > 90 or ram > 90:
            return "CRITICAL", "#ff5555" # Red
        elif cpu > 70 or ram > 80:
            return "STRESSED", "#ffb86c" # Orange/Yellow
        else:
            return "HEALTHY", "#50fa7b"  # Green