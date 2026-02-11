from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QColor, QCursor

# --- استيراد البنية التحتية ---
from ui.core.theme_engine import theme_engine

class NavButton(QPushButton):
    """
    زر تنقل مخصص (Custom Navigation Button).
    يدعم الحالة النشطة (Active State) والرموز (Icons).
    """
    def __init__(self, text, icon_name, page_id, parent=None):
        super().__init__(text, parent)
        self.page_id = page_id
        self.icon_name = icon_name
        self.setCheckable(True) # لكي يبقى مضغوطاً إذا كان نشطاً
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(50)
        self.setIconSize(QSize(24, 24))
        
        # ربط الثيم
        theme_engine.theme_changed.connect(self.apply_style)
        self.apply_style()

    def apply_style(self):
        """تلوين الزر بناءً على حالته (Active/Inactive)"""
        text_color = theme_engine.get_color("text_secondary")
        active_text = theme_engine.get_color("text_primary")
        active_bg = theme_engine.get_color("surface")
        accent = theme_engine.get_color("primary")
        hover = theme_engine.get_color("surface") # افتراضاً
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                border-left: 3px solid transparent;
                text-align: left;
                padding-left: 15px;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover};
                color: {active_text};
            }}
            QPushButton:checked {{
                background-color: {active_bg};
                color: {active_text};
                border-left: 3px solid {accent}; /* المؤشر الجانبي */
                font-weight: bold;
            }}
        """)
        
        # هنا يجب تحميل الأيقونة الحقيقية بناءً على الثيم (أبيض/أسود)
        # self.setIcon(QIcon(f"ui/assets/icons/{self.icon_name}.png")) 


class SideNavBar(QFrame):
    """
    القائمة الجانبية القابلة للطي (Collapsible Sidebar).
    """
    # إشارة لتغيير الصفحة: ترسل اسم الصفحة (page_id)
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.collapsed = False
        self.full_width = 220
        self.collapsed_width = 60
        
        # إعداد الإطار الأساسي
        self.setFixedWidth(self.full_width)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # --- Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 1. Header (Logo + Toggle)
        self._setup_header()
        
        # 2. Navigation Buttons
        self.buttons = []
        self._add_nav_item("Cockpit", "dashboard", "dashboard_view")
        self._add_nav_item("Strategy", "brain", "strategy_view")
        self._add_nav_item("Execution", "flash", "execution_view")
        self._add_nav_item("Lab", "flask", "simulation_view")
        self._add_nav_item("Forensics", "search", "forensics_view")
        
        self.layout.addStretch() # دفع الإعدادات للأسفل
        
        # 3. Footer (Settings)
        self._add_nav_item("Settings", "cogs", "settings_view")
        
        # 4. Version Label
        self.lbl_version = QLabel("v1.0.0 ALPHA")
        self.lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_version.setFont(QFont("Consolas", 8))
        self.lbl_version.setStyleSheet(f"color: {theme_engine.get_color('text_secondary')}; padding-bottom: 10px;")
        self.layout.addWidget(self.lbl_version)

        # ربط الثيم
        theme_engine.theme_changed.connect(self._apply_theme)
        self._apply_theme()
        
        # تحديد الصفحة الافتراضية
        self.set_active_page("dashboard_view")

    def _setup_header(self):
        """رأس القائمة مع زر التوسيع/الطي"""
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(60)
        v_layout = QVBoxLayout(self.header_frame)
        
        self.btn_toggle = QPushButton("ALPHA")
        self.btn_toggle.setFont(QFont("Segoe UI", 12, QFont.Weight.Black))
        self.btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        # إزالة الحدود لزر التوغل ليبدو كعنوان
        self.btn_toggle.setStyleSheet("background: transparent; border: none; text-align: left; padding-left: 15px;")
        
        v_layout.addWidget(self.btn_toggle)
        self.layout.addWidget(self.header_frame)

    def _add_nav_item(self, text, icon, page_id):
        """إضافة زر للقائمة"""
        btn = NavButton(text, icon, page_id)
        btn.clicked.connect(lambda: self.set_active_page(page_id))
        self.layout.addWidget(btn)
        self.buttons.append(btn)

    def set_active_page(self, page_id):
        """تغيير الصفحة النشطة وإطلاق الإشارة"""
        for btn in self.buttons:
            was_checked = btn.isChecked()
            should_check = (btn.page_id == page_id)
            
            if was_checked != should_check:
                btn.setChecked(should_check)
        
        self.page_changed.emit(page_id)

    def toggle_sidebar(self):
        """حركة التوسيع والطي (Animation)"""
        target_width = self.collapsed_width if not self.collapsed else self.full_width
        
        self.anim = QPropertyAnimation(self, b"minimumWidth")
        self.anim.setDuration(300)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(target_width)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
        
        # تحديث النصوص (إخفاء/إظهار)
        if not self.collapsed: # جاري الطي
            self.btn_toggle.setText("A") # شعار صغير
            self.lbl_version.hide()
            for btn in self.buttons:
                btn.setText("") # إخفاء النص والاكتفاء بالأيقونة
        else: # جاري التوسيع
            self.btn_toggle.setText("ALPHA")
            self.lbl_version.show()
            # استعادة النصوص (نحتاج لتخزينها في الزر مسبقاً، للتبسيط هنا نعيد كتابتها)
            # في التطبيق الفعلي يفضل تخزين النص الأصلي داخل NavButton
            btn_texts = ["Cockpit", "Strategy", "Execution", "Lab", "Forensics", "Settings"]
            for i, btn in enumerate(self.buttons):
                btn.setText(btn_texts[i])

        self.collapsed = not self.collapsed

    def _apply_theme(self):
        """تلوين الخلفية"""
        bg = theme_engine.get_color("background")
        border = theme_engine.get_color("grid_line")
        
        self.setStyleSheet(f"""
            SideNavBar {{
                background-color: {bg};
                border-right: 1px solid {border};
            }}
        """)
        
        # تحديث لون الشعار
        primary = theme_engine.get_color("primary")
        self.btn_toggle.setStyleSheet(f"color: {primary}; background: transparent; border: none; text-align: left; padding-left: 15px; font-weight: 900;")