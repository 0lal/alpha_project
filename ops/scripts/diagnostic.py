#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - ADVANCED DIAGNOSTIC SUITE (v2.0)
=================================================================
File: ops/scripts/diagnostic.py
Role: الطبيب الشرعي للنظام (System Forensic Doctor).
Features:
  - Dynamic Path Resolution (يعمل على أي جهاز).
  - Granular API Testing (فحص كل مفتاح ذكاء اصطناعي بشكل منفصل).
  - Infrastructure Scan (Redis, DB, Ports).
  - Environment Audit (التأكد من وجود المفاتيح).
=================================================================
"""

import sys
import os
import asyncio
import platform
import psutil
import socket
import logging
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict

# محاولة استيراد aiohttp للفحص السريع
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# --- 1. تحديد المسارات ديناميكياً (The Fix) ---
CURRENT_FILE = Path(__file__).resolve()
# ops/scripts/diagnostic.py -> ops/scripts -> ops -> alpha_project (ROOT)
ROOT_DIR = CURRENT_FILE.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | DIAGNOSTIC | %(levelname)s | %(message)s'
)
logger = logging.getLogger("AlphaDoctor")

@dataclass
class DiagnosticResult:
    category: str
    target: str
    status: str     # OK, FAIL, WARN, SKIP
    latency: float  # ms
    details: str

class AlphaDiagnostic:
    """
    محرك الفحص الشامل.
    """
    def __init__(self):
        self.results: List[DiagnosticResult] = []
        self.env_vars: Dict[str, str] = {}
        self.system_info = {}

    def load_environment(self):
        """تحميل متغيرات البيئة يدوياً لفحصها"""
        if not ENV_FILE.exists():
            self.results.append(DiagnosticResult("ENV", ".env File", "FAIL", 0, "File missing"))
            return

        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        self.env_vars[k.strip()] = v.strip()
            
            self.results.append(DiagnosticResult("ENV", ".env File", "OK", 0, f"Loaded {len(self.env_vars)} vars"))
        except Exception as e:
            self.results.append(DiagnosticResult("ENV", ".env File", "FAIL", 0, str(e)))

    async def check_neural_apis(self):
        """
        فحص دقيق لكل مزود ذكاء اصطناعي على حدة.
        هذا يحل مشكلة 'أين الخطأ بالتحديد؟'.
        """
        if not HAS_AIOHTTP:
            logger.warning("aiohttp missing. Skipping API latency checks.")
            return

        # تعريف نقاط الفحص
        checks = [
            {
                "name": "Reasoning (Xiaomi)",
                "key_var": "OPENROUTER_KEY_REASONING",
                "url": "https://openrouter.ai/api/v1/auth/key", # نقطة فحص الصلاحية
                "headers": lambda k: {"Authorization": f"Bearer {k}"}
            },
            {
                "name": "Reflex (Gemini)",
                "key_var": "OPENROUTER_KEY_SPEED",
                "url": "https://openrouter.ai/api/v1/auth/key",
                "headers": lambda k: {"Authorization": f"Bearer {k}"}
            },
            {
                "name": "Vision (Qwen)",
                "key_var": "OPENROUTER_KEY_VISION",
                "url": "https://openrouter.ai/api/v1/auth/key",
                "headers": lambda k: {"Authorization": f"Bearer {k}"}
            },
            {
                "name": "Binance API",
                "key_var": None, # عام
                "url": "https://api.binance.com/api/v3/ping",
                "headers": lambda k: {}
            }
        ]

        async with aiohttp.ClientSession() as session:
            for check in checks:
                name = check["name"]
                key = self.env_vars.get(check["key_var"]) if check["key_var"] else "PUBLIC"
                
                # 1. فحص وجود المفتاح
                if check["key_var"] and (not key or "sk-" not in key):
                    self.results.append(DiagnosticResult("API", name, "WARN", 0, "Key Missing in .env"))
                    continue

                # 2. فحص الاتصال الفعلي
                start_t = time.perf_counter()
                try:
                    async with session.get(check["url"], headers=check["headers"](key), timeout=5) as resp:
                        lat = (time.perf_counter() - start_t) * 1000
                        
                        if resp.status == 200:
                            # بالنسبة لـ OpenRouter، فحص محتوى الرد للتأكد من الرصيد
                            data = await resp.json() if "openrouter" in check["url"] else {}
                            details = "Active"
                            if "data" in data: # OpenRouter specific structure
                                limit = data.get("data", {}).get("limit", 0)
                                usage = data.get("data", {}).get("usage", 0)
                                details = f"Usage: {usage}/{limit if limit else '∞'}"

                            self.results.append(DiagnosticResult("API", name, "OK", lat, details))
                        elif resp.status == 401:
                            self.results.append(DiagnosticResult("API", name, "FAIL", lat, "401 Unauthorized (Invalid Key)"))
                        else:
                            self.results.append(DiagnosticResult("API", name, "FAIL", lat, f"HTTP {resp.status}"))
                            
                except Exception as e:
                    self.results.append(DiagnosticResult("API", name, "FAIL", 0, str(e)))

    def check_infrastructure(self):
        """فحص المنافذ والخدمات المحلية"""
        ports = {
            "Redis": 6379,
            "Postgres": 5432,
            "Engine (Rust)": 50051,
            "Web Dashboard": 8080
        }

        for svc, port in ports.items():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            start_t = time.perf_counter()
            result = s.connect_ex(('127.0.0.1', port))
            lat = (time.perf_counter() - start_t) * 1000
            s.close()

            if result == 0:
                self.results.append(DiagnosticResult("INFRA", svc, "OK", lat, f"Port {port} Open"))
            else:
                self.results.append(DiagnosticResult("INFRA", svc, "FAIL", 0, f"Port {port} Closed"))

    def check_resources(self):
        """فحص موارد النظام"""
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(ROOT_DIR.anchor))

        status = "OK" if cpu < 85 and mem.percent < 85 else "WARN"
        self.results.append(DiagnosticResult("SYS", "CPU Load", status, 0, f"{cpu}%"))
        self.results.append(DiagnosticResult("SYS", "RAM Usage", status, 0, f"{mem.percent}% ({mem.available/1024/1024:.0f}MB Free)"))
        self.results.append(DiagnosticResult("SYS", "Disk Space", "OK", 0, f"{disk.free/1024/1024/1024:.1f}GB Free"))

    def print_report(self):
        """عرض التقرير الجنائي"""
        print("\n" + "="*80)
        print(f"ALPHA SOVEREIGN - DIAGNOSTIC REPORT")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')} | OS: {platform.system()} {platform.release()}")
        print(f"Root: {ROOT_DIR}")
        print("="*80)
        print(f"{'CAT':<6} | {'TARGET':<20} | {'STATUS':<6} | {'LATENCY':<8} | {'DETAILS'}")
        print("-" * 80)

        fail_count = 0
        for r in self.results:
            color = ""
            if r.status == "OK": color = "\033[92m" # Green
            elif r.status == "WARN": color = "\033[93m" # Yellow
            elif r.status == "FAIL": 
                color = "\033[91m" # Red
                fail_count += 1
            elif r.status == "SKIP": color = "\033[90m" # Grey
            
            reset = "\033[0m"
            lat_str = f"{r.latency:.1f}ms" if r.latency > 0 else "-"
            print(f"{color}{r.category:<6} | {r.target:<20} | {r.status:<6} | {lat_str:<8} | {r.details}{reset}")

        print("-" * 80)
        if fail_count == 0:
            print("\n✅ SYSTEM INTEGRITY VERIFIED. ALL SYSTEMS GO.")
        else:
            print(f"\n❌ SYSTEM COMPROMISED. {fail_count} CRITICAL ERRORS DETECTED.")
        print("="*80 + "\n")

    async def execute(self):
        self.load_environment()
        self.check_resources()
        self.check_infrastructure()
        await self.check_neural_apis()
        self.print_report()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # تفعيل ألوان التيرمينال في ويندوز
        os.system('color')
    
    diag = AlphaDiagnostic()
    try:
        asyncio.run(diag.execute())
    except KeyboardInterrupt:
        print("\nDiagnostic Aborted.")