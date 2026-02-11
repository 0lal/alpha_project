# Cognitive Snapshot Manager


# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - STATE PERSISTENCE & RECOVERY SERVICE
# =================================================================
# Component Name: brain/state_manager_service.py
# Core Responsibility: حفظ لقطات (Snapshots) للوعي الرقمي لضمان استمرارية التفكير (Stability Pillar).
# Design Pattern: Memento / Atomic Persistence
# Forensic Impact: يمكن استخدام ملفات الحالة (Dump Files) لتحليل ما كان يحتويه "عقل" النظام لحظة الانهيار.
# =================================================================

import logging
import json
import os
import shutil
import hashlib
import time
from typing import Dict, Any, Optional
from datetime import datetime

class StateManagerService:
    """
    مدير الحالة.
    مسؤول عن تجميد (Freeze) وإذابة (Thaw) حالة النظام.
    يستخدم تقنيات الكتابة الذرية لضمان عدم تلف ملف الحالة حتى لو انقطعت الطاقة أثناء الكتابة.
    """

    def __init__(self, storage_dir: str = "./data/state_snapshots"):
        self.logger = logging.getLogger("Alpha.Brain.StateMgr")
        self.storage_dir = storage_dir
        
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        # ملف الحالة الرئيسي والنسخة الاحتياطية
        self.current_state_file = os.path.join(self.storage_dir, "brain_state.json")
        self.backup_state_file = os.path.join(self.storage_dir, "brain_state.bak")

    def capture_snapshot(self, 
                         brain_components: Dict[str, Any], 
                         trigger: str = "SCHEDULED") -> bool:
        """
        أخذ لقطة فورية لحالة النظام وتخزينها.
        
        Args:
            brain_components: قاموس يحتوي على كائنات النظام (Memory, Router, etc.) لاستخراج حالتها.
            trigger: سبب أخذ اللقطة (e.g., "PRE_TRADE", "SHUTDOWN", "CRASH_HANDLER").
        """
        try:
            # 1. تجميع البيانات (Serialization)
            # نطلب من كل مكون استخراج حالته الداخلية القابلة للتخزين
            state_payload = {
                "meta": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "trigger": trigger,
                    "version": "1.0",
                    "boot_id": self._get_boot_id()
                },
                "components": {}
            }

            # استخراج حالة الذاكرة العرضية (المزاج، التوتر)
            if "episodic_memory" in brain_components:
                # نفترض أن EpisodicMemory لديها دالة export_state
                # هنا نحاكي استخراج البيانات مباشرة
                mem = brain_components["episodic_memory"]
                state_payload["components"]["episodic_memory"] = mem.state if hasattr(mem, "state") else {}

            # استخراج حالة مدير المخاطر
            if "exposure_agent" in brain_components:
                # نحتاج معرفة الصفقات المفتوحة والتعرض الحالي
                pass # (Implementation specific)

            # استخراج حالة الـ Circuit Breakers
            if "model_selector" in brain_components:
                pass 

            # 2. حساب التوقيع (Checksum)
            # لضمان عدم تحميل ملف تالف لاحقاً
            serialized_data = json.dumps(state_payload, indent=2)
            checksum = hashlib.sha256(serialized_data.encode()).hexdigest()
            state_payload["integrity_hash"] = checksum
            
            # إعادة السيريالايز مع الهاش
            final_data = json.dumps(state_payload, indent=2)

            # 3. الكتابة الذرية (Atomic Write)
            return self._atomic_write(final_data)

        except Exception as e:
            self.logger.error(f"SNAPSHOT_FAIL: Failed to capture state: {e}")
            return False

    def load_last_state(self) -> Optional[Dict[str, Any]]:
        """
        محاولة استعادة آخر حالة معروفة (Recovery).
        """
        # محاولة قراءة الملف الرئيسي
        state = self._read_and_verify(self.current_state_file)
        
        if state:
            self.logger.info("STATE_RECOVERY: Successfully loaded primary brain state.")
            return state
            
        self.logger.warning("STATE_WARN: Primary state corrupted or missing. Trying backup...")
        
        # محاولة قراءة النسخة الاحتياطية
        state = self._read_and_verify(self.backup_state_file)
        
        if state:
            self.logger.info("STATE_RECOVERY: Restored from backup state.")
            return state
            
        self.logger.critical("STATE_LOSS: No valid state found. Starting with AMNESIA (Clean Slate).")
        return None

    def _atomic_write(self, data_str: str) -> bool:
        """
        الكتابة الآمنة.
        1. اكتب لملف مؤقت.
        2. تأكد من الكتابة للقرص (fsync).
        3. انسخ الملف الحالي إلى backup.
        4. أعد تسمية المؤقت إلى الحالي (Atomic Rename).
        """
        tmp_file = self.current_state_file + ".tmp"
        
        try:
            # 1. الكتابة للمؤقت
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(data_str)
                f.flush()
                os.fsync(f.fileno()) # إجبار نظام التشغيل على الكتابة الفيزيائية

            # 2. تدوير الملفات (Rotation)
            if os.path.exists(self.current_state_file):
                shutil.copy2(self.current_state_file, self.backup_state_file)

            # 3. الاستبدال الذري
            # os.replace هو عملية ذرية في أنظمة POSIX و Windows الحديثة
            os.replace(tmp_file, self.current_state_file)
            
            return True

        except Exception as e:
            self.logger.error(f"ATOMIC_WRITE_ERROR: {e}")
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            return False

    def _read_and_verify(self, filepath: str) -> Optional[Dict[str, Any]]:
        """قراءة الملف والتحقق من صحة الهاش."""
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            stored_hash = data.pop("integrity_hash", None)
            if not stored_hash:
                return None
                
            # إعادة الحساب
            recalc_hash = hashlib.sha256(json.dumps(data, indent=2).encode()).hexdigest()
            
            if stored_hash == recalc_hash:
                return data
            else:
                self.logger.error(f"INTEGRITY_FAIL: Corrupted state file: {filepath}")
                return None
                
        except Exception as e:
            self.logger.error(f"READ_ERROR: {e}")
            return None

    def _get_boot_id(self) -> str:
        """معرف فريد للجلسة الحالية (لتمييز الانهيارات)."""
        # في بيئة حقيقية قد نستخدم ملف PID أو متغير بيئة
        return str(int(time.time()))