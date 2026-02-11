# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - EXPLAINABLE AI (XAI) LOGGER
# =================================================================
# Component Name: brain/reasoning/xai_logger.py
# Core Responsibility: تسجيل مسار التفكير والخطوات المنطقية لضمان الشفافية (Explainability Pillar).
# Design Pattern: Structural Logger / Tamper-Evident Ledger
# Forensic Impact: يوفر دليلاً جنائياً غير قابل للتلاعب (Immutable Log) لكل قرار مالي، مما يسمح بإعادة بناء مسرح الجريمة/القرار لاحقاً.
# =================================================================

import logging
import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, Optional

class XaiLogger:
    """
    مسجل الذكاء الاصطناعي القابل للتفسير.
    يختلف عن الـ Logger العادي بأنه يسجل البيانات مهيكلة (Structured Data)
    ويضيف توقيعاً رقمياً (Checksum) لكل سجل لضمان النزاهة.
    """

    def __init__(self, log_dir: str = "./logs/xai"):
        self.logger = logging.getLogger("Alpha.Brain.XAI")
        self.log_dir = log_dir
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # ملف السجل اليومي (JSON Lines format)
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        self.file_path = os.path.join(self.log_dir, f"decision_trace_{date_str}.jsonl")

    def log_decision_trace(self, 
                           trace_id: str,
                           agent_name: str, 
                           inputs: Dict[str, Any],
                           reasoning_chain: List[Dict[str, Any]],
                           final_decision: str,
                           confidence: float) -> str:
        """
        تسجيل عملية اتخاذ قرار كاملة.
        
        Args:
            trace_id: معرف التتبع الفريد (من CoT Engine).
            agent_name: اسم الوكيل المسؤول (مثل 'BrainRouter').
            inputs: البيانات التي دخلت للنظام (Context).
            reasoning_chain: خطوات التفكير (CoT Steps).
            final_decision: القرار النهائي (BUY/SELL/HOLD).
            confidence: درجة الثقة.
            
        Returns:
            The Integrity Hash (SHA-256) of the record.
        """
        timestamp = datetime.utcnow().isoformat()
        
        # 1. بناء هيكل السجل
        record = {
            "version": "1.0",
            "timestamp": timestamp,
            "trace_id": trace_id,
            "agent": agent_name,
            "context_snapshot": self._sanitize_inputs(inputs),
            "logic_path": reasoning_chain,
            "outcome": final_decision,
            "confidence_score": confidence,
            "metadata": {
                "system_mode": "LIVE", # or SIMULATION
                "risk_level": "HIGH" if confidence < 0.7 else "LOW"
            }
        }

        # 2. التوقيع الرقمي (Cryptographic Hashing)
        # نقوم بتحويل السجل لنص وتشفيره لضمان عدم التلاعب به لاحقاً
        # sort_keys=True يضمن ترتيباً ثابتاً للمفاتيح ليكون الهاش متطابقاً دائماً
        serialized_record = json.dumps(record, sort_keys=True)
        integrity_hash = hashlib.sha256(serialized_record.encode('utf-8')).hexdigest()
        
        record["integrity_hash"] = integrity_hash

        # 3. الكتابة للملف (Append Mode)
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            self.logger.error(f"XAI_WRITE_FAIL: Could not write XAI log! Error: {e}")

        return integrity_hash

    def audit_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        استرجاع سجل قرار معين للتحقيق الجنائي.
        """
        try:
            if not os.path.exists(self.file_path):
                return None

            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    if record.get("trace_id") == trace_id:
                        # التحقق من سلامة البيانات عند القراءة
                        stored_hash = record.pop("integrity_hash")
                        recalc_hash = hashlib.sha256(json.dumps(record, sort_keys=True).encode('utf-8')).hexdigest()
                        
                        if stored_hash != recalc_hash:
                            self.logger.critical(f"TAMPER_ALERT: Log entry {trace_id} has been modified externally!")
                            record["_integrity_check"] = "FAILED"
                        else:
                            record["_integrity_check"] = "PASSED"
                            
                        return record
            return None
        except Exception as e:
            self.logger.error(f"AUDIT_ERROR: {e}")
            return None

    def _sanitize_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        تنظيف المدخلات لتوفير المساحة.
        لا نحتاج لتسجيل كل نقطة بيانات تاريخية، فقط الملخصات.
        """
        sanitized = {}
        for k, v in inputs.items():
            # إذا كانت البيانات ضخمة (مثل مصفوفة 1000 شمعة)، نختصرها
            if isinstance(v, list) and len(v) > 10:
                sanitized[k] = f"List[len={len(v)}]"
            elif isinstance(v, dict) and len(v) > 20:
                sanitized[k] = f"Dict[keys={len(v)}]"
            else:
                sanitized[k] = v
        return sanitized