import sys
import traceback
import logging
from typing import Callable, Any, Optional
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

# استيراد نظام السجلات المركزي لتوثيق الجرائم البرمجية (الأخطاء)
from ui.core.logger_sink import logger_sink

# =============================================================================
# 1. Worker Signals (قنوات الاتصال)
# =============================================================================
class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    
    لماذا هذا الكلاس منفصل؟
    لأن QRunnable ليس QObject، فلا يمكنه إطلاق Signals مباشرة.
    نحتاج هذا "الوسيط" لنقل النتائج من الخلفية إلى الواجهة بسلام.
    """
    finished = pyqtSignal()                 # المهمة انتهت (نجاح أو فشل)
    error = pyqtSignal(tuple)               # حدث خطأ: (ex_type, value, traceback)
    result = pyqtSignal(object)             # النتيجة النهائية (أي نوع بيانات)
    progress = pyqtSignal(int)              # نسبة التقدم (0-100)
    status = pyqtSignal(str)                # رسالة نصية (مثلاً: "جارٍ التحميل...")

# =============================================================================
# 2. The Worker (العامل الكادح)
# =============================================================================
class Worker(QRunnable):
    """
    Worker thread wrapper.
    يقوم بتنفيذ أي دالة (Function) في خيط منفصل.
    
    Forensic Feature:
    يحتوي على "صندوق أسود" يلتقط أي انهيار (Crash) داخل الدالة
    ويرسله للواجهة بدلاً من إغلاق البرنامج بصمت.
    """

    def __init__(self, fn: Callable, *args, **kwargs):
        super(Worker, self).__init__()
        # تخزين الدالة والبيانات التي سنعمل عليها
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        # إنشاء قنوات الاتصال
        self.signals = WorkerSignals()
        
        # دعم callbacks مباشرة (اختياري)
        # نقوم بسحب الـ callbacks من الـ kwargs إذا وجدت لتجنب تمريرها للدالة الهدف
        self.kwargs['progress_callback'] = self.signals.progress
        self.kwargs['status_callback'] = self.signals.status

    @pyqtSlot()
    def run(self):
        """
        نقطة الدخول الرئيسية للخيط.
        """
        try:
            # محاولة تنفيذ المهمة الخطرة
            result = self.fn(*self.args, **self.kwargs)
        except:
            # 🚨 CRIME SCENE INVESTIGATION 🚨
            # في حال الفشل، لا نسمح للبرنامج بالانهيار.
            # نلتقط البصمات (Traceback) ونرسلها للمحقق (Logger).
            traceback.print_exc()
            ex_type, value = sys.exc_info()[:2]
            self.signals.error.emit((ex_type, value, traceback.format_exc()))
        else:
            # إذا نجحت العملية، نرسل الغنيمة (النتيجة)
            self.signals.result.emit(result)
        finally:
            # في كل الأحوال، نعلن انتهاء المهمة لتحرير الموارد
            self.signals.finished.emit()

# =============================================================================
# 3. The Task Manager (مدير المصنع)
# =============================================================================
class TaskManager(QObject):
    """
    The Global Thread Pool Manager.
    
    الوظيفة:
    يدير جيشاً من العمال (Workers). يضمن عدم استهلاك المعالج بالكامل.
    يوفر واجهة بسيطة لأي نافذة تريد تنفيذ مهمة في الخلفية.
    """
    
    _instance = None

    def __init__(self):
        super().__init__()
        if TaskManager._instance is not None:
            raise Exception("TaskManager is a Singleton!")
        
        self.threadpool = QThreadPool()
        
        # Forensic Optimization:
        # نترك نواة واحدة حرة دائماً لنظام التشغيل والواجهة الرسومية
        # لضمان عدم حدوث "System Lag" كامل.
        ideal_thread_count = self.threadpool.maxThreadCount()
        # self.threadpool.setMaxThreadCount(max(1, ideal_thread_count - 1)) 
        # (ملاحظة: تركتها افتراضية الآن للأداء الأقصى، لكن يمكن تفعيل السطر أعلاه للحذر)

        logger_sink.log_system_event(
            "TaskManager", "INFO", 
            f"⚙️ Worker Factory Initialized. Max Threads: {self.threadpool.maxThreadCount()}"
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance

    def start_task(self, 
                   task_func: Callable, 
                   *args, 
                   on_result: Optional[Callable] = None, 
                   on_error: Optional[Callable] = None, 
                   on_finished: Optional[Callable] = None,
                   on_progress: Optional[Callable] = None,
                   **kwargs):
        """
        الأمر المباشر لتشغيل مهمة.
        
        Parameters:
            task_func: الدالة المراد تشغيلها.
            on_result: دالة لاستقبال النتيجة عند النجاح.
            on_error: دالة لاستقبال تقرير الخطأ عند الفشل.
            on_finished: دالة تعمل دائماً عند الانتهاء (لإخفاء مؤشر التحميل مثلاً).
            *args, **kwargs: وسائط تمرر للدالة الأصلية.
        """
        
        # 1. تجنيد عامل جديد
        worker = Worker(task_func, *args, **kwargs)
        
        # 2. ربط قنوات الاتصال (Wiring)
        if on_result:
            worker.signals.result.connect(on_result)
        
        if on_error:
            worker.signals.error.connect(on_error)
        else:
            # Default Error Handler: Send to LoggerSink
            worker.signals.error.connect(self._default_error_handler)
            
        if on_finished:
            worker.signals.finished.connect(on_finished)
            
        if on_progress:
            worker.signals.progress.connect(on_progress)

        # 3. دفع العامل إلى المسبح
        self.threadpool.start(worker)

    def _default_error_handler(self, error_data: tuple):
        """معالج الأخطاء الافتراضي: يبلغ الشرطة (Logger)"""
        ex_type, value, tb = error_data
        # تنظيف شكل الخطأ للعرض
        logger_sink.log_system_event(
            "BackgroundWorker", "ERROR", 
            f"Task Failed: {value}\nTrace: {tb.splitlines()[-1]}" # عرض آخر سطر فقط في الملخص
        )

    def active_tasks_count(self) -> int:
        """لأغراض المراقبة: كم عاملاً يعمل الآن؟"""
        return self.threadpool.activeThreadCount()

    def wait_for_all(self):
        """إجبار النظام على انتظار الجميع (يستخدم عند الإغلاق فقط)"""
        self.threadpool.waitForDone()

# Global Accessor
task_manager = TaskManager.get_instance()