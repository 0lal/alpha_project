# =================================================================
# ALPHA SOVEREIGN ORGANISM - FLATBUFFERS PYTHON COMPILER
# =================================================================
# File: ops/build_tools/flatbuffers_compiler.py
# Status: PRODUCTION (Automation Tool)
# Pillar: Integration & Performance
# Forensic Purpose: توليد أكواد بايثون لقراءة بيانات FlatBuffers الثنائية دون تدخل بشري.
# =================================================================

import os
import sys
import glob
import subprocess
import shutil

def compile_flatbuffers():
    # 1. تحديد المسارات المطلقة
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    fbs_dir = os.path.join(base_dir, "schemas", "flatbuffers")
    out_dir = os.path.join(base_dir, "schemas", "generated", "python")

    print(f"[*] Alpha FlatBuffers Compiler Initialized")
    print(f"[*] Schema Dir: {fbs_dir}")
    print(f"[*] Output Dir: {out_dir}")

    # 2. التحقق من وجود المترجم flatc
    # يجب أن يكون flatc مثبتاً ومضافاً لمسار النظام (PATH)
    flatc_path = shutil.which("flatc")
    if not flatc_path:
        # محاولة البحث في مسارات شائعة في ويندوز/لينكس إذا لم يكن في PATH
        common_paths = [
            "C:\\Program Files\\flatbuffers\\flatc.exe",
            "/usr/local/bin/flatc",
            "/usr/bin/flatc"
        ]
        for p in common_paths:
            if os.path.exists(p):
                flatc_path = p
                break
    
    if not flatc_path:
        print("[-] CRITICAL ERROR: 'flatc' compiler not found!")
        print("[-] Please install FlatBuffers compiler (flatc) and add it to PATH.")
        print("[-] Download: https://github.com/google/flatbuffers/releases")
        sys.exit(1)
    
    print(f"[*] Found flatc at: {flatc_path}")

    # 3. العثور على ملفات المخططات (.fbs)
    fbs_files = glob.glob(os.path.join(fbs_dir, "*.fbs"))
    if not fbs_files:
        print("[-] Error: No .fbs files found!")
        sys.exit(1)

    # 4. عملية الترجمة (Compilation Loop)
    success_count = 0
    for fbs_file in fbs_files:
        filename = os.path.basename(fbs_file)
        print(f"[*] Compiling {filename}...")
        
        # الأمر: flatc --python -o [output_dir] [input_file]
        cmd = [
            flatc_path,
            "--python",
            "-o", out_dir,
            fbs_file
        ]

        try:
            subprocess.check_call(cmd)
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to compile {filename}: {e}")
            sys.exit(1)

    # 5. المعالجة اللاحقة (Post-Processing)
    # FlatBuffers ينشئ مجلدات بناءً على namespace (مثل alpha/market/v1).
    # نحتاج للتأكد من وجود ملفات __init__.py لتتعرف عليها بايثون كحزم (Packages).
    
    print("[*] Verifying Python Package Structure...")
    for root, dirs, files in os.walk(out_dir):
        if "__init__.py" not in files:
            print(f"    [+] Creating __init__.py in {os.path.relpath(root, base_dir)}")
            with open(os.path.join(root, "__init__.py"), "w") as f:
                f.write("# Auto-generated namespace package\n")

    print("-" * 50)
    print(f"[+] BUILD COMPLETE: Compiled {success_count} schemas successfully.")
    print(f"[+] Python modules ready in: {out_dir}")

if __name__ == "__main__":
    compile_flatbuffers()