# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVISOR VIEW (DECOUPLED EDITION)
==================================================
Path: alpha_project/ui/views/advisor/advisor_view.py
Role: "قمرة القيادة" - واجهة الشات التي تتحدث مع المستخدم.
Architecture: MVVM-like (View -> Locator -> Bridge -> Model).

Forensic Features:
  1. **Strict Dependency Decoupling**: لا يوجد أي استيراد مباشر من مجلد 'brain'. كل شيء يمر عبر 'locator'.
  2. **Real-Time Health Monitoring**: مراقبة حية لحالة النظام. إذا مات العقل، تنطفئ الواجهة.
  3. **No-Mock Policy**: إذا فشل الاتصال، يظهر خطأ صريح. لا وجود لردود "تجريبية".
  4. **Thread Safety**: استخدام QThread مع Bridge لضمان عدم تجميد الواجهة أثناء التفكير المالي.

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, 
    QTextEdit, QPushButton, QLabel, QScrollBar, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QColor

# --- استيراد البنية التحتية (Infrastructure) ---
# Forensic Note: نحن نستورد "السفير" (Locator) فقط، ولا نلمس الملفات الداخلية.
from alpha_project.ui.core.service_locator import locator
from alpha_project.ui.core.theme_engine import theme_engine
from alpha_project.ui.core.sound_engine import SoundEngine

# مكونات الواجهة
try:
    from alpha_project.ui.views.advisor.chat_bubbles import ChatBubble
    from alpha_project.ui.views.advisor.input_console import InputConsole
except ImportError:
    # Fallback للمكونات البسيطة إذا لم تكن المخصصة جاهزة
    ChatBubble = None
    InputConsole = None

logger = logging.getLogger("Alpha.UI.Advisor")

# =============================================================================
# 1. The Thinking Worker (الخيط الخلفي للتفكير)
# =============================================================================

class ThinkingThread(QThread):
    """
    خيط معالجة الطلبات.
    يقوم بإرسال السؤال إلى 'الجسر' وينتظر الرد دون تجميد الواجهة.
    """
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def run(self):
        try:
            # 1. طلب الجسر عبر السفير
            # Forensic Note: هذا هو التغيير الجوهري. لا ننشئ Gateway يدوياً.
            bridge = locator.get_bridge()
            
            # 2. إرسال الطلب (الجسر يتكفل بالتوجيه والنسخ الاحتياطي)
            # لاحظ أننا لا نعرف من هو العقل (OpenRouter? Google? Local?)
            response = bridge.ask_brain(self.prompt)
            
            if response:
                self.response_received.emit(response)
            else:
                self.error_occurred.emit("⚠️ Received empty response from system core.")
                
        except RuntimeError as e:
            # هذا الخطأ يحدث إذا كان النظام غير مكتمل (Missing Components)
            self.error_occurred.emit(f"⛔ SYSTEM HALT: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"❌ Communication Error: {str(e)}")

# =============================================================================
# 2. Main View Class (الواجهة الرئيسية)
# =============================================================================

class AdvisorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None 
        
        # 1. إعداد الواجهة
        self.setup_ui()
        
        # 2. التحقق الأولي من الصحة (Pre-Flight Check)
        self._initial_health_check()
        
        # 3. إعداد مراقب النبض (تحديث كل 5 ثواني)
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._monitor_system_health)
        self.health_timer.start(5000)

    def setup_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Header
        self._setup_header()
        # Chat Area
        self._setup_chat_area()
        # Input Area
        self._setup_input_area()

        # Theme Application
        if theme_engine: 
            theme_engine.theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _setup_header(self):
        header = QFrame()
        header.setFixedHeight(60)
        header.setObjectName("HeaderFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        title = QLabel("🤖 غرفة العمليات المالية (Alpha Core)")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88;")
        
        # مؤشر الحالة الديناميكي
        self.status_label = QLabel("⚡ جاري الفحص...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        
        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(self.status_label)
        self.layout.addWidget(header)
        self.header_widget = header

    def _setup_chat_area(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch() 
        
        self.scroll_area.setWidget(self.chat_container)
        self.layout.addWidget(self.scroll_area)

    def _setup_input_area(self):
        input_container = QFrame()
        input_container.setObjectName("InputFrame")
        input_container.setMinimumHeight(80)
        layout = QHBoxLayout(input_container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # زر الإرفاق (للمستقبل)
        self.btn_attach = QPushButton("📎")
        self.btn_attach.setFixedSize(40, 40)
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_attach)

        # الكونسول الذكي
        if InputConsole:
            self.input_field = InputConsole()
            self.input_field.submit_requested.connect(self.process_message)
        else:
            self.input_field = QTextEdit() # Fallback
            
        self.input_field.setPlaceholderText("جاري الاتصال بالنظام...")
        self.input_field.setFixedHeight(50)
        self.input_field.setEnabled(False) # معطل افتراضياً حتى نتأكد من النظام
        layout.addWidget(self.input_field)

        # زر الإرسال
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(50, 50)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._manual_submit)
        self.btn_send.setEnabled(False)
        
        layout.addWidget(self.btn_send)
        self.layout.addWidget(input_container)
        self.input_container_widget = input_container

    # =========================================================================
    # 3. Logic & Connectivity (المنطق والاتصال)
    # =========================================================================

    def _initial_health_check(self):
        """الفحص الأول عند التشغيل"""
        is_healthy = locator.is_system_healthy()
        self._update_ui_state(is_healthy)
        
        if is_healthy:
            self.add_message("SYSTEM", "✅ تم تأمين الاتصال بالنواة. النظام جاهز.")
        else:
            self.add_message("SYSTEM", "⛔ **تحذير**: لم يتم العثور على وحدات الذكاء. النظام في وضع المراقبة فقط.")

    def _monitor_system_health(self):
        """فحص دوري للحالة (Pulse Check)"""
        # نسأل السفير: هل مازال العقل موجوداً؟
        is_healthy = locator.is_system_healthy()
        self._update_ui_state(is_healthy)

    def _update_ui_state(self, is_healthy: bool):
        """تحديث العناصر المرئية بناءً على الصحة"""
        if is_healthy:
            self.status_label.setText("🟢 متصل بالنواة")
            self.status_label.setStyleSheet("color: #00ff88; font-weight: bold;")
            self.input_field.setEnabled(True)
            self.btn_send.setEnabled(True)
            self.input_field.setPlaceholderText("اكتب استفسارك المالي هنا...")
        else:
            self.status_label.setText("🔴 النظام غير متصل")
            self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
            self.input_field.setEnabled(False)
            self.btn_send.setEnabled(False)
            self.input_field.setPlaceholderText("⛔ خطأ في الاتصال بالنواة...")

    def _manual_submit(self):
        if hasattr(self.input_field, 'toPlainText'):
            text = self.input_field.toPlainText().strip()
            if text:
                self.process_message(text)
                self.input_field.clear()

    def process_message(self, text):
        if not text: return
        
        # 1. تدقيق أمني أخير قبل الإرسال
        if not locator.is_system_healthy():
            self.add_message("SYSTEM", "❌ تم رفض الطلب: النظام غير متصل.")
            return

        self.add_message("USER", text)
        if SoundEngine: SoundEngine.get_instance().play("click.wav")
        
        # مؤشر الكتابة
        self.typing_indicator = self.add_message("SYSTEM", "⏳ جاري تحليل السوق...", is_temp=True)
        
        # 2. تشغيل الخيط
        self.worker = ThinkingThread(text)
        self.worker.response_received.connect(self.on_brain_success)
        self.worker.error_occurred.connect(self.on_brain_error)
        self.worker.start()

    def on_brain_success(self, response_text):
        self._remove_typing_indicator()
        self.add_message("SYSTEM", response_text)
        if SoundEngine: SoundEngine.get_instance().play("success.wav")

    def on_brain_error(self, error_msg):
        self._remove_typing_indicator()
        self.add_message("SYSTEM", f"{error_msg}") # الخطأ يأتي منسقاً من الجسر
        if SoundEngine: SoundEngine.get_instance().play("error.wav")

    # =========================================================================
    # 4. Helper Methods (أدوات العرض)
    # =========================================================================

    def _remove_typing_indicator(self):
        if hasattr(self, 'typing_indicator') and self.typing_indicator:
            self.typing_indicator.deleteLater()
            self.typing_indicator = None

    def add_message(self, sender, text, is_temp=False):
        is_user = (sender == "USER")
        
        if ChatBubble:
            # استخدام الفقاعات المتطورة
            bubble = ChatBubble(text, is_user=is_user)
            if is_temp: bubble.setWindowOpacity(0.7)
        else:
            # Fallback للنص العادي
            bubble = QLabel(f"{sender}: {text}")
            bubble.setStyleSheet(f"color: {'#00ff88' if is_user else '#e0e0e0'}; padding: 10px; border-radius: 5px; background: {'#222' if is_user else '#333'};")
            bubble.setWordWrap(True)

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _apply_theme(self):
        try:
            bg = theme_engine.get_color("background")
            surface = theme_engine.get_color("surface")
            border = theme_engine.get_color("grid_line")
            primary = theme_engine.get_color("primary")
            
            self.scroll_area.setStyleSheet(f"background-color: {bg}; border: none;")
            self.chat_container.setStyleSheet(f"background-color: {bg};")
            self.header_widget.setStyleSheet(f"QFrame#HeaderFrame {{ background-color: {bg}; border-bottom: 1px solid {border}; }}")
            self.input_container_widget.setStyleSheet(f"QFrame#InputFrame {{ background-color: {surface}; border-top: 1px solid {border}; }}")
            self.btn_send.setStyleSheet(f"QPushButton {{ background-color: {primary}; color: #000; border-radius: 25px; font-weight: bold; font-size: 20px; }}")
        except: pass