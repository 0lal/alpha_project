import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import TimedRotatingFileHandler

# قفل لضمان عدم تداخل الكتابة من خيوط متعددة (Thread Safety)
_LOCK = threading.Lock()

class ForensicLogger:
    """
    نظام التوثيق الجنائي (Forensic Audit Logger).
    
    الهدف:
    توفير سجل غير قابل للإنكار لكل قرار، معلومة، أو خطأ يحدث داخل النظام المالي.
    يتم تقسيم السجلات إلى "مسارات" (Tracks) حسب نوع البيانات لسهولة التحليل.
    """

    def __init__(self, log_dir: str = "audit/logs"):
        """
        تهيئة النظام وإنشاء المجلدات الضرورية.
        """
        self.base_dir = os.path.abspath(log_dir)
        
        # تعريف مسارات السجلات المطلوبة جنائياً
        self.paths = {
            "decisions": os.path.join(self.base_dir, "decisions"),     # لماذا اتخذنا هذا القرار؟
            "anomalies": os.path.join(self.base_dir, "anomalies"),     # بيانات مشبوهة
            "raw_payloads": os.path.join(self.base_dir, "raw_payloads"), # البيانات الخام (الدليل المادي)
            "errors": os.path.join(self.base_dir, "errors"),           # الأخطاء التقنية
            "security": os.path.join(self.base_dir, "security")        # محاولات اختراق أو رفض وصول
        }

        # إنشاء المجلدات إذا لم تكن موجودة
        for path in self.paths.values():
            os.makedirs(path, exist_ok=True)

        # إعداد المسجلات (Loggers) لكل مسار
        self.loggers = {}
        self._setup_loggers()

    def _setup_loggers(self):
        """
        إعداد معالجات الملفات مع التدوير اليومي (Daily Rotation).
        كل ملف جديد يبدأ عند منتصف الليل.
        """
        for name, path in self.paths.items():
            logger = logging.getLogger(f"Alpha.Audit.{name}")
            logger.setLevel(logging.INFO)
            logger.propagate = False  # منع التكرار في السجلات العامة

            # منع إضافة معالجات مكررة إذا تم استدعاء الكلاس مرتين
            if not logger.handlers:
                # اسم الملف: decisions/2026-02-10.log
                file_path = os.path.join(path, "audit.log")
                
                # تدوير الملف كل يوم عند منتصف الليل، والاحتفاظ بآخر 30 يوم
                handler = TimedRotatingFileHandler(
                    file_path, when="midnight", interval=1, backupCount=30, encoding="utf-8"
                )
                
                # تنسيق الرسالة: JSON فقط لسهولة القراءة الآلية
                formatter = logging.Formatter('%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            
            self.loggers[name] = logger

    def log_decision(self, component: str, reason: str, action: str, 
                    previous_state: Any = None, new_state: Any = None, confidence: float = 1.0):
        """
        [سجل القرارات]
        يوثق "منطق" النظام. مثال: لماذا انتقلنا من Alpha Vantage إلى Twelve Data؟
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "DECISION",
            "component": component,
            "reason_code": reason,  # مثال: "QUOTA_EXCEEDED"
            "action_taken": action, # مثال: "SWITCH_PROVIDER"
            "context": {
                "before": previous_state,
                "after": new_state,
                "confidence_score": confidence
            }
        }
        self._write("decisions", entry)

    def log_raw_payload(self, provider: str, endpoint: str, payload: Dict, latency_ms: float):
        """
        [سجل الأدلة الخام]
        يسجل الرد الحرفي القادم من المصدر قبل أي تعديل.
        هام جداً لإثبات أن الخطأ من المصدر وليس من كود النظام.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "RAW_DATA",
            "provider": provider,
            "endpoint": endpoint,
            "latency_ms": latency_ms,
            "payload_snapshot": self._sanitize(payload)  # إزالة المفاتيح السرية
        }
        self._write("raw_payloads", entry)

    def log_anomaly(self, metric: str, value: Any, threshold: Any, severity: str = "WARNING"):
        """
        [سجل الشذوذ]
        يوثق البيانات التي رفضها النظام لأنها غير منطقية (Sanity Check Failure).
        مثال: السعر = 0، أو تغير 50% في ثانية.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "ANOMALY",
            "severity": severity,
            "metric": metric,
            "suspicious_value": value,
            "violated_threshold": threshold,
            "action": "DATA_REJECTED"
        }
        self._write("anomalies", entry)

    def log_security_event(self, event_type: str, details: str, ip_address: Optional[str] = None):
        """
        [سجل الأمن]
        يوثق محاولات الوصول غير المصرح به أو أخطاء المصادقة.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "SECURITY",
            "event": event_type,
            "details": details,
            "origin_ip": ip_address or "INTERNAL"
        }
        self._write("security", entry)

    def log_error(self, location: str, error_msg: str, traceback_str: Optional[str] = None):
        """
        [سجل الأخطاء التقنية]
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "ERROR",
            "location": location,
            "message": error_msg,
            "stack_trace": traceback_str
        }
        self._write("errors", entry)

    def _write(self, category: str, data: Dict):
        """
        كتابة السجل في الملف المناسب بشكل آمن ومتزامن.
        """
        try:
            # تحويل البيانات لنص JSON
            log_message = json.dumps(data, ensure_ascii=False)
            
            with _LOCK:
                if category in self.loggers:
                    self.loggers[category].info(log_message)
                else:
                    # في حالة طلب فئة غير موجودة، سجلها في الأخطاء
                    self.loggers["errors"].error(f"Unknown log category: {category} - Data: {log_message}")
                    
        except Exception as e:
            # الفشل الأخير: الطباعة على الشاشة إذا فشل كل شيء
            print(f"CRITICAL LOGGING FAILURE: {str(e)}")

    def _sanitize(self, data: Any) -> Any:
        """
        [الحماية] تنظيف البيانات من الأسرار قبل تسجيلها.
        تحذف أي مفتاح يحتوي على 'key', 'token', 'pass', 'secret'.
        """
        if isinstance(data, dict):
            clean_data = {}
            for k, v in data.items():
                key_lower = k.lower()
                if any(x in key_lower for x in ['api_key', 'secret', 'password', 'auth_token', 'access_token']):
                    clean_data[k] = "***REDACTED***"
                else:
                    clean_data[k] = self._sanitize(v)
            return clean_data
        elif isinstance(data, list):
            return [self._sanitize(item) for item in data]
        else:
            return data

# إنشاء نسخة مفردة (Singleton) للاستخدام المباشر في باقي النظام
audit_logger = ForensicLogger()