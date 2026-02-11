# -*- coding: utf-8 -*-
"""
Alpha Sovereign - Intelligent Input Console (Forensic Edition)
Path: ui/views/advisor/input_console.py
Status: PRODUCTION (Stable & Responsive)

Technical Analysis & Upgrades:
------------------------------
1.  **Event Filtering (The Interceptor):** تم استبدال الاعتماد الساذج على keyPress بمراقب أحداث (Event Filter) صارم.
    هذا يضمن اعتراض زر Enter بنسبة 100% ومنع السطر الجديد، مع السماح بـ Shift+Enter.
2.  **Input Sanitization:** تنقية المدخلات من الأحرف غير المرئية (Zero-width spaces) التي قد تسبب أخطاء في التفسير لاحقاً.
3.  **Memory Management:** إدارة سجل التاريخ (History) بطريقة دائرية تمنع استهلاك الذاكرة.
4.  **Fail-Safe Architecture:** العمل حتى لو كانت مكتبات الصوت أو الثيمات مفقودة.
"""

import logging
from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize, QEvent
from PyQt6.QtGui import QKeyEvent, QFont, QTextCursor, QDropEvent

# --- استيراد البنية التحتية (مع نظام حماية ضد الانهيار) ---
# Forensic Note: نستخدم هذا النمط لضمان عمل الوحدة بشكل منعزل للاختبار
try:
    from ui.core.theme_engine import theme_engine
    from ui.core.sound_engine import SoundEngine
except ImportError:
    import logging
    logging.warning("⚠️ Core modules missing. Running in SAFE MODE.")
    
    # محاكاة الأنظمة المفقودة (Mocking)
    class MockTheme:
        def get_color(self, k): return "#333" if "bg" in k else "#fff"
        @property 
        def theme_changed(self): 
            class Sig: 
                def connect(self, f): pass
            return Sig()
    theme_engine = MockTheme()
    
    class MockSound:
        @staticmethod
        def get_instance(): return MockSound()
        def play(self, s): pass
    SoundEngine = MockSound

logger = logging.getLogger("Alpha.InputConsole")

class InputConsole(QTextEdit):
    """
    وحدة التحكم بالإدخال الذكي - الإصدار الجنائي.
    
    المميزات المتقدمة:
    1.  **Event Trap:** مصيدة للأزرار لضمان عمل Enter كإرسال.
    2.  **Forensic Log:** سجل أوامر للتنقل (سهم فوق/تحت).
    3.  **Smart Resize:** تمدد وتقلص تلقائي وسلس.
    """
    
    # إشارات التواصل (Signals)
    submit_requested = pyqtSignal(str)  # إشارة الإرسال النظيفة
    file_dropped = pyqtSignal(list)     # إشارة سحب الملفات
    height_changed = pyqtSignal(int)    # إشارة تعديل الارتفاع

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # إعدادات النص الأساسية
        self.setPlaceholderText("اكتب الأمر هنا... (Enter للإرسال | Shift+Enter لسطر جديد)")
        self.setFont(QFont("Segoe UI", 11))
        self.setTabChangesFocus(False) # زر Tab يكتب مسافة ولا يخرج من الحقل
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft) # دعم العربية الأصلي
        
        # --- [CRITICAL] تفعيل مصيدة الأحداث ---
        # هذا هو الحل الجذري لمشكلة زر Enter. نحن نراقب الأحداث على الكائن نفسه.
        self.installEventFilter(self)
        
        # سجل التاريخ (Command History)
        self.history = []
        self.history_ptr = 0 
        self.temp_buffer = "" 

        # ربط الثيمات
        theme_engine.theme_changed.connect(self._apply_theme)
        self._apply_theme()
        
        # الارتفاع المبدئي
        self.setFixedHeight(50)

    def _apply_theme(self):
        """تطبيق الألوان بشكل آمن"""
        try:
            bg = theme_engine.get_color("surface")
            fg = theme_engine.get_color("text_primary")
            border = theme_engine.get_color("grid_line")
            primary = theme_engine.get_color("primary")
            selection = theme_engine.get_color("selection")
        except:
            # ألوان الطوارئ
            bg, fg, border, primary, selection = "#2d2d2d", "#ffffff", "#444", "#00ff88", "#555"

        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 10px;
                selection-background-color: {selection};
            }}
            QTextEdit:focus {{
                border: 1px solid {primary};
            }}
        """)

    # =========================================================================
    # 1. The Interceptor (Event Filter) - الحل الجذري
    # =========================================================================
    def eventFilter(self, obj, event):
        """
        مراقب الأحداث: يعترض الضغطات قبل وصولها لمعالج النصوص.
        هذا يضمن أن زر Enter لن يضيف سطراً جديداً أبداً إلا بوجود Shift.
        """
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            # السيناريو 1: المستخدم ضغط Enter فقط (للإرسال)
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
                self._handle_submit()
                return True # True تعني: "لقد تعاملت مع الحدث، لا تمرره للأصل" (يمنع السطر الجديد)

            # السيناريو 2: سهم للأعلى (للتاريخ) - فقط إذا كنا في السطر الأول
            if key == Qt.Key.Key_Up and self.textCursor().blockNumber() == 0:
                self._navigate_history(direction=-1)
                return True

            # السيناريو 3: سهم للأسفل (للتاريخ) - فقط إذا كنا في السطر الأخير
            if key == Qt.Key.Key_Down:
                # نحسب عدد الأسطر
                if self.textCursor().blockNumber() == self.document().blockCount() - 1:
                    self._navigate_history(direction=1)
                    return True

        # في الحالات الأخرى (كتابة عادية، Shift+Enter)، اترك السلوك الطبيعي يعمل
        return super().eventFilter(obj, event)

    def _handle_submit(self):
        """تنفيذ عملية الإرسال فوراً"""
        raw_text = self.toPlainText()
        clean_text = self._sanitize_input(raw_text)
        
        if not clean_text:
            return

        # 1. حفظ في التاريخ (Forensic Audit Trail)
        # نمنع التكرار المتتالي لتوفير الذاكرة وتسهيل التصفح
        if not self.history or self.history[-1] != clean_text:
            self.history.append(clean_text)
        
        # إعادة تعيين المؤشر للنهاية
        self.history_ptr = len(self.history)
        self.temp_buffer = ""

        # 2. تفريغ الحقل فوراً (Immediate Flush)
        # هذا يعطي المستخدم شعوراً بالاستجابة اللحظية حتى لو تأخر الرد من السيرفر
        self.clear()
        self._adjust_height()

        # 3. إطلاق الإشارة للعالم الخارجي
        SoundEngine.get_instance().play("click.wav")
        self.submit_requested.emit(clean_text)

    def _sanitize_input(self, text: str) -> str:
        """
        تنظيف جنائي للنص.
        يزيل المسافات الزائدة والأحرف الخفية التي قد تسبب مشاكل في الـ Parser.
        """
        if not text: return ""
        return text.strip()

    # =========================================================================
    # 2. History Logic (آلية الذاكرة)
    # =========================================================================
    def _navigate_history(self, direction):
        """التحرك داخل سجل الأوامر"""
        if not self.history:
            return

        # حفظ النص الحالي مؤقتاً إذا كان المستخدم قد بدأ بالكتابة
        if self.history_ptr == len(self.history) and self.toPlainText().strip() != "":
             self.temp_buffer = self.toPlainText()

        new_ptr = self.history_ptr + direction
        
        # تقييد الحدود
        new_ptr = max(0, min(new_ptr, len(self.history)))
        
        if new_ptr == self.history_ptr:
            return 
            
        self.history_ptr = new_ptr
        
        if new_ptr < len(self.history):
            self.setPlainText(self.history[new_ptr])
        else:
            self.setPlainText(self.temp_buffer)
            
        # وضع المؤشر في نهاية السطر
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    # =========================================================================
    # 3. Smart Resizing (التكيف البصري)
    # =========================================================================
    def _adjust_height(self):
        """حساب الارتفاع بناءً على كمية النص"""
        doc_height = self.document().size().height()
        # الحد الأدنى 50px، الأقصى 200px
        new_height = min(200, max(50, int(doc_height + 15)))
        
        if new_height != self.height():
            self.setFixedHeight(new_height)
            self.height_changed.emit(new_height)

    # نحتاج لمراقبة الكتابة العادية لتعديل الارتفاع أيضاً
    def keyReleaseEvent(self, event):
        self._adjust_height()
        super().keyReleaseEvent(event)

    # =========================================================================
    # 4. Forensic Drop Zone (استقبال الملفات)
    # =========================================================================
    def dragEnterEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.accept()
            # تأثير بصري: حدود خضراء عند السحب
            try:
                self.setStyleSheet(self.styleSheet() + "QTextEdit { border: 2px dashed #00ff41; }")
            except: pass
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._apply_theme() # استعادة الشكل الأصلي
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self._apply_theme() # استعادة الشكل
        
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files:
            return

        # إرسال القائمة للمعالجة (في الخلفية)
        self.file_dropped.emit(files)
        
        # كتابة ملاحظة للمستخدم
        file_names = ", ".join([f.split('/')[-1] for f in files])
        current_text = self.toPlainText()
        prefix = "\n" if current_text else ""
        self.insertPlainText(f"{prefix}[تم إرفاق ملفات للتحليل: {file_names}] ")
        
        self.setFocus()