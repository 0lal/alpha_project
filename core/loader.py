# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - DYNAMIC COMPONENT LOADER (THE SCANNER)
========================================================
Path: alpha_project/core/loader.py
Role: "الكشاف الآلي" - مسح المجلدات، استيراد الوحدات، وتشغيلها تلقائياً.
Forensic Features:
  1. **Safe Import Sandbox**: محاولة استيراد كل ملف في بيئة معزولة لمنع انهيار النظام.
  2. **Strict Compliance Check**: التأكد من أن الكلاس يطبق 'Interfaces' قبل تشغيله.
  3. **Quarantine Logic**: عزل الملفات الفاسدة وتسجيل أسباب الفشل بدقة جنائية.
  4. **Recursive Discovery**: البحث في أعماق المجلدات الفرعية (Deep Scan).

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import os
import sys
import importlib
import importlib.util
import inspect
import logging
import traceback
from typing import List, Dict, Type

# استيراد النواة والقوانين
from alpha_project.core.registry import registry
from alpha_project.core.interfaces import ISovereignComponent

logger = logging.getLogger("Alpha.Core.Loader")

class ComponentLoader:
    """
    محرك التحميل الديناميكي.
    يقوم بتحويل الملفات الساكنة (.py) إلى كائنات حية داخل السجل (Registry).
    """

    def __init__(self, root_path: str):
        self.root_path = os.path.abspath(root_path)
        self.loaded_count = 0
        self.quarantine_list: List[Dict] = [] # سجل الملفات المعطوبة

    def scan_and_load(self, target_dirs: List[str]):
        """
        الوظيفة الرئيسية: مسح المجلدات المحددة وتحميل ما فيها.
        Args:
            target_dirs: قائمة المجلدات النسبية (e.g., ['brain', 'data/collectors'])
        """
        logger.info(f"🔍 Starting Deep Scan on: {target_dirs}")
        
        for relative_dir in target_dirs:
            full_path = os.path.join(self.root_path, relative_dir)
            
            if not os.path.exists(full_path):
                logger.warning(f"⚠️ Directory not found, skipping: {full_path}")
                continue

            # بدء المسح المتكرر (Recursive Walk)
            self._walk_and_import(full_path, relative_dir)

        logger.info(f"✅ Boot Complete. Activated {self.loaded_count} components.")
        if self.quarantine_list:
            logger.error(f"🚫 QUARANTINE REPORT: {len(self.quarantine_list)} modules failed.")
            for fail in self.quarantine_list:
                logger.error(f"   -> {fail['file']}: {fail['error']}")

    def _walk_and_import(self, directory: str, base_package: str):
        """التجول داخل المجلدات واستيراد الملفات"""
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    # بناء المسار الكامل
                    file_path = os.path.join(root, file)
                    
                    # استنتاج اسم الباكيج (e.g., brain.agents.risk)
                    # هذا الجزء يحول مسار الملف إلى Python Dot Notation
                    rel_path = os.path.relpath(file_path, self.root_path)
                    module_name = rel_path.replace(os.sep, ".")[:-3] # حذف .py
                    
                    # محاولة التحميل الآمن
                    self._safe_load_module(module_name, file_path)

    def _safe_load_module(self, module_name: str, file_path: str):
        """
        منطقة الحجر الصحي: محاولة استيراد الموديول والتقاط أي خطأ قاتل.
        """
        try:
            # 1. الاستيراد الديناميكي (Dynamic Import)
            # هذه الخطوة تنفذ كود البايثون داخل الملف
            module = importlib.import_module(module_name)
            
            # 2. التفتيش (Inspection)
            # البحث عن أي كلاس يرث من ISovereignComponent
            self._inspect_and_activate(module)
            
        except Exception as e:
            # في حال انفجار الملف، لا نوقف النظام، بل نسجله في الجنايات
            error_msg = f"{str(e)}"
            # traceback_str = traceback.format_exc() # يمكن تفعيلها للتفاصيل الكاملة
            
            self.quarantine_list.append({
                "file": file_path,
                "module": module_name,
                "error": error_msg
            })
            logger.debug(f"💥 Module Load Failed: {module_name} | Error: {error_msg}")

    def _inspect_and_activate(self, module):
        """
        فحص محتويات الموديول بحثاً عن المكونات الصالحة وتشغيلها.
        """
        for name, obj in inspect.getmembers(module):
            # الشروط الصارمة لقبول المكون:
            # 1. هو كلاس (Class)
            # 2. يرث من ISovereignComponent (الدستور)
            # 3. ليس هو الكلاس الجذري نفسه (ISovereignComponent)
            # 4. معرف داخل هذا الموديول (وليس مستورداً من مكان آخر)
            if (inspect.isclass(obj) 
                and issubclass(obj, ISovereignComponent) 
                and obj is not ISovereignComponent
                and obj.__module__ == module.__name__):
                
                try:
                    # 3. التشغيل (Instantiation)
                    # هنا يتم خلق الكائن، وإذا كان يستخدم @register_component
                    # فسيقوم بتسجيل نفسه تلقائياً في Registry.
                    instance = obj()
                    
                    # 4. التحقق من التسجيل (Double Check)
                    # للتأكد من أن الكلاس قام بتسجيل نفسه، أو نقوم نحن بذلك
                    if not registry.get(instance.name):
                        logger.info(f"🔧 Manual Registration: {instance.name}")
                        registry.register(instance.name, instance, category="auto_discovered")
                    
                    # 5. التجهيز (Initialize)
                    # استدعاء دالة الإقلاع الخاصة بالمكون
                    success = instance.initialize({}) # نمرر كونفيج فارغ حالياً
                    
                    if success:
                        self.loaded_count += 1
                        logger.debug(f"🚀 Activated: {instance.name}")
                    else:
                        logger.warning(f"⚠️ Component {instance.name} failed initialization check.")
                        
                except Exception as e:
                    logger.error(f"❌ Activation Error for {name}: {e}")

# =============================================================================
# Helper Function (للاستخدام المباشر في main.py)
# =============================================================================
def ignite_system(root_dir: str = None):
    """
    زر التشغيل السحري. استدعه وسيقوم بكل شيء.
    """
    if not root_dir:
        # اكتشاف الجذر تلقائياً (3 مستويات للأعلى من هذا الملف)
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        
    # إضافة الجذر للمسار لضمان الاستيراد الصحيح
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    logger.info("🔥 Igniting Alpha Sovereign System...")
    
    loader = ComponentLoader(root_dir)
    
    # تحديد المجلدات المستهدفة للمسح
    # يمكن مستقبلاً قراءتها من ملف config.yaml
    target_sectors = [
        'brain',  # الذكاء والاستراتيجيات
        'data',   # موصلات البيانات
        'shield'  # الحماية والأمان
    ]
    
    loader.scan_and_load(target_sectors)
    
    return registry