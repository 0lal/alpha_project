# =================================================================
# ALPHA SOVEREIGN ORGANISM - FORENSIC LOG VIEWER
# =================================================================
# File: tools/debugger/log_viewer.py
# Status: PRODUCTION (Forensic Tool)
# Pillar: Observability (الركيزة: المراقبة)
# Forensic Purpose: تحويل السجلات الخام (JSON) إلى عرض ملون قابل للتحليل البشري السريع.
# =================================================================

import json
import sys
import argparse
from datetime import datetime

# أكواد الألوان للطرفية (Terminal Colors)
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"      # للأخطاء
    GREEN = "\033[92m"    # للنجاح
    YELLOW = "\033[93m"   # للتحذير
    BLUE = "\033[94m"     # للمعلومات
    CYAN = "\033[96m"     # للتفاصيل التقنية
    GREY = "\033[90m"     # للطابع الزمني

def parse_log_line(line):
    """محاولة قراءة السطر كـ JSON، وإذا فشل نعرضه كما هو."""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"raw": line.strip(), "level": "UNKNOWN"}

def format_timestamp(ts_str):
    """تنسيق الوقت ليكون مقروءاً."""
    # نفترض أن الوقت يأتي بصيغة ISO 8601
    return ts_str.replace("T", " ").split(".")[0]

def print_log_entry(entry):
    """طباعة السجل بتنسيق جنائي."""
    level = entry.get("level", "INFO").upper()
    msg = entry.get("message", "")
    ts = entry.get("timestamp", datetime.now().isoformat())
    component = entry.get("target", "System")
    
    # تحديد اللون بناءً على الخطورة
    color = Colors.BLUE
    if level in ["ERROR", "CRITICAL", "FATAL"]:
        color = Colors.RED
    elif level == "WARN" or level == "WARNING":
        color = Colors.YELLOW
    elif level == "DEBUG":
        color = Colors.GREY

    # طباعة السطر المنسق
    # [TIME] [LEVEL] [COMPONENT] Message {Context}
    print(f"{Colors.GREY}[{format_timestamp(ts)}]{Colors.RESET} "
          f"{color}[{level:5}]{Colors.RESET} "
          f"{Colors.CYAN}[{component}]{Colors.RESET} "
          f"{msg}", end="")

    # طباعة السياق الإضافي (Context) إذا وجد
    context = {k: v for k, v in entry.items() if k not in ["level", "message", "timestamp", "target"]}
    if context:
        print(f" {Colors.GREY}{json.dumps(context)}{Colors.RESET}")
    else:
        print()

def main():
    parser = argparse.ArgumentParser(description="Alpha Forensic Log Viewer")
    parser.add_argument("logfile", help="Path to the .json log file")
    parser.add_argument("--level", help="Filter by level (INFO, WARN, ERROR)", default=None)
    args = parser.parse_args()

    print(f"{Colors.GREEN}[*] Analyzing Forensic Log: {args.logfile}{Colors.RESET}")
    print("-" * 80)

    try:
        with open(args.logfile, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                entry = parse_log_line(line)
                
                # تطبيق الفلتر
                if args.level and entry.get("level") != args.level:
                    continue
                    
                print_log_entry(entry)
    except FileNotFoundError:
        print(f"{Colors.RED}[!] Error: File not found.{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}[!] Critical Error: {e}{Colors.RESET}")

if __name__ == "__main__":
    main()