# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - GENETIC VERSION CONTROL MANAGER
======================================================
Component Name: ops/auto_patcher/version_control_mgr.py
Core Responsibility: إدارة إصدارات "الوعي الرقمي" وضمان القدرة على التراجع (Pillar: Stability).
Creation Date: 2026-02-03
Version: 1.0.0 (Time-Travel Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يعمل كـ "كاتب العدل" (Notary Public) للنظام.
لا يتم اعتماد أي سطر كود جديد يكتبه الذكاء الاصطناعي إلا بعد:
1. تصوير الحالة الحالية (Snapshot).
2. تسجيل سبب التغيير (Mutation Reason).
3. الحصول على معرف فريد (Commit Hash) للرجوع إليه عند الطوارئ.
"""

import subprocess
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# إعداد السجلات
logger = logging.getLogger("AlphaVCS")

class VersionControlManager:
    """
    غلاف برمجي حول نظام Git لإدارة دورة حياة الكود ذاتي التعديل.
    يوفر واجهة آمنة للقيام بعمليات Commit و Rollback برمجياً.
    """

    def __init__(self, repo_path: str = "."):
        """
        تهيئة مدير النسخ.
        :param repo_path: مسار الجذر للمستودع (Repository Root).
        """
        self.repo_path = os.path.abspath(repo_path)
        self._verify_git_repo()

    def _verify_git_repo(self):
        """
        التحقق من أن المسار هو بالفعل مستودع Git صالح.
        """
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            logger.critical(f"FATAL: No .git directory found in {self.repo_path}. Version control disabled.")
            raise EnvironmentError("System is not running inside a Git repository.")

    def _run_git_cmd(self, args: List[str]) -> Tuple[bool, str]:
        """
        تنفيذ أوامر Git من خلال الصدفة (Shell) بأمان.
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    def create_snapshot(self, message: str, author: str = "AlphaAI") -> Optional[str]:
        """
        إنشاء نقطة استعادة (Snapshot) قبل تطبيق أي تعديلات خطيرة.
        يقوم بعمل Commit للتغييرات الحالية.
        
        :return: الـ Commit Hash الجديد في حالة النجاح.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[AUTO-MUTATION] {message} | Author: {author} | Time: {timestamp}"

        logger.info(f"Creating genetic snapshot: {message}")

        # 1. إضافة كل الملفات (Stage All)
        ok, out = self._run_git_cmd(["add", "."])
        if not ok:
            logger.error(f"Failed to stage files: {out}")
            return None

        # 2. التحقق مما إذا كان هناك شيء للتغيير
        ok, status = self._run_git_cmd(["status", "--porcelain"])
        if not ok or not status:
            logger.warning("No changes detected to commit.")
            return self.get_current_head_hash()

        # 3. الالتزام بالتغيير (Commit)
        # نستخدم --allow-empty لتجنب الأخطاء إذا لم تكن هناك تغييرات فعلية
        ok, out = self._run_git_cmd(["commit", "-m", full_message])
        if ok:
            new_hash = self.get_current_head_hash()
            logger.info(f"Snapshot created successfully. Hash: {new_hash}")
            return new_hash
        else:
            logger.error(f"Failed to commit snapshot: {out}")
            return None

    def emergency_rollback(self, steps: int = 1) -> bool:
        """
        زر الطوارئ الأحمر.
        يقوم بإلغاء التغييرات الأخيرة والعودة إلى الحالة المستقرة السابقة.
        يستخدم: git reset --hard
        """
        logger.warning(f"INITIATING EMERGENCY ROLLBACK ({steps} steps back)...")
        
        # استخدام reset --hard هو الخيار الوحيد لضمان تطابق الكود مع السجل
        ok, out = self._run_git_cmd(["reset", "--hard", f"HEAD~{steps}"])
        
        if ok:
            logger.info(f"System successfully rolled back. Current Head: {out}")
            return True
        else:
            logger.critical(f"ROLLBACK FAILED: {out}. System might be in inconsistent state!")
            return False

    def get_current_head_hash(self) -> str:
        """
        الحصول على البصمة الوراثية الحالية (Commit Hash).
        """
        ok, out = self._run_git_cmd(["rev-parse", "--short", "HEAD"])
        return out if ok else "UNKNOWN"

    def get_mutation_log(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        استرجاع سجل التغييرات لعرضه في لوحة التحكم (Forensics UI).
        """
        # Format: Hash|Date|Message
        ok, out = self._run_git_cmd(["log", f"-{limit}", "--pretty=format:%h|%cd|%s", "--date=iso"])
        
        logs = []
        if ok and out:
            for line in out.split('\n'):
                try:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        logs.append({
                            "hash": parts[0],
                            "date": parts[1],
                            "message": parts[2]
                        })
                except:
                    continue
        return logs

    def has_uncommitted_changes(self) -> bool:
        """
        فحص ما إذا كان النظام "ملوثاً" بتغييرات غير محفوظة.
        """
        ok, out = self._run_git_cmd(["status", "--porcelain"])
        return ok and len(out.strip()) > 0

# --- Unit Test ---
if __name__ == "__main__":
    # اختبار بسيط (يتطلب أن يكون المجلد الحالي مستودع git)
    try:
        vcs = VersionControlManager()
        print(f"Current Genetic Hash: {vcs.get_current_head_hash()}")
        
        if vcs.has_uncommitted_changes():
            print("WARNING: Uncommitted changes detected!")
        else:
            print("System is clean.")
            
        # محاكاة حفظ نسخة
        # vcs.create_snapshot("Test Snapshot from Script")
        
    except Exception as e:
        print(f"VCS Initialization Failed: {e}")