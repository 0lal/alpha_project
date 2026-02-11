import re
from collections import deque
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, 
    QLabel, QCheckBox, QLineEdit, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon

# --- استيراد البنية التحتية ---
from ui.core.event_hub import event_hub
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink
from ui.components.atoms.modern_buttons import ActionButton, ModernButton

class LogViewer(QWidget):
    """
    عارض السجلات الجنائي (Forensic Log Viewer).
    
    المميزات:
    1. Rich Text: يدعم الألوان والتنسيق (HTML) القادم من LoggerSink.
    2. Filtering: فلترة حية حسب المستوى (DEBUG, INFO, ERROR).
    3. Auto-Scroll Control: إمكانية إيقاف التمرير التلقائي للقراءة.
    4. Regex Search: بحث متقدم داخل السجلات.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Internal State ---
        self._logs_buffer = deque(maxlen=2000) # الذاكرة الحية (آخر 2000 سطر)
        self._is_paused = False
        self._active_filters = {
            "DEBUG": False, # افتراضياً نخفي الـ Debug لتقليل الضوضاء
            "INFO": True,
            "WARNING": True,
            "ERROR": True,
            "CRITICAL": True,
            "SUCCESS": True
        }
        self._search_term = ""

        # --- UI Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        # 1. شريط التحكم العلوي (Toolbar)
        self.toolbar_layout = QHBoxLayout()
        self._setup_toolbar()
        self.layout.addLayout(self.toolbar_layout)

        # 2. منطقة عرض السجلات (The Terminal)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setReadOnly(True)
        self.text_browser.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap) # تمرير أفقي للأسطر الطويلة
        
        # تطبيق خط Monospace للأكواد
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_browser.setFont(font)
        
        self.layout.addWidget(self.text_browser)

        # 3. شريط الحالة السفلي (Search & Status)
        self.status_layout = QHBoxLayout()
        self._setup_statusbar()
        self.layout.addLayout(self.status_layout)

        # --- Wiring ---
        # الاستماع لتدفق السجلات من القلب النابض
        event_hub.system_log_received.connect(self._on_log_received)
        
        # مؤقت للتحديث الدوري (تخفيف الحمل على الواجهة)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._refresh_display)
        self._update_timer.start(200) # تحديث كل 200ms
        self._pending_refresh = False

        # تطبيق الثيم
        theme_engine.theme_changed.connect(self._apply_style)
        self._apply_style()
        
        logger_sink.log_system_event("LogViewer", "INFO", "🖥️ Forensic Console Attached.")

    def _setup_toolbar(self):
        """إعداد أزرار الفلترة والتحكم"""
        # Checkboxes for Levels
        self.chk_error = self._create_filter_chk("ERR", "ERROR", "#ff5555", True)
        self.chk_warn = self._create_filter_chk("WRN", "WARNING", "#ffb86c", True)
        self.chk_info = self._create_filter_chk("INF", "INFO", "#8be9fd", True)
        self.chk_debug = self._create_filter_chk("DBG", "DEBUG", "#6272a4", False)

        # Spacer
        self.toolbar_layout.addStretch()

        # Control Buttons
        self.btn_pause = ActionButton("PAUSE")
        self.btn_pause.setCheckable(True)
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_pause.setFixedHeight(25)
        
        self.btn_clear = ModernButton("CLEAR")
        self.btn_clear.clicked.connect(self._clear_logs)
        self.btn_clear.setFixedHeight(25)
        
        self.btn_save = ModernButton("SAVE")
        self.btn_save.clicked.connect(self._save_logs_to_file)
        self.btn_save.setFixedHeight(25)

        self.toolbar_layout.addWidget(self.btn_pause)
        self.toolbar_layout.addWidget(self.btn_clear)
        self.toolbar_layout.addWidget(self.btn_save)

    def _create_filter_chk(self, label, level_key, color, checked):
        chk = QCheckBox(label)
        chk.setChecked(checked)
        chk.setStyleSheet(f"color: {color}; font-weight: bold;")
        chk.stateChanged.connect(lambda: self._update_filter(level_key, chk.isChecked()))
        self.toolbar_layout.addWidget(chk)
        return chk

    def _setup_statusbar(self):
        """إعداد شريط البحث"""
        lbl_search = QLabel("🔍 Find:")
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Regex supported...")
        self.txt_search.textChanged.connect(self._on_search_changed)
        
        self.status_layout.addWidget(lbl_search)
        self.status_layout.addWidget(self.txt_search)

    def _apply_style(self):
        """تلوين الواجهة لتشبه التيرمينال الحقيقي"""
        bg = theme_engine.get_color("background")
        fg = theme_engine.get_color("text_primary")
        surface = theme_engine.get_color("surface")
        
        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {theme_engine.get_color("grid_line")};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {surface};
                color: {fg};
                border: 1px solid {theme_engine.get_color("grid_line")};
                border-radius: 4px;
                padding: 2px 5px;
            }}
        """)

    # =========================================================================
    # Logic Implementation
    # =========================================================================

    def _update_filter(self, level, is_checked):
        self._active_filters[level] = is_checked
        self._pending_refresh = True # طلب إعادة رسم
        self._refresh_display()

    def _toggle_pause(self):
        self._is_paused = self.btn_pause.isChecked()
        if self._is_paused:
            self.btn_pause.setText("RESUME")
            self.btn_pause.setStyleSheet(f"background-color: {theme_engine.get_color('danger')}")
        else:
            self.btn_pause.setText("PAUSE")
            self.btn_pause.setStyleSheet("") # Revert to default
            self._pending_refresh = True # تحديث ما فاتنا

    def _on_search_changed(self, text):
        self._search_term = text
        self._pending_refresh = True
        self._refresh_display()

    @pyqtSlot(str, str, str)
    def _on_log_received(self, level, source, html_message):
        """استقبال السجل وتخزينه في الذاكرة المؤقتة"""
        # تخزين السجل كـ Tuple (raw_data, html_formatted)
        # نحتاج المستوى للتصفية لاحقاً
        entry = {
            'level': level,
            'source': source,
            'html': html_message,
            'raw': self._strip_html(html_message) # للنص الخام للبحث
        }
        self._logs_buffer.append(entry)
        
        # إذا لم نكن في وضع الإيقاف المؤقت، نطلب التحديث
        if not self._is_paused:
            self._pending_refresh = True

    def _refresh_display(self):
        """إعادة بناء النص المعروض بناءً على الفلاتر (Batch Rendering)"""
        if not self._pending_refresh or self._is_paused:
            return

        # تجميع النصوص المقبولة
        visible_logs = []
        for log in self._logs_buffer:
            # 1. فلتر المستوى
            if not self._active_filters.get(log['level'], True):
                continue
            
            # 2. فلتر البحث (Regex)
            if self._search_term:
                try:
                    if not re.search(self._search_term, log['raw'], re.IGNORECASE):
                        continue
                except re.error:
                    pass # تجاهل أخطاء الـ Regex أثناء الكتابة

            visible_logs.append(log['html'])

        # تحديث العارض دفعة واحدة
        final_html = "<br>".join(visible_logs)
        self.text_browser.setHtml(final_html)
        
        # التمرير للأسفل تلقائياً
        scrollbar = self.text_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        self._pending_refresh = False

    def _strip_html(self, html):
        """إزالة وسوم HTML للبحث في النص الخام"""
        return re.sub('<[^<]+?>', '', html)

    def _clear_logs(self):
        self._logs_buffer.clear()
        self.text_browser.clear()
        logger_sink.log_system_event("LogViewer", "INFO", "🧹 Console Cleared by User.")

    def _save_logs_to_file(self):
        """تصدير السجلات الحالية لملف نصي"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for log in self._logs_buffer:
                        f.write(f"[{log['level']}] {log['raw']}\n")
                logger_sink.log_system_event("LogViewer", "SUCCESS", f"💾 Logs exported to {file_path}")
            except Exception as e:
                logger_sink.log_system_event("LogViewer", "ERROR", f"Failed to export logs: {e}")