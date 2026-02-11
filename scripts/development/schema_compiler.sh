#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - UNIVERSAL SCHEMA COMPILER
# ==============================================================================
# Component: scripts/development/schema_compiler.sh
# Responsibility: ترجمة ملفات Proto/Flatbuffers إلى كود (Rust, Python, Dart).
# Pillar: Efficiency (Polyglot Synchronization)
# Author: Chief DevOps Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[COMPILER]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC}   $1"; }

# ==============================================================================
# CONFIGURATION PATHS
# ==============================================================================
SCHEMA_ROOT="./schemas"
PROTO_DIR="$SCHEMA_ROOT/proto"
FBS_DIR="$SCHEMA_ROOT/fbs"

# Output Directories
RUST_OUT="./engine/src/generated"
PYTHON_OUT="./shield/core/generated"
DART_OUT="./ui/lib/generated"

# ==============================================================================
# PHASE 1: PRE-FLIGHT CHECK (Tools Verification)
# ==============================================================================
log_info "Phase 1: Verifying Compiler Tools..."

if ! command -v protoc &> /dev/null; then
    log_err "'protoc' not found! Please install Protocol Buffers Compiler."
    exit 1
fi

if ! command -v flatc &> /dev/null; then
    log_err "'flatc' not found! Please install FlatBuffers Compiler."
    # لن نوقف السكريبت هنا، قد لا نستخدم FlatBuffers في البداية
fi

# التأكد من وجود Dart Protoc Plugin
if ! command -v protoc-gen-dart &> /dev/null; then
    log_err "'protoc-gen-dart' not found. Run 'dart pub global activate protoc_plugin'."
    # تحذير فقط
fi

# ==============================================================================
# PHASE 2: CLEANING (Hygiene)
# ==============================================================================
log_info "Phase 2: Cleaning old artifacts..."

# تنظيف المجلدات لضمان عدم بقاء ملفات قديمة (Zombie Code)
rm -rf "$PYTHON_OUT" "$DART_OUT" # لا نمس Rust لأنه يدار بواسطة build.rs غالباً
mkdir -p "$PYTHON_OUT"
mkdir -p "$DART_OUT"
mkdir -p "$RUST_OUT"

# إنشاء __init__.py للبايثون ليصبح Package
touch "$PYTHON_OUT/__init__.py"

# ==============================================================================
# PHASE 3: COMPILING PROTOCOL BUFFERS
# ==============================================================================
log_info "Phase 3: Compiling Protobuf Schemas..."

if [ -d "$PROTO_DIR" ] && [ "$(ls -A $PROTO_DIR/*.proto 2>/dev/null)" ]; then
    
    # 3.1 Python Compilation
    log_info "-> Generating Python Code..."
    protoc -I="$PROTO_DIR" \
           --python_out="$PYTHON_OUT" \
           "$PROTO_DIR"/*.proto
    
    # إصلاح مشاكل الاستيراد النسبية في بايثون (Common Protobuf Bug)
    # يحول "import xyz_pb2" إلى "from . import xyz_pb2"
    if [ "$(uname)" == "Darwin" ]; then
        sed -i '' 's/^import.*_pb2/from . \0/' "$PYTHON_OUT"/*_pb2.py
    else
        sed -i 's/^import.*_pb2/from . \0/' "$PYTHON_OUT"/*_pb2.py
    fi

    # 3.2 Dart Compilation
    if command -v protoc-gen-dart &> /dev/null; then
        log_info "-> Generating Dart Code..."
        protoc -I="$PROTO_DIR" \
               --dart_out=grpc:"$DART_OUT" \
               "$PROTO_DIR"/*.proto
    fi

    # 3.3 Rust Compilation
    # ملاحظة: Rust يفضل استخدام `prost-build` داخل `build.rs`
    # لكن يمكننا توليد ملفات هنا إذا لزم الأمر
    # log_info "-> Rust generation is handled by Engine's build.rs"

else
    log_info "No .proto files found to compile."
fi

# ==============================================================================
# PHASE 4: COMPILING FLATBUFFERS (High Performance)
# ==============================================================================
log_info "Phase 4: Compiling FlatBuffers Schemas..."

if [ -d "$FBS_DIR" ] && [ "$(ls -A $FBS_DIR/*.fbs 2>/dev/null)" ] && command -v flatc &> /dev/null; then
    
    for fbs in "$FBS_DIR"/*.fbs; do
        filename=$(basename "$fbs")
        log_info "-> Compiling $filename..."
        
        # Rust
        flatc --rust -o "$RUST_OUT" "$fbs"
        
        # Python
        flatc --python -o "$PYTHON_OUT" "$fbs"
        
        # Dart
        flatc --dart -o "$DART_OUT" "$fbs"
    done

else
    log_info "No .fbs files found or flatc missing."
fi

# ==============================================================================
# PHASE 5: SUMMARY
# ==============================================================================
echo "---------------------------------------------------"
echo -e "${GREEN}SCHEMA COMPILATION COMPLETE${NC}"
echo "---------------------------------------------------"
echo "Python: $PYTHON_OUT"
echo "Dart:   $DART_OUT"
echo "Rust:   $RUST_OUT"
echo "---------------------------------------------------"
echo -e "${YELLOW}NOTE: If you added new fields, remember to restart the Engine & Brain.${NC}"