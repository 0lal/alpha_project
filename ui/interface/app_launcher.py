# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QLabel
from PySide6.QtCore import Qt
from interface.assets.styles import AlphaStyles
from interface.components.sidebar import Sidebar
from interface.pages.advisory_view import AdvisoryView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALPHA SOVEREIGN")
        self.resize(1200, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(AlphaStyles.MASTER)
        
        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        layout.addWidget(self.sidebar)
        
        self.stack = QStackedWidget()
        self.stack.addWidget(QLabel("لوحة القيادة", alignment=Qt.AlignCenter)) # 0
        self.stack.addWidget(AdvisoryView()) # 1
        layout.addWidget(self.stack)
        
        self.switch_page(1)

    def switch_page(self, index):
        if index < self.stack.count():
            self.stack.setCurrentIndex(index)