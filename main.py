# -*- coding: utf-8 -*-
"""
Alpha Sovereign System - Master Controller [Version 35.0]
-------------------------------------------------------
الوظيفة: بوابة التحكم السيادية الموحدة (Orchestration & Diagnostics).
المسؤولية: إدارة دورة حياة الكيان، فحص النزاهة، واتخاذ قرار الإقلاع.
"""

import sys
import os
import argparse
import time
from pathlib import Path

# --- إعداد الألوان والسمات البصرية (Visual Identity) ---
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'

# --- إعداد المسارات الجينية (System Paths Injection) ---
BASE_DIR = Path(__file__).resolve().parent
SUB_PATHS = [
    BASE_DIR / "ops" / "scripts",
    BASE_DIR / "tools",
    BASE_DIR / "shield" / "core",
    BASE_DIR / "shared" / "nexus"
]

for path in SUB_PATHS:
    if path.exists():
        sys.path.append(str(path))

# --- مصفوفة الأوامر السيادية ---

def show_banner():
    banner = f"""{BOLD}{OKBLUE}
    █████  ██      ██████  ██   ██  █████  
    ██   ██ ██      ██   ██ ██   ██ ██   ██ 
    ███████ ██      ██████  ███████ ███████ 
    ██   ██ ██      ██      ██   ██ ██   ██ 
    ██   ██ ███████ ██      ██   ██ ██   ██ 
    {ENDC}{BOLD}===================================================
       ALPHA SOVEREIGN ORGANISM - UNIFIED COMMAND
    ==================================================={ENDC}
    """
    print(banner)

def perform_preflight_check():
    """
    إجراء فحص ما قبل الإقلاع (Pre-flight Check)
    يدمج منطق التشخيص العميق قبل السماح للنظام بالعمل.
    """
    print(f"\n{BOLD}[*] البدء في إجراءات الفحص الجنائي للنزاهة...{ENDC}")
    
    try:
        # ملاحظة: تم تغيير المسار من core.system ليطابق الهيكلية الجديدة في tools
        from diagnostic import AlphaDiagnostics
        scanner = AlphaDiagnostics()
        report = scanner.run_full_scan()
    except ImportError:
        print(f"{FAIL}[!] خطأ حرج: مديول التشخيص مفقود أو الهيكلية غير مكتملة.{ENDC}")
        return None

    # عرض التقرير البصري
    print(f"\n{BOLD}--- تقرير الحالة الصحية (Health Audit) ---{ENDC}")
    for component, data in report["components"].items():
        if data["status"] == "HEALTHY":
            icon = f"{OKGREEN}✅{ENDC}"
        elif data["status"] == "WARNING":
            icon = f"{WARNING}⚠️{ENDC}"
        else:
            icon = f"{FAIL}❌{ENDC}"
        print(f"{icon} {component.ljust(20)} : {data['status']} ({data['details']})")

    return report

def run_launcher(report):
    """تشغيل بوابة الإيقاظ بناءً على التقرير الطبي"""
    if not report:
        sys.exit(1)

    status = report["system_status"]
    
    if status == "CRITICAL_FAILURE":
        print(f"\n{FAIL}{BOLD}!!! تم إيقاف الإقلاع: وجود أخطاء حرجة تهدد نزاهة الكيان !!!{ENDC}")
        sys.exit(1)
        
    elif status == "DEGRADED":
        print(f"\n{WARNING}{BOLD}>>> تحذير: النظام يبدأ في وضع التشغيل المقيد (Degraded Mode) <<<{ENDC}")
    else:
        print(f"\n{OKGREEN}{BOLD}>>> النظام جاهز تماماً: جميع الأعضاء في حالة استعداد قصوى <<<{ENDC}")

    print(f"{OKBLUE}[*] جاري استدعاء مديول الإيقاظ الرئيسي (launcher.py)...{ENDC}")
    try:
        import launcher
        launcher.start_system(report)
    except ImportError as e:
        print(f"{FAIL}[!] فشل في العثور على مديول الإقلاع في ops/scripts/. {e}{ENDC}")

def run_genesis():
    """بروتوكول التكوين والبناء"""
    print(f"{OKBLUE}[*] تفعيل بروتوكول التكوين (Genesis)...{ENDC}")
    try:
        import genesis
        genesis.initialize_structure()
    except ImportError:
        print(f"{FAIL}[!] سكريبت Genesis مفقود في tools/setup/.{ENDC}")

# --- المعالج الرئيسي (CLI Entry Point) ---

def main():
    show_banner()
    parser = argparse.ArgumentParser(description="Alpha Sovereign Command Center")
    parser.add_argument("command", choices=["start", "doctor", "genesis", "status"], 
                        help="الأوامر: start (تشغيل مع فحص), doctor (فحص فقط), genesis (بناء البيئة)")

    args = parser.parse_args()

    if args.command == "start":
        report = perform_preflight_check()
        run_launcher(report)
    
    elif args.command == "doctor":
        perform_preflight_check()
        
    elif args.command == "genesis":
        run_genesis()
        
    elif args.command == "status":
        print(f"{OKGREEN}[+] الكيان Alpha في حالة سكون إيجابي. بانتظار أمر الإيقاظ.{ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{FAIL}[!] تم إنهاء جلسة التحكم يدوياً. إغلاق الأنظمة الحيوية...{ENDC}")
        sys.exit(0)