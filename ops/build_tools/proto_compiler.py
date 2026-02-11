# -*- coding: utf-8 -*-
# =================================================================
# ALPHA SOVEREIGN ORGANISM - ADVANCED PROTO COMPILER
# =================================================================
# File: ops/build_tools/proto_compiler.py
# Status: PRODUCTION (Self-Healing & Auto-Patching)
# Role: تحويل العقود العصبية (.proto) إلى أنسجة حية (.py) مع تصحيح المسارات.
# =================================================================

import os
import sys
import glob
import subprocess
import shutil
import re
from pathlib import Path

# --- إعدادات الألوان للمخرجات ---
CYAN = '\033[96m'
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

class AlphaProtoCompiler:
    def __init__(self):
        # 1. تحديد الجذور ديناميكياً (Dynamic Root Discovery)
        self.current_script = Path(__file__).resolve()
        # نعود للخلف 3 مستويات: ops/build_tools/ -> ops/ -> alpha_project/
        self.project_root = self.current_script.parent.parent.parent
        
        # مسار ملفات البروتوكول المصدرية
        self.proto_src_dir = self.project_root / "schemas" / "proto"
        
        # مسار الإخراج المستهدف (داخل Brain مباشرة لضمان الرؤية)
        self.output_dir = self.project_root / "brain" / "generated"

    def log(self, msg, level="INFO"):
        prefix = f"{GREEN}[+]{RESET}" if level == "SUCCESS" else \
                 f"{RED}[!]{RESET}" if level == "ERROR" else \
                 f"{CYAN}[*]{RESET}"
        print(f"{prefix} {msg}")

    def sanitize_environment(self):
        """تنظيف بيئة الإخراج من الملفات القديمة لتجنب التضارب"""
        self.log("Cleaning old neural pathways...", "INFO")
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # إنشاء ملف __init__.py لجعل المجلد Package
        (self.output_dir / "__init__.py").touch()

    def get_proto_files(self):
        files = list(self.proto_src_dir.glob("*.proto"))
        if not files:
            self.log(f"No .proto files found in {self.proto_src_dir}", "ERROR")
            sys.exit(1)
        return files

    def compile(self):
        """تنفيذ عملية الترجمة باستخدام grpc_tools"""
        self.sanitize_environment()
        proto_files = self.get_proto_files()
        
        self.log(f"Compiling {len(proto_files)} protocols from Schema Layer...", "INFO")
        
        # بناء الأمر
        # python -m grpc_tools.protoc -I<src> --python_out=<dst> --grpc_python_out=<dst> <files>
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"-I{self.proto_src_dir}",
            f"--python_out={self.output_dir}",
            f"--grpc_python_out={self.output_dir}"
        ] + [str(p) for p in proto_files]

        try:
            subprocess.check_call(cmd)
            self.log("Compilation successful. Generating artifacts...", "SUCCESS")
        except subprocess.CalledProcessError as e:
            self.log(f"Protoc compilation failed: {e}", "ERROR")
            sys.exit(1)

    def surgical_patch_imports(self):
        """
        الحل الجذري لمشكلة Relative Imports في بايثون 3.
        يقوم هذا التابع بفتح الملفات المولدة وتعديل سطور الاستيراد.
        من: import brain_service_pb2 as ...
        إلى: from . import brain_service_pb2 as ...
        """
        self.log("Applying surgical patches to imports...", "INFO")
        
        generated_files = list(self.output_dir.glob("*.py"))
        patched_count = 0

        # نمط البحث: يبحث عن أي سطر يبدأ بـ import وينتهي بـ _pb2
        # Regex explanation: ^import (.*_pb2) -> يلتقط اسم المديول
        import_pattern = re.compile(r'^import (\w+_pb2)', re.MULTILINE)

        for py_file in generated_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # البحث والاستبدال
                if import_pattern.search(content):
                    # الاستبدال بـ from . import \1
                    new_content = import_pattern.sub(r'from . import \1', content)
                    
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    patched_count += 1
            except Exception as e:
                self.log(f"Failed to patch {py_file.name}: {e}", "ERROR")

        self.log(f"Patched {patched_count} files. System is strictly linked.", "SUCCESS")

    def execute(self):
        print(f"{CYAN}==========================================")
        print(f" ALPHA SOVEREIGN - PROTOCOL COMPILER v2.0")
        print(f"=========================================={RESET}")
        
        # 1. التأكد من الأدوات
        try:
            import grpc_tools
        except ImportError:
            self.log("Missing dependency: grpcio-tools", "ERROR")
            print(f"{YELLOW}Run: pip install grpcio-tools{RESET}")
            sys.exit(1)

        # 2. الترجمة
        self.compile()

        # 3. الإصلاح (أهم خطوة)
        self.surgical_patch_imports()
        
        print(f"\n{GREEN}>>> Neural Network Interface Ready.{RESET}")
        print(f"Location: {self.output_dir}\n")

if __name__ == "__main__":
    compiler = AlphaProtoCompiler()
    compiler.execute()