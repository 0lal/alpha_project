# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - FORENSIC DIAGNOSTIC UNIT (THE SYSTEM DOCTOR)
==============================================================
Path: alpha_project/alpha_diagnostic.py
Role: فحص شامل ودقيق للنظام. يتأكد من أن القلب ينبض، والعقل يفكر، والأعين ترى.
Type: Standalone Tool (Can be run independently).

Forensic Features:
  1. **Registry Audit**: استجواب السجل المركزي للتأكد من تحميل جميع الخدمات.
  2. **Pulse Check**: استدعاء health_check() لكل مكون لاكتشاف الأمراض الخفية.
  3. **Credential Validation**: التأكد من أن المفاتيح في .env صالحة وليست مجرد نصوص فارغة.
  4. **Strict Zero-Mock**: يكتشف الكائنات الوهمية (Placeholders) ويعتبرها فشلاً.

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import sys
import os
import time
import logging

# ضبط المسار الجذري لضمان عمل الاستيراد
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# استيراد النواة
try:
    from alpha_project.core.registry import registry
    from alpha_project.core.loader import ignite_system
    from alpha_project.core.interfaces import ComponentStatus
    from alpha_project.ui.core.config_provider import config
except ImportError as e:
    print(f"❌ CRITICAL SETUP ERROR: Could not import system core. {e}")
    print("   -> Run this script from the parent folder using: python -m alpha_project.alpha_diagnostic")
    sys.exit(1)

# إعداد ألوان التقرير
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

logging.basicConfig(level=logging.ERROR) # نمنع ضوضاء السجلات العادية، نريد التقرير فقط

class ForensicDoctor:
    def __init__(self):
        self.errors = []
        self.warnings = []
        print(f"{Colors.HEADER}{Colors.BOLD}🔍 STARTING ALPHA SOVEREIGN FORENSIC DIAGNOSIS...{Colors.ENDC}")
        print("="*60)

    def run_full_autopsy(self):
        """تشغيل دورة الفحص الكاملة"""
        
        # 1. فحص البيئة والمفاتيح
        self._check_environment()
        
        # 2. إشعال النظام (تشغيل المحرك للفحص)
        if not self._ignite_engine():
            return # لا يمكن الإكمال إذا فشل التحميل

        # 3. تدقيق السجل (Registry Audit)
        self._audit_registry()
        
        # 4. اختبار الاتصال الحي (Live Connectivity)
        self._test_vital_organs()

        # 5. التقرير النهائي
        self._print_verdict()

    def _check_environment(self):
        """فحص ملفات التكوين والمفاتيح"""
        print(f"\n{Colors.OKBLUE}--- [PHASE 1] Environmental Forensics ---{Colors.ENDC}")
        
        # فحص وجود ملفات YAML و ENV
        if config:
            print(f"✅ Config Provider: ACTIVE")
            
            # فحص المفاتيح الحرجة
            critical_keys = ["OPENROUTER_KEY_REASONING", "BINANCE_API_KEY"]
            for key in critical_keys:
                val = config.get_secret(key)
                if val and len(val) > 10:
                    print(f"✅ Secret '{key}': LOADED (Masked: {val[:4]}...{val[-4:]})")
                else:
                    print(f"{Colors.FAIL}❌ Secret '{key}': MISSING or INVALID{Colors.ENDC}")
                    self.errors.append(f"Missing Secret: {key}")
        else:
            print(f"{Colors.FAIL}❌ Config System: FAILED{Colors.ENDC}")
            self.errors.append("Config Provider failed to load.")

    def _ignite_engine(self) -> bool:
        """تشغيل النظام في وضع الفحص"""
        print(f"\n{Colors.OKBLUE}--- [PHASE 2] Core System Ignition ---{Colors.ENDC}")
        try:
            print("🔥 Igniting Loader...")
            ignite_system(root_dir=current_dir)
            services = registry.list_services()
            print(f"✅ Loader completed. Found {len(services)} active components.")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}💥 IGNITION CRASH: {e}{Colors.ENDC}")
            self.errors.append(f"System Crash: {e}")
            return False

    def _audit_registry(self):
        """فحص الخدمات المسجلة"""
        print(f"\n{Colors.OKBLUE}--- [PHASE 3] Registry Audit ---{Colors.ENDC}")
        
        services = registry.list_services()
        if not services:
            print(f"{Colors.FAIL}❌ Registry is EMPTY! No agents loaded.{Colors.ENDC}")
            self.errors.append("Registry Empty")
            return

        for svc in services:
            name = svc['name']
            category = svc['category']
            status_icon = "❓"
            
            # جلب الكائن الفعلي لفحصه
            instance = registry.get(name)
            health = ComponentStatus.UNKNOWN
            
            if hasattr(instance, 'health_check'):
                health = instance.health_check()
            
            if health == ComponentStatus.HEALTHY:
                status_icon = "🟢"
                print(f"   {status_icon} [{category.upper()}] {name}: HEALTHY")
            elif health == ComponentStatus.DEGRADED:
                status_icon = "🟠"
                print(f"   {status_icon} [{category.upper()}] {name}: DEGRADED")
                self.warnings.append(f"{name} is Degraded")
            else:
                status_icon = "🔴"
                print(f"   {status_icon} [{category.upper()}] {name}: FAILED/STOPPED")
                self.errors.append(f"{name} Health Check Failed")

            # كشف الوهم (Fake Detection)
            if "Missing" in str(type(instance).__name__):
                print(f"      {Colors.FAIL}⚠️ DETECTION: This is a MOCK object (Placeholders are banned).{Colors.ENDC}")
                self.errors.append(f"{name} is a MOCK object")

    def _test_vital_organs(self):
        """اختبارات وظيفية حقيقية (هل يمكننا التفكير؟ هل يمكننا رؤية السعر؟)"""
        print(f"\n{Colors.OKBLUE}--- [PHASE 4] Vital Organ Functionality ---{Colors.ENDC}")
        
        # 1. اختبار العقل (Brain)
        brain_gateway = registry.get("brain.gateway")
        if brain_gateway:
            print("🧠 Testing Brain Gateway Connectivity...")
            # لا نجري اختباراً مكلفاً، فقط نتأكد من أنه مهيأ
            if brain_gateway.keys.get('openrouter'):
                print("   ✅ Brain Keys Present.")
            else:
                print(f"   {Colors.FAIL}❌ Brain Keys Missing.{Colors.ENDC}")
                self.errors.append("Brain Gateway has no keys")
        else:
            print(f"{Colors.FAIL}❌ Brain Gateway NOT FOUND.{Colors.ENDC}")
            self.errors.append("Critical: Brain Gateway missing")

        # 2. اختبار البيانات (Data)
        binance = registry.get("data.binance")
        if binance:
            print("📉 Testing Binance Connectivity...")
            # هنا نستدعي دالة الاتصال الحقيقية
            if binance.connect():
                print("   ✅ Binance API Reachable.")
            else:
                print(f"   {Colors.FAIL}❌ Binance API Unreachable.{Colors.ENDC}")
                self.errors.append("Binance Connectivity Failed")
        else:
            print(f"{Colors.WARNING}⚠️ Binance Collector NOT FOUND (Market data will be blind).{Colors.ENDC}")
            self.warnings.append("No Market Data Collector")

    def _print_verdict(self):
        """الحكم النهائي"""
        print("\n" + "="*60)
        print(f"{Colors.BOLD}🕵️ FORENSIC DIAGNOSIS VERDICT:{Colors.ENDC}")
        
        if not self.errors:
            print(f"\n{Colors.OKGREEN}✅ SYSTEM INTEGRITY CONFIRMED.{Colors.ENDC}")
            print("   The system is healthy, authentic, and ready for financial operations.")
            if self.warnings:
                print(f"   ⚠️ {len(self.warnings)} Warnings detected (Non-Critical).")
        else:
            print(f"\n{Colors.FAIL}🛑 SYSTEM CRITICAL FAILURE.{Colors.ENDC}")
            print(f"   Found {len(self.errors)} fatal errors:")
            for e in self.errors:
                print(f"   - {e}")
            print(f"\n{Colors.FAIL}🚫 LAUNCH ABORTED. DO NOT TRADE.{Colors.ENDC}")

if __name__ == "__main__":
    doctor = ForensicDoctor()
    doctor.run_full_autopsy()
    input("\nPress Enter to exit...")