# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - INTRUSION DETECTION SYSTEM (IDS)
=================================================================
Component: shield/perimeter/ids_intrusion_detector.py
Core Responsibility: نظام كشف التسلل والمحاولات الخارجية غير المصرح بها (Security Pillar).
Design Pattern: Anomaly Detection / Whitelisting
Forensic Impact: يسجل أي عنوان IP غريب يحاول الاتصال بالمنافذ الحساسة، ويطلق إنذاراً فورياً، كما يراقب سلامة الملفات.
=================================================================
"""

import time
import threading
import logging
import psutil
import hashlib
import os
from typing import Set, Dict, List

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.ids")

class IntrusionDetector:
    def __init__(self, check_interval: int = 10):
        self.interval = check_interval
        self._running = False
        self._thread = None
        
        # 1. القائمة البيضاء (Whitelisting)
        # العناوين المسموح لها بالاتصال بالمحرك (Localhost, Docker Internal IPs)
        self.TRUSTED_IPS: Set[str] = {
            "127.0.0.1", 
            "::1", 
            "172.17.0.1", # افتراض بوابة دوكر
            "0.0.0.0"     # للسوكيت المستمعة (Listening)
        }
        
        # المنافذ الحساسة التي يجب حمايتها بصرامة (gRPC, ZMQ, Web Dashboard)
        self.CRITICAL_PORTS: Set[int] = {50051, 5555, 8080}

        # 2. بصمات الملفات (File Integrity Monitoring)
        # نراقب الملفات الحساسة للكشف عن أي تعديل خبيث أو حقن أكواد
        self.monitored_files = [
            "config/settings.toml",
            "shield/crypto/secrets.key",
            "shield/sentinel/dead_man_switch.py" # حماية كود الوصية الأخيرة
        ]
        self.file_hashes: Dict[str, str] = {}
        
        # حساب البصمات الأولية عند التشغيل
        self._calculate_initial_hashes()

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._surveillance_loop, daemon=True)
        self._thread.start()
        logger.info("IDS: Intrusion Detector activated. Monitoring Perimeter & Filesystem.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _surveillance_loop(self):
        """حلقة المراقبة المستمرة"""
        while self._running:
            try:
                # أ. فحص الشبكة (Network Perimeter Scan)
                self._scan_network_connections()
                
                # ب. فحص سلامة الملفات (File Integrity Scan)
                self._check_file_integrity()
                
            except Exception as e:
                logger.error(f"IDS_ERR: Surveillance loop error: {e}")
            
            time.sleep(self.interval)

    def _scan_network_connections(self):
        """
        فحص جميع الاتصالات الشبكية الحالية.
        القاعدة: أي اتصال بمنفذ حساس من IP غير موجود في القائمة البيضاء هو هجوم.
        """
        try:
            # kind='inet' لجلب اتصالات IPv4 و IPv6
            for conn in psutil.net_connections(kind='inet'):
                # تجاهل الاتصالات المغلقة، نركز على النشطة والمستمعة
                if conn.status not in [psutil.CONN_ESTABLISHED, psutil.CONN_LISTEN]:
                    continue

                laddr = conn.laddr
                raddr = conn.raddr # Remote Address (الطرف الآخر)

                # هل المنفذ الذي يتم الاتصال به هو منفذ حساس؟
                if laddr.port in self.CRITICAL_PORTS:
                    # إذا كان الاتصال قائماً (ESTABLISHED)، تحقق من هوية المتصل
                    if conn.status == psutil.CONN_ESTABLISHED and raddr:
                        remote_ip = raddr.ip
                        
                        if remote_ip not in self.TRUSTED_IPS:
                            self._trigger_intrusion_alert(
                                "UNAUTHORIZED_NETWORK_ACCESS", 
                                f"Unknown IP {remote_ip} connected to critical port {laddr.port}!"
                            )
                            # [Forensic Note] هنا يمكننا إضافة منطق لقطع الاتصال فوراً (Kill TCP Connection)
        except Exception as e:
            logger.error(f"IDS_ERR: Network scan failed: {e}")

    def _calculate_initial_hashes(self):
        """حساب البصمات الأولية للملفات كمرجع (Baseline)"""
        for file_path in self.monitored_files:
            if os.path.exists(file_path):
                self.file_hashes[file_path] = self._get_file_hash(file_path)

    def _check_file_integrity(self):
        """
        التأكد من أن الملفات الحساسة لم يتم تعديلها منذ بدء التشغيل.
        """
        for file_path, original_hash in self.file_hashes.items():
            if not os.path.exists(file_path):
                self._trigger_intrusion_alert("FILE_MISSING", f"Critical file vanished: {file_path}")
                continue
            
            current_hash = self._get_file_hash(file_path)
            if current_hash != original_hash:
                self._trigger_intrusion_alert("FILE_TAMPERING", f"Critical file modified: {file_path}")
                # تحديث الهاش مؤقتاً لمنع إغراق السجلات، لكن الضرر قد وقع
                self.file_hashes[file_path] = current_hash

    def _get_file_hash(self, path: str) -> str:
        """حساب هاش SHA-256 للملف (بصمة رقمية)"""
        try:
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                # قراءة الملف كتل لتوفير الذاكرة
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""

    def _trigger_intrusion_alert(self, alert_type: str, details: str):
        """إطلاق صافرات الإنذار"""
        logger.critical(f"IDS_ALARM: [{alert_type}] {details}")
        # هنا يتم ربط النظام بـ DeadManSwitch أو SelfHealingLogic لعزل النظام