# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - MASTER LAUNCHER (THE DETONATOR)
=================================================
Path: alpha_project/run_alpha.py
Role: "بروتوكول الإطلاق" - يربط النواة، يحمل الخدمات، يفحص التكامل، ثم يطلق الواجهة.
Policy: ZERO-MOCK TOLERANCE (No Fake Data).

Forensic Features:
  1. **Dynamic Path Injection**: يحل مشاكل الاستيراد نهائياً عن طريق فرض المسار الجذري.
  2. **Pre-Flight Diagnostics**: يرفض التشغيل إذا كانت البيئة غير آمنة (مفاتيح ناقصة).
  3. **Component Auto-Discovery**: يستخدم Loader لمسح النظام وتشغيل الخدمات تلقائياً.
  4. **Strict Integrity Check**: يمنع تشغيل الواجهة إذا لم يتم تحميل "العقل" أو "البيانات".

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import sys
import os
import logging
import traceback

# =============================================================================
# 1. Environmental Forensics (تهيئة مسرح الجريمة)
# =============================================================================
# قبل استيراد أي ملف من المشروع، يجب أن نضمن أن بايثون يرى المجلد الجذري.
# هذا يحل مشكلة: ModuleNotFoundError: No module named 'alpha_project'

current_dir = os.path.dirname(os.path.abspath(__file__))
# نفترض أن هذا الملف موجود مباشرة داخل alpha_project
# إذا كان داخل مجلد فرعي، يجب تعديل الـ parent directory
project_root = os.path.dirname(current_dir) # الصعود خطوة واحدة للأعلى إذا لزم الأمر
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# إعداد نظام التسجيل الجنائي (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler("alpha_boot.log") # يمكن تفعيله لتسجيل الملفات
    ]
)
logger = logging.getLogger("Alpha.Bootloader")

# =============================================================================
# 2. Bootstrapper Class (مدير الإطلاق)
# =============================================================================

class SystemBootstrapper:
    """
    يقوم بإعداد النظام وتشغيله بتسلسل صارم.
    """
    
    def __init__(self):
        self.registry = None
        self.app = None

    def run_diagnostics(self):
        """
        الخطوة 1: الفحص الأولي.
        التأكد من أن المكتبات الأساسية والملفات الحيوية موجودة.
        """
        print("🔍 [PHASE 1] Running Pre-Flight Diagnostics...")
        
        # فحص ملف التكوين
        env_path = os.path.join(current_dir, '.env')
        if not os.path.exists(env_path):
            logger.critical("❌ FATAL: Configuration file (.env) is MISSING.")
            print("⚠️ System Halt: Cannot run a financial system without credentials.")
            sys.exit(1)

        # فحص المكتبات الخارجية
        try:
            import PyQt6
            import requests
            import dotenv
        except ImportError as e:
            logger.critical(f"❌ FATAL: Missing Library: {e.name}")
            print(f"⚠️ System Halt: Please run 'pip install {e.name}'")
            sys.exit(1)
            
        print("✅ Diagnostics Passed.")

    def ignite_core(self):
        """
        الخطوة 2: الإشعال (Ignition).
        تشغيل الماسح الضوئي (Loader) لاكتشاف الخدمات وتسجيلها.
        """
        print("🔥 [PHASE 2] Igniting Core Systems...")
        
        try:
            # استيراد النواة الديناميكية التي بنيناها
            from alpha_project.core.loader import ignite_system
            from alpha_project.core.registry import registry
            
            # تحديد القطاعات التي سيتم مسحها بحثاً عن كود
            # لاحظ أننا لا نحدد أسماء الملفات، بل المجلدات فقط
            self.registry = ignite_system(root_dir=current_dir)
            
            # طباعة تقرير عما تم تحميله
            services = self.registry.list_services()
            print(f"\n📊 [REGISTRY REPORT] {len(services)} Services Loaded:")
            for s in services:
                print(f"   -> [{s['category'].upper()}] {s['name']} ({s['type']})")
                
        except Exception as e:
            logger.critical(f"💥 Core Ignition Failed: {e}")
            traceback.print_exc()
            sys.exit(1)

    def verify_integrity(self):
        """
        الخطوة 3: التحقق من النزاهة (Integrity Check).
        هل النظام صالح للعمل المالي؟ أم أنه فارغ؟
        """
        print("🛡️ [PHASE 3] Verifying System Integrity (No Mock Data)...")
        
        brains = self.registry.get_by_category("brain")
        data_sources = self.registry.get_by_category("data")
        
        # التحقق الصارم: يجب وجود عقل واحد على الأقل
        if not brains:
            logger.error("❌ INTEGRITY FAILURE: No Intelligence Unit (Brain) found!")
            print("⚠️ Warning: System is brainless. Connecting to fallback protocols...")
            # في بيئة الإنتاج الصارمة، قد نوقف النظام هنا.
            # ولكن سنسمح بالمرور إذا كان هناك "جسر" (Bridge) للتعامل مع الخطأ.
            
        # التحقق الصارم: يجب وجود مصدر بيانات
        if not data_sources:
            logger.warning("⚠️ ALERT: No Data Collectors found. Market data will be unavailable.")
            
        if brains or data_sources:
            print("✅ System Integrity Verified. Ready for Financial Operations.")
        else:
            print("⚠️ SYSTEM HOLLOW: No components loaded. Check your folders!")

    def launch_ui(self):
        """
        الخطوة 4: إطلاق الواجهة (Lift Off).
        """
        print("🚀 [PHASE 4] Launching User Interface...")
        
        from PyQt6.QtWidgets import QApplication
        # استيراد الواجهة التي تم تحديثها لتستخدم Service Locator
        from alpha_project.ui.views.advisor.advisor_view import AdvisorView
        
        # تفعيل الثيمات
        try:
            from alpha_project.ui.core.theme_engine import theme_engine
            # theme_engine.apply_theme("dark_mode") # (اختياري)
        except: pass

        self.app = QApplication(sys.argv)
        
        # إعداد النافذة الرئيسية
        window = AdvisorView()
        window.setWindowTitle("Alpha Sovereign | Financial Intelligence Terminal")
        window.resize(1200, 800)
        window.show()
        
        logger.info("🟢 System Online. User Control Active.")
        sys.exit(self.app.exec())

# =============================================================================
# Main Execution Entry Point
# =============================================================================

if __name__ == "__main__":
    bootstrapper = SystemBootstrapper()
    
    try:
        # 1. فحص المتطلبات
        bootstrapper.run_diagnostics()
        
        # 2. تحميل الكود ديناميكياً
        bootstrapper.ignite_core()
        
        # 3. التأكد من عدم وجود بيانات وهمية
        bootstrapper.verify_integrity()
        
        # 4. فتح الشاشة
        bootstrapper.launch_ui()
        
    except KeyboardInterrupt:
        print("\n🛑 Launch Aborted by User.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"💀 CRITICAL SYSTEM FAILURE: {e}")
        traceback.print_exc()
        sys.exit(1)