# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton
from interface.assets.styles import AlphaColors

class ChatBox(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.cb = callback
        layout = QVBoxLayout(self)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"background: #0D0D0D; border: 1px solid #333; border-radius: 8px;")
        
        inp_lay = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("أمر التحليل...")
        self.inp.setStyleSheet("background: #151515; border: 1px solid #333; padding: 10px;")
        self.inp.returnPressed.connect(self.send)
        
        btn = QPushButton("إرسال")
        btn.setStyleSheet(f"background: {AlphaColors.ACCENT}; color: black; font-weight: bold; padding: 10px;")
        btn.clicked.connect(self.send)
        
        inp_lay.addWidget(self.inp); inp_lay.addWidget(btn)
        layout.addWidget(self.log); layout.addLayout(inp_lay)

    def send(self):
        t = self.inp.text()
        if t:
            self.log.append(f"<br><b>أنت:</b> {t}")
            self.cb(t)
            self.inp.clear()

    def add_msg(self, t):
        self.log.append(f"<b style='color:{AlphaColors.ACCENT}'>ألفا:</b> {t}")