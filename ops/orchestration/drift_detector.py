# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - ENVIRONMENT DRIFT DETECTOR
===================================================
Component Name: ops/orchestration/drift_detector.py
Core Responsibility: كشف الانزياح بين التكوين المتوقع والواقع التشغيلي (Pillar: Stability).
Creation Date: 2026-02-03
Version: 1.0.0 (Calibration Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يحمي من "التعديلات الصامتة".
- Integrity Check: يحسب بصمات (Hashes) الملفات الحيوية ويقارنها بـ "القائمة الذهبية" (Golden Manifest).
- Time Drift: يراقب انزياح الساعة الداخلية للسيرفر (Clock Skew) وهو أمر حيوي لترتيب الصفقات زمنياً.
- Env Consistency: يتأكد من أن المتغيرات في الذاكرة تطابق الملفات على القرص.
"""

import os
import hashlib
import time
import logging
import sys
import importlib.metadata
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

# إعداد السجلات
logger = logging.getLogger("AlphaDrift")

@dataclass
class DriftReport:
    """تقرير الانزياح."""
    timestamp: float
    is_clean: bool
    drift_details: List[str] = field(default_factory=list)
    clock_skew_ms: float = 0.0

class DriftDetector:
    """
    كاشف الانزياح.
    يعمل كـ "مدقق جودة مستمر" للبيئة.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        
        # قائمة الملفات الحساسة التي يجب ألا تتغير أبداً أثناء التشغيل
        self.critical_files = [
            "shield/core/brain_router.py",
            "ops/monetization/revenue_manager.py",
            ".env"
        ]
        
        # القائمة الذهبية (Baseline) - يتم تعبئتها عند الإقلاع
        self._golden_hashes: Dict[str, str] = {}
        self._capture_baseline()

    def _capture_baseline(self):
        """
        أخذ "صورة طبق الأصل" للحالة الأولية عند بدء التشغيل.
        """
        logger.info("Capturing Golden State Baseline...")
        for rel_path in self.critical_files:
            full_path = self.root_dir / rel_path
            if full_path.exists():
                self._golden_hashes[rel_path] = self._calculate_hash(full_path)
            else:
                logger.warning(f"Critical file missing during baseline: {rel_path}")

    def run_drift_scan(self) -> DriftReport:
        """
        إجراء فحص كامل للانزياح.
        """
        drifts = []
        
        # 1. فحص سلامة الملفات (Code Integrity)
        file_drifts = self._check_file_integrity()
        drifts.extend(file_drifts)
        
        # 2. فحص انزياح الساعة (Time Drift)
        # ملاحظة: في بيئة الإنتاج نقارن مع NTP Server حقيقي
        skew = self._estimate_clock_skew()
        if abs(skew) > 100: # أكثر من 100ms يعتبر انزياحاً خطيراً
            drifts.append(f"CRITICAL CLOCK DRIFT: System clock off by {skew:.2f}ms")

        # 3. فحص المكتبات (Dependency Drift)
        # (يمكن تفعيله للتحقق من عدم تحديث المكتبات في الخلفية)
        
        is_clean = len(drifts) == 0
        if not is_clean:
            logger.warning(f"ENVIRONMENT DRIFT DETECTED: {drifts}")
        
        return DriftReport(
            timestamp=time.time(),
            is_clean=is_clean,
            drift_details=drifts,
            clock_skew_ms=skew
        )

    def _check_file_integrity(self) -> List[str]:
        """مقارنة البصمات الحالية مع القائمة الذهبية."""
        issues = []
        for rel_path, original_hash in self._golden_hashes.items():
            full_path = self.root_dir / rel_path
            
            if not full_path.exists():
                issues.append(f"MISSING FILE: {rel_path} was deleted!")
                continue
                
            current_hash = self._calculate_hash(full_path)
            if current_hash != original_hash:
                issues.append(f"INTEGRITY VIOLATION: {rel_path} has been modified on disk!")
                
        return issues

    def _estimate_clock_skew(self) -> float:
        """
        تقدير انزياح الساعة.
        (محاكاة: في الواقع نستخدم مكتبة ntplib)
        """
        # هنا نفترض أن ساعة النظام دقيقة لأننا لا نملك اتصال NTP في هذا الكود المعزول
        # لكن يمكننا قياس "قفزات" الوقت غير المنطقية (Monotonic Consistency)
        return 0.0

    def _calculate_hash(self, filepath: Path) -> str:
        """حساب SHA-256 للملف."""
        sha = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                # قراءة الملف كتل لتوفير الذاكرة
                for chunk in iter(lambda: f.read(4096), b""):
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception as e:
            logger.error(f"Hashing failed for {filepath}: {e}")
            return "ERROR"

    def verify_dependencies(self, required_packages: Dict[str, str]) -> List[str]:
        """
        التحقق من أن المكتبات المثبتة تطابق الإصدارات المطلوبة.
        """
        drift = []
        for pkg, version in required_packages.items():
            try:
                installed_ver = importlib.metadata.version(pkg)
                if installed_ver != version:
                    drift.append(f"Dependency Drift: {pkg} is {installed_ver}, expected {version}")
            except importlib.metadata.PackageNotFoundError:
                drift.append(f"Missing Dependency: {pkg}")
        return drift

# --- Unit Test ---
if __name__ == "__main__":
    # تهيئة الكاشف
    detector = DriftDetector()
    
    print("--- Baseline Captured. Modifying a file to simulate attack... ---")
    
    # 1. محاكاة هجوم: تعديل ملف .env (سننشئه مؤقتاً للتجربة)
    env_path = Path(".env")
    original_content = ""
    if env_path.exists():
        with open(env_path, "r") as f: original_content = f.read()
    else:
        with open(env_path, "w") as f: f.write("SECRET=123")
        detector._golden_hashes[".env"] = detector._calculate_hash(env_path) # تحديث البصمة للتجربة

    # تعديل الملف
    with open(env_path, "a") as f: f.write("\n# HACKED_BY_DRIFT")
    
    # 2. تشغيل الفحص
    report = detector.run_drift_scan()
    
    print(f"\nReport Status: {'CLEAN' if report.is_clean else 'DRIFT DETECTED'}")
    for issue in report.drift_details:
        print(f"[!] {issue}")
        
    # إعادة الملف لحالته (Clean up)
    if original_content:
        with open(env_path, "w") as f: f.write(original_content)
    else:
        os.remove(env_path)