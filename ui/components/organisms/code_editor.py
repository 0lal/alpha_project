import sys
import ast
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QTextFormat, QFont, QSyntaxHighlighter, QTextCharFormat, QFontDatabase

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine
from ui.core.logger_sink import logger_sink

# =============================================================================
# 1. Syntax Highlighter (الملون اللغوي)
# =============================================================================
class PythonHighlighter(QSyntaxHighlighter):
    """
    يقوم بتحليل النص وتلوينه بناءً على قواعد لغة بايثون.
    """
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # إعداد التنسيقات (سيتم تحديث الألوان لاحقاً من الثيم)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        self.string_format = QTextCharFormat()
        self.comment_format = QTextCharFormat()
        self.number_format = QTextCharFormat()
        
        # الكلمات المفتاحية لبايثون
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True',
            'try', 'while', 'with', 'yield'
        ]
        
        # قواعد التلوين (Regex Patterns)
        for word in keywords:
            pattern = fr'\b{word}\b'
            self.highlighting_rules.append((pattern, self.keyword_format))

        # Strings ("..." or '...')
        self.highlighting_rules.append((r'".*?"', self.string_format))
        self.highlighting_rules.append((r"'.*?'", self.string_format))
        
        # Comments (# ...)
        self.highlighting_rules.append((r'#[^\n]*', self.comment_format))
        
        # Numbers
        self.highlighting_rules.append((r'\b\d+\b', self.number_format))

        self.update_colors()

    def update_colors(self):
        """تحديث الألوان بناءً على الثيم الحالي"""
        # جلب الألوان من ThemeEngine
        # استخدام ألوان 'logic' من الثيم (أو ألوان افتراضية)
        palette = theme_engine.get_palette()
        
        keyword_color = QColor(palette.get("primary", "#ff79c6")) # Pink/Green
        string_color = QColor("#f1fa8c") # Yellow
        comment_color = QColor(palette.get("text_secondary", "#6272a4")) # Gray
        number_color = QColor(palette.get("secondary", "#bd93f9")) # Purple/Cyan

        self.keyword_format.setForeground(keyword_color)
        self.string_format.setForeground(string_color)
        self.comment_format.setForeground(comment_color)
        self.number_format.setForeground(number_color)
        
        self.rehighlight()

    def highlightBlock(self, text):
        import re
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), format)

# =============================================================================
# 2. Line Number Area (شريط الأرقام الجانبي)
# =============================================================================
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)

# =============================================================================
# 3. The Code Editor (المحرر الجراحي)
# =============================================================================
class CodeEditor(QPlainTextEdit):
    """
    محرر أكواد متقدم يدعم التلوين والتحقق والترقيم.
    """
    validation_status_changed = pyqtSignal(bool, str) # (is_valid, error_msg)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # إعداد الخط (Monospace)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        
        # المكونات الإضافية
        self.line_number_area = LineNumberArea(self)
        self.highlighter = PythonHighlighter(self.document())

        # إعدادات العرض
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap) # لا نلف الأسطر في الكود
        
        # الأحداث
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.textChanged.connect(self._on_text_changed)
        
        theme_engine.theme_changed.connect(self._apply_theme)
        
        self.update_line_number_area_width(0)
        self._apply_theme()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space + 10

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        
        # لون خلفية الأرقام
        bg_color = theme_engine.get_color("surface")
        painter.fillRect(event.rect(), QColor(bg_color))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        # لون الأرقام
        text_color = theme_engine.get_color("text_secondary")
        painter.setPen(QColor(text_color))

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def _apply_theme(self):
        """تطبيق ألوان المحرر"""
        bg = theme_engine.get_color("background")
        fg = theme_engine.get_color("text_primary")
        caret = theme_engine.get_color("primary")
        
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {theme_engine.get_color("grid_line")};
                border-radius: 4px;
            }}
        """)
        
        # تحديث ألوان المؤشر (Caret)
        p = self.palette()
        p.setColor(p.ColorRole.Text, QColor(fg))
        p.setColor(p.ColorRole.Base, QColor(bg))
        self.setPalette(p)
        
        # تحديث الملون اللغوي
        self.highlighter.update_colors()

    # =========================================================================
    # Forensic Validation (التحقق الجنائي)
    # =========================================================================
    def _on_text_changed(self):
        """التحقق من الكود عند كل تغيير"""
        code = self.toPlainText()
        try:
            # محاولة بناء شجرة النحو (AST)
            ast.parse(code)
            self.validation_status_changed.emit(True, "Valid Python Syntax")
            
            # إزالة الحدود الحمراء إذا كانت موجودة
            self.setStyleSheet(self.styleSheet().replace("border: 2px solid #ff5555;", f"border: 1px solid {theme_engine.get_color('grid_line')};"))
            
        except SyntaxError as e:
            msg = f"Syntax Error at line {e.lineno}: {e.msg}"
            self.validation_status_changed.emit(False, msg)
            
            # وضع حدود حمراء للتحذير
            self.setStyleSheet(self.styleSheet() + "QPlainTextEdit { border: 2px solid #ff5555; }")

    def get_code(self) -> str:
        """استرجاع الكود فقط إذا كان صالحاً"""
        code = self.toPlainText()
        try:
            ast.parse(code)
            return code
        except SyntaxError:
            return None # أو إثارة استثناء

    def set_code(self, code: str):
        self.setPlainText(code)