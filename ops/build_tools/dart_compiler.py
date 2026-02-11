# =================================================================
# ALPHA SOVEREIGN ORGANISM - DART PROTO COMPILER
# =================================================================
# File: ops/build_tools/dart_compiler.py
# Status: PRODUCTION (Mobile/Desktop Bridge)
# Pillar: Integration (الركيزة: التكامل)
# Forensic Purpose: توليد أكواد Dart تلقائياً لضمان تطابق واجهة تطبيق Flutter مع المحرك.
# =================================================================

import os
import sys
import glob
import subprocess
import shutil

def compile_dart_protos():
    # 1. تحديد المسارات
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    proto_dir = os.path.join(base_dir, "schemas", "proto")
    out_dir = os.path.join(base_dir, "schemas", "generated", "dart")

    print(f"[*] Alpha Dart Compiler Initialized")
    print(f"[*] Source Dir: {proto_dir}")
    print(f"[*] Output Dir: {out_dir}")

    # 2. إنشاء مجلد الإخراج إذا لم يكن موجوداً
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # 3. التحقق من المتطلبات (protoc & dart-plugin)
    protoc_path = shutil.which("protoc")
    if not protoc_path:
        print("[-] CRITICAL: 'protoc' compiler not found.")
        sys.exit(1)

    # التحقق من وجود إضافة Dart
    # عادة ما يتم تفعيلها عبر: dart pub global activate protoc_plugin
    # نفترض أنها في المسار (PATH) أو نترك protoc يبحث عنها.
    
    # 4. البحث عن ملفات .proto
    proto_files = glob.glob(os.path.join(proto_dir, "*.proto"))
    if not proto_files:
        print("[-] Error: No .proto files found!")
        sys.exit(1)

    # 5. التجميع (Compilation)
    print(f"[*] Compiling {len(proto_files)} contracts to Dart...")
    
    # الأمر: protoc --dart_out=grpc:[output_dir] -I[proto_dir] [files...]
    cmd = [
        protoc_path,
        f"--dart_out=grpc:{out_dir}",
        f"-I{proto_dir}"
    ] + proto_files

    try:
        subprocess.check_call(cmd)
        print("[+] Dart Compilation Successful!")
        print(f"[+] Generated files in: {out_dir}")
        print("    - engine_control.pb.dart (Messages)")
        print("    - engine_control.pbenum.dart (Enums)")
        print("    - engine_control.pbgrpc.dart (Client Stub)")
    except subprocess.CalledProcessError as e:
        print(f"[-] Compilation Failed: {e}")
        print("[-] Hint: Ensure you installed the Dart plugin: 'dart pub global activate protoc_plugin'")
        sys.exit(1)

if __name__ == "__main__":
    compile_dart_protos()