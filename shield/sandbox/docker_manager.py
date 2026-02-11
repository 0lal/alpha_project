# Container Orchestrator

# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - DOCKER SANDBOX MANAGER
=================================================================
Component: shield/sandbox/docker_manager.py
Core Responsibility: إدارة بيئات التنفيذ المعزولة للأكواد غير الموثوقة (Security Pillar).
Design Pattern: Sandbox / Facade
Forensic Impact: يوفر عزلاً تاماً. إذا انفجر الكود، فإنه يدمر الحاوية فقط ولا يمس المحرك الرئيسي.
=================================================================
"""

import docker
from docker.errors import APIError, ImageNotFound, ContainerError
from docker.models.containers import Container
import logging
from typing import Dict, List, Optional, Union

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.docker")

class SandboxConfig:
    """إعدادات الأمان للحاوية (The Jail Constraints)"""
    def __init__(
        self, 
        image: str, 
        mem_limit: str = "512m", 
        cpu_quota: int = 50000, # 50% of a core
        network_enabled: bool = False,
        read_only_root: bool = True
    ):
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.network_enabled = network_enabled
        self.read_only_root = read_only_root

class DockerSandboxManager:
    def __init__(self):
        try:
            # الاتصال بمحرك Docker المحلي
            self.client = docker.from_env()
            logger.info("SHIELD_DOCKER: Connected to Docker Engine successfully.")
        except Exception as e:
            logger.critical(f"SHIELD_DOCKER: Failed to connect to Docker daemon! {e}")
            raise RuntimeError("Docker is required for the Shield module.")

    def create_sandbox(
        self, 
        config: SandboxConfig, 
        command: Optional[str] = None, 
        environment: Dict[str, str] = None,
        name: str = None
    ) -> Optional[Container]:
        """
        إنشاء وتشغيل حاوية معزولة (The Cell).
        """
        try:
            logger.info(f"SANDBOX: Spawning container from image '{config.image}'...")
            
            # تحديد سياسة الشبكة
            network_mode = "bridge" if config.network_enabled else "none"

            # إنشاء الحاوية مع تشديد أمني أقصى
            container = self.client.containers.run(
                image=config.image,
                command=command,
                name=name,
                detach=True, # تشغيل في الخلفية
                
                # 1. قيود الموارد (Resource Limits)
                mem_limit=config.mem_limit,
                cpu_quota=config.cpu_quota,
                cpu_period=100000,
                
                # 2. العزل الشبكي (Network Isolation)
                network_mode=network_mode,
                
                # 3. عزل نظام الملفات (Filesystem Isolation)
                read_only=config.read_only_root, # نظام ملفات للقراءة فقط
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=64m'}, # مساحة مؤقتة صغيرة للكتابة
                
                # 4. إسقاط الصلاحيات (Capability Dropping)
                # هذا يمنع الحاوية من العبث بالنواة (Kernel) حتى لو كانت Root
                cap_drop=['ALL'],
                
                # 5. متغيرات البيئة
                environment=environment or {},
                
                # 6. منع إعادة التشغيل التلقائي (Fail-Fast)
                restart_policy={"Name": "no"}
            )
            
            logger.info(f"SANDBOX: Container started. ID: {container.short_id} | Name: {container.name}")
            return container

        except ImageNotFound:
            logger.error(f"SANDBOX_ERR: Image '{config.image}' not found locally.")
            # هنا يمكن إضافة منطق لسحب الصورة (pull) تلقائياً
            return None
        except APIError as e:
            logger.error(f"SANDBOX_ERR: Docker API Error: {e}")
            return None

    def stop_sandbox(self, container_id: str, force: bool = False):
        """إيقاف الحاوية (The Termination)"""
        try:
            container = self.client.containers.get(container_id)
            if force:
                container.kill()
                logger.warning(f"SANDBOX: Container {container_id[:12]} KILLED.")
            else:
                container.stop(timeout=5)
                logger.info(f"SANDBOX: Container {container_id[:12]} stopped gracefully.")
        except Exception as e:
            logger.error(f"SANDBOX_ERR: Failed to stop container {container_id}: {e}")

    def cleanup_sandbox(self, container_id: str):
        """حذف الحاوية وتنظيف الأدلة (Evidence Disposal)"""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"SANDBOX: Container {container_id[:12]} removed.")
        except Exception as e:
            logger.error(f"SANDBOX_ERR: Cleanup failed for {container_id}: {e}")

    def get_logs(self, container_id: str) -> str:
        """استخراج السجلات للتحليل الجنائي (Forensic Extraction)"""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(stdout=True, stderr=True)
            return logs.decode('utf-8')
        except Exception as e:
            logger.error(f"SANDBOX_ERR: Could not retrieve logs for {container_id}: {e}")
            return ""

    def inspect_stats(self, container_id: str) -> Dict:
        """مراقبة استهلاك الموارد لحظياً"""
        try:
            container = self.client.containers.get(container_id)
            return container.stats(stream=False)
        except Exception as e:
            return {"error": str(e)}

# مثال للاستخدام (للتوثيق فقط)
if __name__ == "__main__":
    # تهيئة المدير
    manager = DockerSandboxManager()
    
    # إعداد سجن مشدد: بايثون، 128 ميجا رام، بدون إنترنت، للقراءة فقط
    config = SandboxConfig(
        image="python:3.9-slim",
        mem_limit="128m",
        network_enabled=False,
        read_only_root=True
    )
    
    # تشغيل كود تجريبي يطبع "Hello Sandbox"
    container = manager.create_sandbox(
        config=config,
        command='python -c "print(\'Hello form inside the Shield Sandbox!\')"'
    )
    
    if container:
        import time
        time.sleep(2)
        print(f"--- LOGS ---\n{manager.get_logs(container.id)}")
        manager.cleanup_sandbox(container.id)