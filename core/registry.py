# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - SYSTEM REGISTRY CORE (THE NEXUS)
==================================================
Path: alpha_project/core/registry.py
Role: "السجل المدني المركزي" - إدارة دورة حياة الكائنات والخدمات.
Type: Singleton / Thread-Safe Container

Forensic Features:
  1. **Audit Trail**: تسجيل دقيق لوقت ومصدر كل خدمة يتم تسجيلها.
  2. **Thread Safety**: استخدام أقفال (RLock) لمنع تضارب البيانات أثناء الإقلاع المتوازي.
  3. **Dependency Injection**: يتيح للواجهة طلب الخدمات بالاسم (String) بدلاً من الاستيراد المباشر.
  4. **Hot-Swapping**: قابلية استبدال أجزاء من النظام أثناء التشغيل (Runtime Replacement).

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

# إعداد السجلات الخاصة بالنواة
logger = logging.getLogger("Alpha.Core.Registry")

@dataclass
class ServiceEntry:
    """
    وثيقة هوية الخدمة (Service Identity Card).
    تحتفظ ليس فقط بالكائن، بل ببياناته الجنائية.
    """
    instance: Any                  # الكائن الفعلي (الذكاء، قاعدة البيانات، الخ)
    name: str                      # الاسم الفريد (مثال: 'brain.main')
    category: str                  # التصنيف (brain, data, ui)
    registered_at: float = field(default_factory=time.time) # طابع زمني للتسجيل
    is_critical: bool = False      # هل توقف هذه الخدمة يوقف النظام؟

class SovereignRegistry:
    """
    السجل السيادي (The Central Nervous System).
    نمط تصميم Singleton لضمان وجود نسخة واحدة فقط للحقيقة.
    """
    _instance = None
    _lock = threading.RLock() # قفل لتأمين العمليات متعددة الخيوط

    def __new__(cls):
        """ضمان وجود نسخة واحدة فقط من السجل في الذاكرة"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SovereignRegistry, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """تهيئة السجل (تعمل مرة واحدة فقط)"""
        with self._lock:
            if self._initialized:
                return
            
            # مخزن الخدمات: { 'service_name': ServiceEntry }
            self._services: Dict[str, ServiceEntry] = {}
            
            # قائمة المراقبين (لإشعار النظام عند تسجيل خدمة جديدة)
            self._hooks: List[Callable] = []
            
            self._initialized = True
            logger.info("🟢 Sovereign Registry Initialized (Memory Nexus Ready).")

    # =========================================================================
    # 1. Registration Logic (بوابة الدخول)
    # =========================================================================
    def register(self, name: str, instance: Any, category: str = "general", is_critical: bool = False, force: bool = False):
        """
        تسجيل خدمة جديدة في النظام.
        
        Args:
            name: اسم الخدمة (يجب أن يكون فريداً، مثل 'brain.gateway').
            instance: الكائن الفعلي (Object/Class Instance).
            category: تصنيف الخدمة للتنظيم.
            is_critical: هل هذه خدمة حيوية؟
            force: هل نستبدل الخدمة إذا كانت موجودة مسبقاً؟ (للإصلاح الذاتي).
        """
        with self._lock:
            # التحقق من وجود الاسم مسبقاً (حماية من التصادم)
            if name in self._services and not force:
                logger.warning(f"⚠️ Service '{name}' already registered. Use force=True to overwrite.")
                return

            # إنشاء السجل الجنائي للخدمة
            entry = ServiceEntry(
                instance=instance,
                name=name,
                category=category,
                is_critical=is_critical
            )
            
            self._services[name] = entry
            
            # تسجيل الحدث (للمحلل الجنائي)
            action = "Overwritten" if force and name in self._services else "Registered"
            logger.debug(f"✅ Service {action}: [{category.upper()}] {name}")

            # إشعار المراقبين (مثلاً: تحديث الواجهة فوراً)
            self._notify_hooks(name, instance)

    # =========================================================================
    # 2. Retrieval Logic (بوابة الاستعلام)
    # =========================================================================
    def get(self, name: str) -> Optional[Any]:
        """
        استدعاء خدمة بالاسم.
        هذه هي الطريقة الوحيدة التي يجب أن تتحدث بها الملفات مع بعضها.
        """
        with self._lock:
            entry = self._services.get(name)
            if entry:
                return entry.instance
            
            # تسجيل فشل الوصول (يساعد في تشخيص المشاكل)
            logger.debug(f"🔍 Lookup Failed: Service '{name}' not found.")
            return None

    def get_by_category(self, category: str) -> Dict[str, Any]:
        """جلب جميع الخدمات تحت تصنيف معين (مثلاً: كل استراتيجيات التداول)"""
        with self._lock:
            return {
                name: entry.instance 
                for name, entry in self._services.items() 
                if entry.category == category
            }

    # =========================================================================
    # 3. Diagnostic & Maintenance (أدوات الفحص)
    # =========================================================================
    def list_services(self) -> List[dict]:
        """تقرير كامل عن حالة النظام (للمحلل الجنائي)"""
        with self._lock:
            report = []
            for name, entry in self._services.items():
                age = time.time() - entry.registered_at
                report.append({
                    "name": name,
                    "category": entry.category,
                    "critical": entry.is_critical,
                    "age_seconds": round(age, 2),
                    "type": str(type(entry.instance).__name__)
                })
            return report

    def unregister(self, name: str):
        """إزالة خدمة (تنظيف الذاكرة أو إيقاف ميزة)"""
        with self._lock:
            if name in self._services:
                del self._services[name]
                logger.info(f"🗑️ Service Unregistered: {name}")

    # =========================================================================
    # 4. Hooks System (نظام رد الفعل)
    # =========================================================================
    def add_hook(self, callback: Callable[[str, Any], None]):
        """إضافة دالة يتم تنفيذها عند تسجيل أي خدمة جديدة"""
        self._hooks.append(callback)

    def _notify_hooks(self, name: str, instance: Any):
        for callback in self._hooks:
            try:
                callback(name, instance)
            except Exception as e:
                logger.error(f"⚠️ Hook Error for {name}: {e}")

# =============================================================================
# Helper Decorator (للتسجيل التلقائي السهل)
# =============================================================================
# هذه الأداة ستسهل عليك إضافة الملفات مستقبلاً.
# فقط ضع @register_component فوق أي كلاس وسيعمل تلقائياً.

def register_component(name: str, category: str = "general", is_critical: bool = False):
    def decorator(cls):
        # نقوم بالتسجيل عند تعريف الكلاس (أو يمكن تأجيلها عند التشغيل)
        # هنا سنقوم بحقن وظيفة التسجيل الذاتي
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # التسجيل التلقائي عند تشغيل الكلاس
            registry = SovereignRegistry()
            registry.register(name, self, category, is_critical)
        
        cls.__init__ = new_init
        return cls
    return decorator

# إنشاء النسخة العالمية (Global Instance)
registry = SovereignRegistry()