#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - AUTOMATED DOCUMENTATION GENERATOR
# ==============================================================================
# Component: scripts/development/doc_generator.sh
# Responsibility: استخراج التوثيق الفني، الرسوم البيانية، وخرائط التبعيات من الكود.
# Pillar: Explainability (Truth in Documentation)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[DOC-GEN]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC}   $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}    $1"; }

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DOCS_ROOT="./docs"
TECH_DOCS="$DOCS_ROOT/technical"
API_DOCS="$DOCS_ROOT/api"
GRAPHS_DOCS="$DOCS_ROOT/architecture_graphs"

mkdir -p "$TECH_DOCS"
mkdir -p "$API_DOCS"
mkdir -p "$GRAPHS_DOCS"

# ==============================================================================
# PHASE 1: PRE-REQUISITES CHECK
# ==============================================================================
log_info "Phase 1: Verifying Documentation Tools..."

# pdoc: لتوليد توثيق بايثون
if ! command -v pdoc &> /dev/null; then
    log_warn "'pdoc' not found. Installing..."
    pip install pdoc
fi

# graphviz: لرسم المخططات
if ! command -v dot &> /dev/null; then
    log_err "'graphviz' is missing. Please install it (sudo apt install graphviz)."
    # لن نوقف السكريبت، لكن الرسوم لن تعمل
fi

# pydeps: لرسم خريطة تبعيات بايثون
if ! command -v pydeps &> /dev/null; then
    log_warn "'pydeps' not found. Installing..."
    pip install pydeps
fi

# ==============================================================================
# PHASE 2: PYTHON BRAIN DOCUMENTATION (The Logic)
# ==============================================================================
log_info "Phase 2: Extracting Brain Knowledge (Python)..."

# توليد HTML من الـ Docstrings داخل مجلد shield
# --html: المخرج HTML
# --force: استبدال القديم
# --output-dir: مكان الحفظ
pdoc --html --force --output-dir "$API_DOCS/brain" ./shield

if [ $? -eq 0 ]; then
    log_ok "Brain API documentation generated."
else
    log_err "Failed to generate Brain docs."
fi

# ==============================================================================
# PHASE 3: RUST ENGINE DOCUMENTATION (The Muscle)
# ==============================================================================
log_info "Phase 3: Extracting Engine Specifications (Rust)..."

if [ -d "./engine" ]; then
    cd ./engine
    # cargo doc: أداة Rust الرسمية
    # --no-deps: نوثق كودنا فقط، لا نريد توثيق المكتبات الخارجية
    # --document-private-items: نوثق حتى الدوال الداخلية (لأننا مطورون)
    cargo doc --no-deps --document-private-items --target-dir "../$API_DOCS/engine_build"
    
    # نقل النتيجة للمكان الصحيح
    mkdir -p "../$API_DOCS/engine"
    cp -r "../$API_DOCS/engine_build/doc/"* "../$API_DOCS/engine/"
    rm -rf "../$API_DOCS/engine_build"
    
    cd ..
    log_ok "Engine API documentation generated."
else
    log_warn "Engine directory not found. Skipping Rust docs."
fi

# ==============================================================================
# PHASE 4: ARCHITECTURE MAPPING (Forensic Visualization)
# ==============================================================================
log_info "Phase 4: Mapping Neural Pathways (Dependency Graphs)..."

# رسم خريطة الاعتماديات لمجلد shield
# هذا يكشف "الكود السباغيتي" (Spaghetti Code) والارتباطات الدائرية (Circular Imports)
if command -v pydeps &> /dev/null; then
    pydeps ./shield \
        --max-bacon 2 \
        --cluster \
        --rankdir TB \
        --noshow \
        -o "$GRAPHS_DOCS/brain_dependency_graph.svg"
        
    log_ok "Dependency Graph saved to $GRAPHS_DOCS/brain_dependency_graph.svg"
else
    log_warn "Skipping Dependency Graph (pydeps missing)."
fi

# ==============================================================================
# PHASE 5: SYSTEM STRUCTURE TREE
# ==============================================================================
log_info "Phase 5: Generating File System Topology..."

# إنشاء خريطة نصية للمشروع (تفيد في فهم الهيكلية بسرعة)
if command -v tree &> /dev/null; then
    tree -I 'venv|__pycache__|target|dist|.git|.idea|node_modules' \
         -o "$DOCS_ROOT/system_structure_map.txt" .
    log_ok "System Map generated."
else
    # بديل بسيط في حال عدم وجود tree
    find . -maxdepth 3 -not -path '*/.*' > "$DOCS_ROOT/system_structure_map.txt"
    log_warn "'tree' command missing, used 'find' fallback."
fi

# ==============================================================================
# PHASE 6: TIMESTAMPING (Forensic Watermark)
# ==============================================================================
log_info "Phase 6: Signing Documentation..."

MANIFEST="$DOCS_ROOT/documentation_manifest.json"

# الحصول على نسخة الـ Git الحالية (إن وجدت)
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "UNVERSIONED")

cat > "$MANIFEST" <<EOF
{
    "generation_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "git_commit": "$GIT_HASH",
    "generated_by": "$USER",
    "components": [
        "Brain (Python)",
        "Engine (Rust)",
        "Architecture Graphs"
    ],
    "status": "VALID"
}
EOF

echo "---------------------------------------------------"
echo -e "${GREEN}DOCUMENTATION GENERATION COMPLETE${NC}"
echo "---------------------------------------------------"
echo "API Docs:     file://$(realpath $API_DOCS)"
echo "Graphs:       file://$(realpath $GRAPHS_DOCS)"
echo "Manifest:     $MANIFEST"
echo "---------------------------------------------------"