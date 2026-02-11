# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from interface.assets.styles import AlphaStyles, AlphaColors

class Sidebar(QFrame):
    page_changed = Signal(int)
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {AlphaColors.SURFACE}; min-width: 220px;")
        layout = QVBoxLayout(self)
        
        title = QLabel("ALPHA\nSOVEREIGN")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {AlphaColors.ACCENT}; font-weight: bold; font-size: 20px; margin: 20px;")
        layout.addWidget(title)
        
        self.btns = []
        for i, txt in enumerate(["القيادة", "الشورى", "السجلات"]):
            btn = QPushButton(txt)
            btn.setStyleSheet(AlphaStyles.BTN_SIDEBAR)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, x=i: self.clk(x))
            layout.addWidget(btn)
            self.btns.append(btn)
        
        layout.addStretch()
        self.clk(1)

    def clk(self, idx):
        self.page_changed.emit(idx)
        for i, b in enumerate(self.btns):
            b.setProperty("active", i == idx)
            b.style().unpolish(b); b.style().polish(b)