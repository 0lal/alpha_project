# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - UNIFIED FORENSIC LOGGING AGGREGATOR
============================================================
Component Name: ops/telemetry/logging_aggregator.py
Core Responsibility: تجميع السجلات من كافة اللغات في سجل جنائي واحد موحد (Pillar: Explainability).
Creation Date: 2026-02-03
Version: 1.0.0 (Black Box Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يعمل بمثابة "الصندوق الأسود" للطائرة.
- يضمن تسلسل الأحداث (Causality): الحدث A يجب أن يظهر قبل الحدث B.
- يوحد التوقيت (Normalization): يحول كل التوقيتات إلى UTC ISO-8601.
- يضمن عدم التلاعب (Immutability): السجلات تكتب بطريقة الإلحاق (Append-Only).
"""

import os
import json
import time
import logging
import threading
import queue
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pathlib import Path

# إعداد المسارات
LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
FORENSIC_LOG_FILE = LOG_DIR / "alpha_forensic_timeline.jsonl"

@dataclass
class LogEntry:
    """
    بنية البيانات الموحدة للسجل.
    بغض النظر عن المصدر (Rust/Dart/Python)، سيتم تحويل السجل إلى هذا الهيكل.
    """
    timestamp: str          # توقيت دقيق (ISO 8601)
    sequence_id: int        # رقم تسلسلي لكشف فقدان السجلات
    source: str             # المصدر (ENGINE, BRAIN, UI, SYSTEM)
    level: str              # المستوى (INFO, WARN, ERROR, CRITICAL)
    message: str            # نص الرسالة
    metadata: Dict[str, Any] # بيانات إضافية (سعر، رمز، خطأ)

class LoggingAggregator:
    """
    المجمع المركزي للسجلات.
    يستخدم طابوراً (Queue) ومسلكاً منفصلاً (Thread) للكتابة لضمان عدم تعطيل الأداء.
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._sequence_counter = 0
        self._lock = threading.Lock()
        
        # تشغيل عامل الكتابة في الخلفية
        self._worker_thread = threading.Thread(target=self._writer_loop, daemon=True, name="LogWriter")
        self._worker_thread.start()
        
        # تسجيل بداية الجلسة
        self.ingest_system_event("LOGGING_STARTED", "Forensic Aggregator Online")

    def ingest_log(self, source: str, level: str, message: str, metadata: Optional[Dict] = None):
        """
        نقطة الدخول العامة لاستقبال السجلات من أي مكان.
        """
        with self._lock:
            self._sequence_counter += 1
            seq_id = self._sequence_counter

        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            sequence_id=seq_id,
            source=source.upper(),
            level=level.upper(),
            message=message,
            metadata=metadata or {}
        )
        
        # وضع السجل في الطابور للمعالجة غير المتزامنة
        self._queue.put(entry)

    def ingest_rust_log(self, raw_json: str):
        """
        مخصص لاستقبال سجلات المحرك (Rust Engine).
        عادة ما يرسل Rust السجلات عبر ZMQ أو Pipe بصيغة JSON.
        """
        try:
            data = json.loads(raw_json)
            self.ingest_log(
                source="ENGINE",
                level=data.get("level", "INFO"),
                message=data.get("msg", "No message"),
                metadata=data.get("context", {})
            )
        except Exception as e:
            self.ingest_system_event("LOG_ERROR", f"Failed to parse Rust log: {e}")

    def ingest_ui_log(self, raw_json: str):
        """
        مخصص لاستقبال سجلات الواجهة (Flutter UI).
        """
        try:
            data = json.loads(raw_json)
            self.ingest_log(
                source="UI",
                level=data.get("level", "INFO"),
                message=data.get("message", ""),
                metadata=data.get("details", {})
            )
        except Exception as e:
            self.ingest_system_event("LOG_ERROR", f"Failed to parse UI log: {e}")

    def ingest_system_event(self, event_type: str, details: str):
        """
        تسجيل أحداث النظام الداخلية.
        """
        self.ingest_log("SYSTEM", "INFO", event_type, {"details": details})

    def _writer_loop(self):
        """
        الحلقة الخلفية المسؤولة عن الكتابة الفعلية على القرص.
        تستخدم تجميع الدفعات (Batching) لتحسين أداء I/O.
        """
        buffer = []
        last_flush = time.time()
        
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                # محاولة سحب سجل مع مهلة زمنية قصيرة
                entry = self._queue.get(timeout=0.5)
                buffer.append(entry)
            except queue.Empty:
                pass
            
            # الكتابة إذا امتلأ المخزن المؤقت أو مر وقت كافٍ
            current_time = time.time()
            if len(buffer) >= 10 or (buffer and current_time - last_flush > 1.0):
                self._flush_buffer(buffer)
                buffer = []
                last_flush = current_time

    def _flush_buffer(self, buffer: list):
        """
        كتابة القائمة في ملف JSONL (سطر لكل سجل).
        """
        try:
            with open(FORENSIC_LOG_FILE, "a", encoding="utf-8") as f:
                for entry in buffer:
                    # تحويل الكائن إلى نص JSON وكتابته كسطر جديد
                    f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            # إذا فشلت الكتابة على القرص، نطبع في الخطأ القياسي كحل أخير
            print(f"CRITICAL: LOGGING DISK FAILURE: {e}")

    def shutdown(self):
        """
        إغلاق آمن للمجمع.
        """
        self.ingest_system_event("LOGGING_STOPPED", "System Shutdown Initiated")
        self._stop_event.set()
        self._worker_thread.join()

# --- Singleton Instance ---
# لضمان وجود مجمع واحد فقط في العملية
aggregator = LoggingAggregator()

# --- Unit Test ---
if __name__ == "__main__":
    print(f"--- Log Aggregator Test ---")
    print(f"Logs will be written to: {FORENSIC_LOG_FILE}")
    
    # 1. محاكاة سجل من Python
    aggregator.ingest_log("BRAIN", "INFO", "Neural Network Loaded", {"model": "DeepSeek-V2"})
    
    # 2. محاكاة سجل من Rust (عبر JSON)
    rust_msg = json.dumps({"level": "WARN", "msg": "High Latency Detected", "context": {"latency_ms": 150}})
    aggregator.ingest_rust_log(rust_msg)
    
    # 3. محاكاة سجل من UI
    ui_msg = json.dumps({"level": "ERROR", "message": "Connection Lost", "details": {"screen": "Dashboard"}})
    aggregator.ingest_ui_log(ui_msg)
    
    time.sleep(1.5) # انتظار الكتابة
    aggregator.shutdown()
    print("[+] Test Complete. Check the file.")