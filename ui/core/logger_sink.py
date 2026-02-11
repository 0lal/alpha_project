import logging
import html
import re
import os
from datetime import datetime
from typing import Optional
from PyQt6.QtCore import QObject

# استيراد المكونات الأساسية
from ui.core.event_hub import event_hub
from ui.core.theme_engine import theme_engine
from ui.core.config_provider import config

# -----------------------------------------------------------------------------
# Forensic & Security Filters
# -----------------------------------------------------------------------------
class LogSanitizer:
    """
    Forensic Filter: يقوم بتنظيف السجلات من البيانات الحساسة قبل العرض.
    """
    SENSITIVE_PATTERNS = [
        r'(api_key|secret|password|token)\s*[:=]\s*([A-Za-z0-9_\-]+)',
        r'(Bearer)\s+([A-Za-z0-9\-\._]+)',
        r'(private_key)\s*[:=]\s*(-----BEGIN.*)'
    ]
    
    @staticmethod
    def clean(message: str) -> str:
        for pattern in LogSanitizer.SENSITIVE_PATTERNS:
            message = re.sub(pattern, r'\1: [REDACTED_SECURE]', message, flags=re.IGNORECASE)
        return message

# -----------------------------------------------------------------------------
# Main Logger Sink
# -----------------------------------------------------------------------------
class AlphaLoggerSink(logging.Handler, QObject):
    """
    The Central Log Aggregator.
    """
    
    DEFAULT_COLORS = {
        'DEBUG': '#808080',    # Gray
        'INFO': '#e6edf3',     # White/Light Gray
        'WARNING': '#d29922',  # Yellow/Gold
        'ERROR': '#f85149',    # Red
        'CRITICAL': '#ff0000', # Bright Red
        'SUCCESS': '#238636'   # Green
    }

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AlphaLoggerSink, cls).__new__(cls)
            QObject.__init__(cls._instance)
            logging.Handler.__init__(cls._instance)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self._setup_python_logging()
        self._initialized = True
        
        # لا نستخدم log_system_event هنا لتجنب التكرار عند البدء، نعتمد على الإشارة المباشرة إذا لزم الأمر
        # لكن بما أن النظام لم يبدأ بالكامل، قد لا تصل الإشارة. نكتفي بالتهيئة الصامتة.

    def _setup_python_logging(self):
        """ربط هذا الـ Sink بجذر النظام لالتقاط كل شيء"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # إزالة المعالجات المكررة لتجنب تكرار الرسائل في الكونسول
        if not any(isinstance(h, AlphaLoggerSink) for h in root_logger.handlers):
            root_logger.addHandler(self)

    def emit(self, record: logging.LogRecord):
        """Python logging entry point"""
        try:
            msg = self.format(record)
            level = record.levelname
            source = record.name
            clean_msg = LogSanitizer.clean(msg)
            self._broadcast_to_ui(level, source, clean_msg)
        except Exception:
            self.handleError(record)

    def process_external_log(self, level: str, source: str, message: str):
        """External/Rust logging entry point"""
        clean_msg = LogSanitizer.clean(message)
        normalized_level = level.upper()
        if normalized_level == 'WARN': normalized_level = 'WARNING'
        if normalized_level == 'ERR': normalized_level = 'ERROR'
        self._broadcast_to_ui(normalized_level, source, clean_msg)

    def _broadcast_to_ui(self, level: str, source: str, message: str):
        """تجهيز وإرسال الرسالة"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = self._get_level_color(level)
        safe_msg = html.escape(message)
        
        formatted_html = (
            f'<span style="color:#555;">[{timestamp}]</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:#888;">[{source}]:</span> '
            f'<span style="color:{theme_engine.get_color("text_primary")};">{safe_msg}</span>'
        )
        
        # التأكد من أن event_hub مهيأ
        try:
            event_hub.system_log_received.emit(level, source, formatted_html)
        except RuntimeError:
            # قد يحدث هذا إذا تم استدعاء اللوج قبل إنشاء QApplication
            pass

    def _get_level_color(self, level: str) -> str:
        """جلب اللون من الثيم"""
        # نستخدم try-except لتجنب الانهيار إذا كان theme_engine لم يجهز بالكامل بعد
        try:
            if level in ['ERROR', 'CRITICAL']: return theme_engine.get_color('danger')
            elif level == 'WARNING': return theme_engine.get_color('secondary')
            elif level == 'INFO': return theme_engine.get_color('primary')
            elif level == 'DEBUG': return theme_engine.get_color('text_secondary')
        except:
            pass
        return self.DEFAULT_COLORS.get(level, '#ffffff')

    def log_system_event(self, source: str, level: str, message: str):
        self.process_external_log(level, source, message)

# -----------------------------------------------------------------------------
# Helper Functions (This was missing!)
# -----------------------------------------------------------------------------
def setup_logging():
    """
    تهيئة المجلدات وإعدادات التسجيل الأساسية.
    يتم استدعاؤها في بداية تشغيل البرنامج (main).
    """
    # 1. إنشاء مجلد السجلات إذا لم يكن موجوداً
    log_dir = config.project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. إعداد ملف السجل الفعلي (FileHandler) لحفظ الأحداث في ملف نصي
    # هذا مهم للتحليل الجنائي لاحقاً حتى لو أغلق البرنامج
    log_file = log_dir / f"alpha_session_{datetime.now().strftime('%Y%m%d')}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    
    # 3. إعداد التسجيل الجذري
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler] # نضيف FileHandler هنا، أما AlphaLoggerSink فيضيف نفسه تلقائياً
    )

# Global Accessor
logger_sink = AlphaLoggerSink()