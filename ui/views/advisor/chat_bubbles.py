# -*- coding: utf-8 -*-
"""
Alpha Sovereign - Intelligent Chat Bubbles
Path: ui/views/advisor/chat_bubbles.py
Description: Renders chat messages with Markdown support, auto-resizing, and dynamic theming.
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPalette, QDesktopServices

# --- استيراد البنية التحتية ---
# تأكد من أن ملف theme_engine موجود في المسار الصحيح
try:
    from ui.core.theme_engine import theme_engine
except ImportError:
    # Fallback إذا لم يتم العثور على المحرك لسبب ما
    logging.warning("ThemeEngine not found, using default mocks.")
    class MockTheme:
        def get_color(self, name): return "#00ff88" if name == "primary" else "#333"
        @property
        def theme_changed(self): 
            class Sig: 
                def connect(self, f): pass
            return Sig()
    theme_engine = MockTheme()

class ChatBubble(QWidget):
    """
    فقاعة محادثة ذكية (Smart Chat Bubble).
    
    المميزات:
    1. Markdown Rendering: تحويل نصوص MD إلى HTML لعرض الأكواد والجداول.
    2. Auto-Resizing: تمدد تلقائي لارتفاع الفقاعة بناءً على المحتوى.
    3. Selectable Text: إمكانية تحديد ونسخ النصوص (ضروري للأكواد).
    """

    def __init__(self, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.raw_text = text
        
        # إعداد التخطيط العام للفقاعة داخل السطر
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(10)

        # بناء المحتوى الداخلي
        self._init_ui()
        
        # تطبيق الثيم المبدئي
        # نستخدم try/except لتجنب انهيار البرنامج إذا لم يكن theme_engine جاهزاً
        try:
            theme_engine.theme_changed.connect(self._apply_theme)
        except Exception:
            pass
            
        self._apply_theme()

    def _init_ui(self):
        # 1. الصورة الرمزية (Avatar)
        self.avatar = QLabel()
        self.avatar.setFixedSize(35, 35)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        # سيتم ضبط الألوان في دالة _apply_theme
        
        if self.is_user:
            self.avatar.setText("U") # User
        else:
            self.avatar.setText("A") # Alpha Advisor

        # 2. محتوى الرسالة (Message Content)
        # نستخدم QTextEdit بدلاً من QLabel لدعم التحديد والنسخ
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content.setFrameShape(QFrame.Shape.NoFrame)
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # تحويل المارك داون إلى HTML
        # نستخدم setMarkdown المدمجة في PyQt6
        try:
            self.content.setMarkdown(self.raw_text)
        except AttributeError:
            # Fallback للنسخ القديمة جداً
            self.content.setText(self.raw_text)

        # 3. طابع زمني صغير (Timestamp)
        self.lbl_time = QLabel(datetime.now().strftime("%H:%M"))
        self.lbl_time.setFont(QFont("Segoe UI", 8))
        
        # 4. حاوية عمودية للنص والوقت
        msg_container = QWidget()
        msg_layout = QVBoxLayout(msg_container)
        msg_layout.setContentsMargins(0, 0, 0, 0)
        msg_layout.setSpacing(2)
        msg_layout.addWidget(self.content)
        
        # محاذاة الوقت تعتمد على المرسل
        time_align = Qt.AlignmentFlag.AlignRight if self.is_user else Qt.AlignmentFlag.AlignLeft
        msg_layout.addWidget(self.lbl_time, alignment=time_align)

        # --- تجميع العناصر في السطر الرئيسي ---
        # ترتيب العناصر: [صورة] ... [نص] ... [صورة] حسب المرسل
        
        if self.is_user:
            # المستخدم (يمين): [فراغ] [نص] [صورة]
            self.layout.addStretch() 
            self.layout.addWidget(msg_container)
            self.layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignTop)
        else:
            # المستشار (يسار): [صورة] [نص] [فراغ]
            self.layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignTop)
            self.layout.addWidget(msg_container)
            self.layout.addStretch()

        # تخزين الحاوية لتطبيق الستايل عليها لاحقاً
        self.msg_container_widget = msg_container 

        # ضبط الارتفاع تلقائياً بعد الرسم الأولي
        QTimer.singleShot(10, self._adjust_height)

    def _adjust_height(self):
        """حساب ارتفاع النص بدقة لضبط حجم الفقاعة"""
        doc = self.content.document()
        # نضبط عرض المستند ليكون أقل قليلاً من عرض الفقاعة المتاح لضمان التفاف النص
        available_width = self.width() - 80 # خصم الصورة والهوامش
        if available_width > 0:
            doc.setTextWidth(available_width)
            
        height = doc.size().height() + 25 # هامش إضافي للوقت والبادينج
        
        # تعيين الارتفاع الأدنى
        height = max(50, int(height))
        
        self.content.setFixedHeight(int(doc.size().height() + 10))
        self.setFixedHeight(height)

    def resizeEvent(self, event):
        """إعادة الحساب عند تغيير حجم النافذة"""
        self._adjust_height()
        super().resizeEvent(event)

    def _apply_theme(self):
        """تلوين الفقاعات حسب الثيم"""
        primary = theme_engine.get_color("primary")
        surface = theme_engine.get_color("surface")
        text_fg = theme_engine.get_color("text_primary")
        text_sec = theme_engine.get_color("text_secondary")
        bg_color = theme_engine.get_color("background")
        
        # ألوان مختلفة للمستخدم وللنظام
        if self.is_user:
            # فقاعة المستخدم (ملونة وشفافة قليلاً)
            try:
                c = QColor(primary)
                bubble_bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 40)" 
            except:
                bubble_bg = "#333"
                
            border_col = primary
            text_col = text_fg
            avatar_bg = primary
            avatar_fg = "#000000"
        else:
            # فقاعة النظام (داكنة)
            bubble_bg = surface
            border_col = theme_engine.get_color("grid_line")
            text_col = text_fg
            avatar_bg = theme_engine.get_color("secondary")
            avatar_fg = bg_color

        # 1. ستايل الصورة الرمزية
        self.avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {avatar_bg};
                color: {avatar_fg};
                border-radius: 17px;
                font-weight: bold;
                border: 1px solid {border_col};
            }}
        """)

        # 2. ستايل النص (داخل QTextEdit)
        self.content.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bubble_bg};
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 10px;
                padding: 8px;
                font-family: 'Segoe UI';
                font-size: 14px;
            }}
        """)
        
        # 3. لون الوقت
        self.lbl_time.setStyleSheet(f"color: {text_sec}; margin-top: 2px;")