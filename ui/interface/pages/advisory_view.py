# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVISORY DASHBOARD (COMMAND CENTER)
=================================================================
Component: interface/pages/advisory_view.py
Role: واجهة التحكم الاستراتيجي (Strategic Control Interface).
Forensic Features:
  - Real-Time Toggles: مفاتيح تحكم فورية لتفعيل/تعطيل أجزاء العقل.
  - Visual Feedback: تأكيد بصري عند تغيير الإعدادات.
  - Modular Layout: فصل التحكم عن العرض (Chat).
=================================================================
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QComboBox, QGroupBox, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPalette

# استيراد المكونات
from interface.components.chat_box import ChatBox
from core.workers import BrainWorker

class StrategyPanel(QGroupBox):
    """
    لوحة التحكم في استراتيجيات العقل.
    تسمح بتفعيل/تعطيل الوحدات العصبية (Quant, Sentiment, AI) ديناميكياً.
    """
    config_changed = Signal(dict) # إشارة ترسل الإعدادات الجديدة

    def __init__(self):
        super().__init__("بروتوكولات الاشتباك (Active Doctrines)")
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(20)

        # 1. مفاتيح التبديل (Strategic Toggles)
        self.chk_quant = self._create_toggle("التحليل الكمي (Quant)", True, "تحليل المؤشرات وتدفق الأوامر")
        self.chk_sent = self._create_toggle("تحليل المشاعر (Sentiment)", True, "مراقبة الأخبار والسوشيال ميديا")
        self.chk_hybrid = self._create_toggle("التفكير الهجين (Hybrid AI)", False, "استخدام LLM لدمج القرارات (مكلف)")

        # 2. القائمة المنسدلة للوضع العام
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["وضع آمن (Conservative)", "متوازن (Balanced)", "هجومي (Sovereign)"])
        self.combo_mode.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b; color: #fff; border: 1px solid #555; padding: 5px;
            }
        """)

        # 3. زر التطبيق
        self.btn_apply = QPushButton("تحديث البروتوكول")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #0066cc; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0077ee; }
            QPushButton:pressed { background-color: #0055aa; }
        """)
        self.btn_apply.clicked.connect(self._emit_config)

        # التجميع
        layout.addWidget(self.chk_quant)
        layout.addWidget(self.chk_sent)
        layout.addWidget(self.chk_hybrid)
        layout.addStretch()
        layout.addWidget(QLabel("ملف المخاطر:"))
        layout.addWidget(self.combo_mode)
        layout.addWidget(self.btn_apply)

    def _create_toggle(self, text, checked, tooltip):
        chk = QCheckBox(text)
        chk.setChecked(checked)
        chk.setToolTip(tooltip)
        chk.setStyleSheet("""
            QCheckBox { color: #ccc; font-size: 13px; }
            QCheckBox::indicator:checked { background-color: #00aa00; border: 1px solid #00ff00; }
        """)
        return chk

    def _emit_config(self):
        """تجميع الإعدادات وإرسالها"""
        config_payload = {
            "modules": {
                "quant_analysis": {"enabled": self.chk_quant.isChecked()},
                "sentiment_analysis": {"enabled": self.chk_sent.isChecked()},
                "hybrid_reasoning": {"enabled": self.chk_hybrid.isChecked()}
            },
            "risk_profile": self.combo_mode.currentText()
        }
        self.config_changed.emit(config_payload)

class AdvisoryView(QWidget):
    """
    الصفحة الرئيسية لغرفة الشورى.
    تدمج بين لوحة التحكم وصندوق المحادثة مع النظام.
    """
    def __init__(self):
        super().__init__()
        
        # التنسيق العام
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. العنوان والحالة
        header_layout = QHBoxLayout()
        title = QLabel("غرفة العمليات المركزية (Sovereign Command)")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff;")
        
        self.status_lbl = QLabel("● النظام متصل")
        self.status_lbl.setStyleSheet("color: #00ff00; font-weight: bold;")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.status_lbl)
        
        self.main_layout.addLayout(header_layout)

        # 2. لوحة الاستراتيجيات (New Component)
        self.strategy_panel = StrategyPanel()
        self.strategy_panel.config_changed.connect(self.on_strategy_update)
        self.main_layout.addWidget(self.strategy_panel)

        # 3. فاصل جمالي
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")
        self.main_layout.addWidget(line)

        # 4. صندوق المحادثة (التقارير الحية)
        # نستخدم worker للاتصال الخلفي
        self.worker = BrainWorker()
        self.worker.response_received.connect(self.on_brain_response)
        
        self.chat = ChatBox(self.worker.analyze)
        self.main_layout.addWidget(self.chat)
        
        # رسالة ترحيبية
        self.chat.add_msg("مرحباً أيها القائد. بانتظار توجيهات الاستراتيجية...", "system")

    @Slot(dict)
    def on_strategy_update(self, config):
        """عندما يضغط المستخدم زر التحديث"""
        # هنا يتم إرسال الإعدادات إلى الـ Backend عبر الـ Worker
        # (سنحتاج لتحديث BrainWorker لاحقاً لدعم هذا النوع من الرسائل)
        
        # محاكاة الاستجابة الفورية في الواجهة
        active_modules = [k for k, v in config['modules'].items() if v['enabled']]
        msg = f"تم تحديث البروتوكولات:\n- الوحدات النشطة: {', '.join(active_modules)}\n- مستوى المخاطرة: {config['risk_profile']}"
        
        self.chat.add_msg(msg, "user_command")
        self.chat.add_msg("جاري إعادة تكوين المصفوفة العصبية...", "system")
        
        # إرسال فعلي (يجب تفعيله عند ربط الـ Router)
        # self.worker.update_config(config)

    @Slot(str)
    def on_brain_response(self, text):
        """استقبال ردود من العقل"""
        self.chat.add_msg(text, "brain")