# -*- coding: utf-8 -*-
from PySide6.QtCore import QThread, Signal
from core.bridge import SystemBridge

class BrainWorker(QThread):
    response_received = Signal(str)
    def __init__(self):
        super().__init__()
        self.bridge = SystemBridge()
        self.pending_text = None

    def run(self):
        if self.pending_text:
            resp = self.bridge.process_user_query(self.pending_text)
            self.response_received.emit(resp)
            self.pending_text = None

    def analyze(self, text):
        self.pending_text = text
        self.start()