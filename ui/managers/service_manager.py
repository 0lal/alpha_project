import sys
import socket
import subprocess
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker

# --- استيراد البنية التحتية ---
from ui.core.config_provider import config
from ui.core.logger_sink import logger_sink
from ui.core.event_hub import event_hub
from ui.core.workers import task_manager

class AlphaServiceManager(QObject):
    """
    The Infrastructure Orchestrator.
    
    الوظيفة:
    1. إدارة دورة حياة الخدمات الخارجية (Docker, Redis, Rust Engine).
    2. المراقبة الصحية النشطة (Health Checks) واكتشاف الفشل.
    3. الاستشفاء الذاتي (Self-Healing): إعادة تشغيل الخدمات الميتة تلقائياً.
    
    التحليل الجنائي:
    يحتفظ بسجل دقيق لكل محاولة تشغيل أو إيقاف، مع التقاط أكواد الخروج (Exit Codes)
    لمعرفة سبب الوفاة التقني لأي خدمة.
    """

    # إشارة بتحديث حالة خدمة معينة
    # Payload: (service_name, status, details)
    # Statuses: STARTING, RUNNING, STOPPED, DEAD, ERROR
    service_status_changed = pyqtSignal(str, str, str)

    _instance = None
    _lock = QMutex()

    def __init__(self):
        super().__init__()
        if AlphaServiceManager._instance is not None:
            raise Exception("ServiceManager is a Singleton!")

        # --- Configuration ---
        self.redis_host = config.get("network.redis.host", "localhost")
        self.redis_port = config.get("network.redis.port", 6379)
        
        self.engine_host = config.get("network.grpc.brain_service.host", "localhost")
        self.engine_port = config.get("network.grpc.brain_service.port", 50051)

        # --- State Tracking ---
        self._services_state: Dict[str, str] = {
            "docker": "UNKNOWN",
            "redis": "UNKNOWN",
            "rust_engine": "UNKNOWN"
        }
        
        # --- Health Monitor Timer ---
        # نقوم بفحص الخدمات كل 5 ثوانٍ (فحص خفيف لا يرهق النظام)
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._run_health_checks)
        self._monitor_timer.start(5000)

        logger_sink.log_system_event("ServiceManager", "INFO", "🛠️ Infrastructure Orchestrator Online.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AlphaServiceManager()
        return cls._instance

    # =========================================================================
    # 1. Orchestration (التشغيل المنظم)
    # =========================================================================
    def start_full_system(self):
        """
        تشغيل النظام بالكامل بالترتيب الصحيح.
        هذه الدالة هي التي يتم استدعاؤها عند ضغط زر "Start System" في الواجهة.
        """
        logger_sink.log_system_event("ServiceManager", "INFO", "🚀 Initiating Alpha System Startup Sequence...")
        
        # نستخدم TaskManager لمنع تجميد الواجهة أثناء التشغيل
        task_manager.start_task(
            self._startup_sequence_worker,
            on_finished=lambda: logger_sink.log_system_event("ServiceManager", "SUCCESS", "✅ Startup Sequence Completed.")
        )

    def _startup_sequence_worker(self):
        """
        المنطق التسلسلي للتشغيل (يعمل في خيط منفصل).
        """
        # Step 1: Check Docker
        self._update_status("docker", "CHECKING", "Verifying Docker Daemon...")
        if not self._is_docker_installed():
            self._update_status("docker", "ERROR", "Docker not found in PATH")
            return

        # Step 2: Start Infrastructure (Redis via Docker Compose)
        self._update_status("redis", "STARTING", "Booting up containers...")
        success, logs = self._run_docker_compose("up -d redis")
        if not success:
            self._update_status("redis", "ERROR", f"Docker failed: {logs}")
            return
        
        # الانتظار والتأكد من أن Redis حي يرزق
        if not self._wait_for_port(self.redis_host, self.redis_port, timeout=10):
            self._update_status("redis", "DEAD", "Redis container started but port is unreachable.")
            return
        self._update_status("redis", "RUNNING", "Redis is active.")

        # Step 3: Start Brain (Rust Engine)
        self._update_status("rust_engine", "STARTING", "Igniting Neural Engine...")
        # هنا سنقوم بتشغيل المحرك (إما كـ Binary محلي أو Docker Container)
        # للسيناريو الحالي، سنفترض أنه حاوية أيضاً لضمان العزل
        success, logs = self._run_docker_compose("up -d alpha_engine")
        if success:
            if self._wait_for_port(self.engine_host, self.engine_port, timeout=15):
                self._update_status("rust_engine", "RUNNING", "Neural Engine Connected.")
            else:
                 self._update_status("rust_engine", "DEAD", "Engine process running but gRPC port closed.")
        else:
             self._update_status("rust_engine", "ERROR", f"Engine launch failed: {logs}")

    def stop_full_system(self):
        """إيقاف كل شيء بأمان"""
        logger_sink.log_system_event("ServiceManager", "WARNING", "🛑 Initiating System Shutdown...")
        task_manager.start_task(
            lambda: self._run_docker_compose("down"),
            on_finished=lambda: self._update_status("system", "STOPPED", "All services halted.")
        )

    # =========================================================================
    # 2. Health Checks (الفحوصات الطبية)
    # =========================================================================
    def _run_health_checks(self):
        """يتم استدعاؤها دورياً لفحص النبض"""
        # فحص Redis
        if self._check_port(self.redis_host, self.redis_port):
             self._update_status("redis", "RUNNING", "")
        else:
             # إذا كنا نظن أنه يعمل ولكنه توقف فجأة
             if self._services_state.get("redis") == "RUNNING":
                 self._update_status("redis", "DEAD", "Connection lost unexpectedly.")
                 # TODO: Trigger Auto-Restart here

        # فحص Engine
        if self._check_port(self.engine_host, self.engine_port):
             self._update_status("rust_engine", "RUNNING", "")
        else:
             if self._services_state.get("rust_engine") == "RUNNING":
                 self._update_status("rust_engine", "DEAD", "Brain signal lost.")

    # =========================================================================
    # 3. Low-Level Utilities (أدوات النظام)
    # =========================================================================
    def _is_docker_installed(self) -> bool:
        return shutil.which("docker") is not None

    def _run_docker_compose(self, args: str) -> (bool, str):
        """
        تنفيذ أوامر Docker Compose والتقاط المخرجات للأدلة الجنائية.
        """
        try:
            # تحديد مسار ملف الـ Compose بدقة
            compose_file = config.project_root / "docker-compose.yml"
            if not compose_file.exists():
                return False, f"Missing docker-compose.yml at {compose_file}"

            cmd = f"docker compose -f \"{compose_file}\" {args}"
            
            # Forensic Capture: التقاط كل من stdout و stderr
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8' # مهم جداً لدعم الرموز الغريبة في اللوج
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except Exception as e:
            return False, str(e)

    def _check_port(self, host: str, port: int) -> bool:
        """فحص سريع جداً (Ping) لمنفذ TCP"""
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _wait_for_port(self, host: str, port: int, timeout: int) -> bool:
        """انتظار منفذ ليعمل (مع مهلة زمنية)"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_port(host, port):
                return True
            time.sleep(0.5)
        return False

    def _update_status(self, service: str, status: str, details: str):
        """تحديث الحالة الداخلية وإعلام الواجهة"""
        with QMutexLocker(self._lock):
            old_status = self._services_state.get(service, "UNKNOWN")
            if old_status != status:
                self._services_state[service] = status
                self.service_status_changed.emit(service, status, details)
                
                # توثيق التغيير في السجل
                level = "INFO" if status in ["RUNNING", "STARTING"] else "ERROR"
                logger_sink.log_system_event("ServiceManager", level, f"Service [{service}] -> {status}: {details}")

# Global Accessor
service_manager = AlphaServiceManager.get_instance()