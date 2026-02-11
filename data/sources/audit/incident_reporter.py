import os
import json
import sys
import traceback
import platform
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

# استيراد نظام التسجيل المركزي الذي بنيناه سابقاً
# تأكد من أن logger_service.py موجود في المجلد الصحيح
try:
    from audit.logger_service import audit_logger
except ImportError:
    # احتياط في حالة تشغيل الملف بشكل منفصل للاختبار
    logging.basicConfig(level=logging.INFO)
    audit_logger = None

class IncidentReporter:
    """
    نظام إدارة الحوادث والكوارث (Incident Management System).
    
    المهام الجنائية:
    1. التقاط سياق الخطأ: ليس فقط "ماذا حدث"، بل "أين" و "متى" و "حالة الذاكرة".
    2. منع الإزعاج (Deduplication): إذا تكرر نفس الخطأ 100 مرة في الثانية، نرسل تنبيهاً واحداً فقط.
    3. التصعيد الذكي: الأخطاء البسيطة تسجل فقط، الكوارث ترسل SMS/Telegram فوراً.
    """

    # مستويات الخطورة المالية
    SEVERITY_INFO = "INFO"         # معلومة عادية
    SEVERITY_WARNING = "WARNING"   # تحذير (مثل: بطء في الشبكة)
    SEVERITY_CRITICAL = "CRITICAL" # خطر (مثل: فشل صفقة، انقطاع بيانات)
    SEVERITY_FATAL = "FATAL"       # كارثة (مثل: انهيار النظام، اختراق)

    def __init__(self):
        """
        تهيئة النظام وتجهيز مخزن التقارير.
        """
        self._lock = threading.Lock()
        
        # سجل التكرار لمنع إغراق المستخدم بالتنبيهات (Throttling)
        # الصيغة: { "error_hash": last_alert_timestamp }
        self._alert_history: Dict[str, float] = {}
        
        # فترة الصمت الإجباري بين التنبيهات المتطابقة (بالثواني)
        self.suppression_window = 60.0 
        
        # قائمة القنوات الخارجية (مثل Telegram, Make.com)
        # يتم حقنها لاحقاً لفك الارتباط (Decoupling)
        self._external_channels: List[Callable[[Dict], None]] = []

        # معلومات النظام الثابتة (للتوثيق الجنائي)
        self._system_info = {
            "os": platform.system(),
            "release": platform.release(),
            "python_version": sys.version.split()[0],
            "node": platform.node()
        }

    def register_alert_channel(self, callback_function: Callable[[Dict], None]):
        """
        تسجيل قناة تنبيه خارجية (مثل دالة إرسال التيليجرام).
        يسمح للنظام بالتوسع دون تعديل الكود الأساسي.
        """
        with self._lock:
            self._external_channels.append(callback_function)

    def report(self, title: str, severity: str, details: str, 
               payload: Optional[Dict] = None, exception: Optional[Exception] = None):
        """
        الإبلاغ عن حادثة جديدة.
        
        المعاملات:
        - title: عنوان مختصر للمشكلة.
        - severity: مستوى الخطورة (INFO, WARNING, CRITICAL, FATAL).
        - details: شرح نصي للمشكلة.
        - payload: بيانات إضافية (مثل محتوى الصفقة الفاشلة).
        - exception: كائن الخطأ البرمجي (إذا وجد) لاستخراج الـ Stack Trace.
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # 1. استخراج الأدلة الجنائية (Forensic Context)
            stack_trace = None
            if exception:
                # تحويل الخطأ إلى نص كامل يوضح موقع الخطأ في الكود
                stack_trace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            elif severity in [self.SEVERITY_CRITICAL, self.SEVERITY_FATAL]:
                # حتى لو لم يكن هناك Exception، نحتاج لمعرفة من استدعى هذه الدالة
                stack_trace = "".join(traceback.format_stack()[:-1])

            # بناء تقرير الحادثة الموحد
            incident_report = {
                "incident_id": self._generate_incident_id(title, timestamp),
                "timestamp": timestamp,
                "title": title,
                "severity": severity,
                "description": details,
                "system_context": self._system_info,
                "technical_context": {
                    "stack_trace": stack_trace,
                    "payload_snapshot": self._sanitize_payload(payload)
                }
            }

            # 2. التسجيل المحلي (Local Logging)
            self._log_locally(incident_report)

            # 3. اتخاذ قرار التنبيه (Alerting Decision)
            if self._should_alert(incident_report):
                self._dispatch_alert(incident_report)

        except Exception as e:
            # في أسوأ الظروف، إذا فشل نظام التبليغ نفسه، نطبع على الشاشة
            print(f"!!! CRITICAL FAILURE IN INCIDENT REPORTER !!!: {e}")
            traceback.print_exc()

    def _should_alert(self, report: Dict) -> bool:
        """
        المنطق الذكي: هل يستحق هذا الحادث إيقاظ المستخدم؟
        """
        severity = report["severity"]
        
        # المعلومات العادية لا تحتاج تنبيه فوري
        if severity == self.SEVERITY_INFO:
            return False

        # التحقق من التكرار (Deduplication)
        incident_hash = f"{report['title']}:{report['description']}"
        current_time = time.time()
        
        with self._lock:
            last_time = self._alert_history.get(incident_hash, 0)
            
            # إذا مر وقت كافٍ منذ آخر تنبيه لنفس الخطأ، أو إذا كان الخطأ قاتلاً (FATAL) نرسل دائماً
            if (current_time - last_time > self.suppression_window) or (severity == self.SEVERITY_FATAL):
                self._alert_history[incident_hash] = current_time
                return True
            
        return False

    def _dispatch_alert(self, report: Dict):
        """
        إرسال التقرير لكل القنوات المسجلة (Telegram, Email, etc).
        """
        # تجهيز رسالة مختصرة للتنبيهات
        alert_summary = {
            "title": f"[{report['severity']}] {report['title']}",
            "body": f"{report['description']}\nTime: {report['timestamp']}",
            "severity": report['severity']
        }

        # تشغيل القنوات في خيط منفصل لعدم تعطيل النظام الرئيسي
        def _notify_all():
            for channel in self._external_channels:
                try:
                    channel(alert_summary)
                except Exception as e:
                    print(f"Failed to send alert via channel: {e}")

        threading.Thread(target=_notify_all, daemon=True).start()

    def _log_locally(self, report: Dict):
        """
        الحفظ في ملفات السجلات باستخدام LoggerService.
        """
        if audit_logger:
            severity = report["severity"]
            log_msg = json.dumps(report, ensure_ascii=False)
            
            if severity == self.SEVERITY_FATAL:
                audit_logger.log_error("SYSTEM_FATAL", f"FATAL INCIDENT: {report['title']}", report['technical_context']['stack_trace'])
                # حفظ نسخة JSON مستقلة للكوارث
                self._save_crash_dump(report)
                
            elif severity == self.SEVERITY_CRITICAL:
                audit_logger.log_error("SYSTEM_CRITICAL", log_msg)
            else:
                audit_logger.log_anomaly("INCIDENT", report['title'], severity)

    def _save_crash_dump(self, report: Dict):
        """
        إنشاء ملف Crash Dump منفصل عند الانهيار التام.
        """
        try:
            dump_dir = "audit/logs/crash_dumps"
            os.makedirs(dump_dir, exist_ok=True)
            filename = f"{dump_dir}/crash_{report['incident_id']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _sanitize_payload(self, payload: Any) -> Any:
        """
        تنظيف البيانات من المفاتيح السرية قبل إضافتها للتقرير.
        """
        if not payload:
            return None
        # نستخدم دالة التنظيف الموجودة في audit_logger إذا توفرت
        if audit_logger:
            return audit_logger._sanitize(payload)
        return str(payload) # نسخة مبسطة

    def _generate_incident_id(self, title: str, timestamp: str) -> str:
        """
        توليد رقم مرجعي فريد للحادثة.
        """
        import hashlib
        raw = f"{title}{timestamp}{platform.node()}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

# نسخة مفردة (Singleton) للاستخدام العام
incident_manager = IncidentReporter()