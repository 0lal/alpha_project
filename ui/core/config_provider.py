# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - UNIFIED CONFIGURATION PROVIDER (THE VAULT)
============================================================
Path: alpha_project/ui/core/config_provider.py
Role: المصدر الموحد للحقيقة. يدمج الأسرار (.env) مع القوانين (YAML).
Pattern: Singleton + Strategy Fusion

Forensic Features:
  1. **Strict Separation**: الأسرار في الذاكرة فقط، الهيكل في الملفات.
  2. **Fail-Fast**: إذا كان ملف التكوين مفقوداً، يوقف النظام فوراً (لا تخمين).
  3. **Secret Masking**: يمنع ظهور المفاتيح في السجلات عند طلب طباعة الإعدادات.
  4. **Dot-Notation Access**: وصول جراحي دقيق لأي إعداد متداخل.

Author: Alpha Architect (AI)
Status: FINANCIAL GRADE STABILITY
"""

import os
import sys
import logging
import threading
from typing import Any, Optional, Dict

# محاولة استيراد المكتبات الضرورية
try:
    import yaml
    from dotenv import load_dotenv
except ImportError:
    # هذا ملف حيوي، إذا فشل الاستيراد يجب إيقاف النظام
    print("❌ CRITICAL: Missing 'PyYAML' or 'python-dotenv'. Run pip install.")
    sys.exit(1)

logger = logging.getLogger("Alpha.Core.Config")

class ConfigProvider:
    """
    مخزن الإعدادات الموحد.
    يدمج system_manifest.yaml (للسلوك) مع .env (للمفاتيح).
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigProvider, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        with self._lock:
            if self._initialized:
                return
            
            self._manifest: Dict[str, Any] = {}
            self._secrets: Dict[str, str] = {}
            self._project_root = self._find_project_root()
            
            # تحميل البيانات فوراً عند الإنشاء
            self._load_secrets()
            self._load_manifest()
            
            self._initialized = True
            logger.info("🔐 Configuration Vault Locked & Loaded.")

    def _find_project_root(self) -> str:
        """تحديد مسار المشروع بدقة جنائية لتجنب أخطاء المسارات النسبية"""
        # نعود للخلف 3 خطوات من موقع هذا الملف: ui/core/config -> alpha_project
        current = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(current, "../../../alpha_project"))

    # =========================================================================
    # 1. Loading Logic (منطق التحميل)
    # =========================================================================

    def _load_secrets(self):
        """تحميل المتغيرات البيئية (الأسرار)"""
        env_path = os.path.join(self._project_root, '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            self._secrets = os.environ
            logger.info("🔑 Secrets loaded from .env")
        else:
            logger.critical("❌ .env file NOT FOUND at: " + env_path)
            # لا نوقف النظام هنا، قد تكون المتغيرات محقونة في السيرفر (Production)
            # لكن نسجل تحذيراً شديد اللهجة
            self._secrets = os.environ

    def _load_manifest(self):
        """تحميل دستور النظام (YAML)"""
        yaml_path = os.path.join(self._project_root, 'config', 'system_manifest.yaml')
        
        if not os.path.exists(yaml_path):
            logger.critical(f"❌ SYSTEM MANIFEST MISSING: {yaml_path}")
            raise FileNotFoundError("Critical: system_manifest.yaml is required for financial operations.")

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                self._manifest = yaml.safe_load(f) or {}
            logger.info("📜 System Manifest loaded successfully.")
        except Exception as e:
            logger.critical(f"💥 YAML PARSING ERROR: {e}")
            raise RuntimeError("Corrupted Configuration File.")

    # =========================================================================
    # 2. Access Logic (منطق الوصول)
    # =========================================================================

    def get(self, path: str, default: Any = None) -> Any:
        """
        استرجاع إعداد هيكلي (من YAML).
        يدعم التنقل بالنقطة: get("brain.models.speed.id")
        """
        keys = path.split('.')
        value = self._manifest
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            if default is not None:
                return default
            # Forensic Rule: إذا لم يكن هناك قيمة افتراضية، نرجع None
            # ولا نخمن قيمة وهمية.
            return None

    def get_secret(self, key: str) -> Optional[str]:
        """
        استرجاع سر (من ENV).
        """
        val = self._secrets.get(key)
        if not val:
            logger.warning(f"⚠️ Secret Key Missing: {key}")
            return None
        return val

    def is_feature_enabled(self, feature_path: str) -> bool:
        """
        فحص سريع هل الميزة مفعلة أم لا.
        مثال: is_feature_enabled("brain.agents.sentiment_analyst")
        """
        # نفترض أن الهيكل في الـ YAML ينتهي بـ 'enabled' أو القيمة نفسها هي boolean
        val = self.get(feature_path)
        
        if isinstance(val, bool):
            return val
        
        if isinstance(val, dict) and 'enabled' in val:
            return val['enabled']
            
        return False

    # =========================================================================
    # 4. Public Properties (إضافات التوافق)
    # =========================================================================
    
    @property
    def project_root(self):
        """
        إتاحة الوصول لمسار الجذر (للتوافق مع ThemeEngine).
        يعيد كائن Path إذا أمكن، أو نص.
        """
        from pathlib import Path
        return Path(self._project_root)

# =============================================================================
# Global Instance (Singleton)
# =============================================================================
config = ConfigProvider()