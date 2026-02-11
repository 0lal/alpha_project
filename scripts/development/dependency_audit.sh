#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - DEPENDENCY SECURITY AUDIT
# ==============================================================================
# Component: scripts/development/dependency_audit.sh
# Responsibility: فحص المكتبات الخارجية بحثاً عن ثغرات أمنية (Supply Chain Security).
# Pillar: Security (Vulnerability Management)
# Author: Chief Security Officer
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[AUDIT]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[SECURE]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[RISK]${NC}   $1"; }
log_err()  { echo -e "${RED}[VULN]${NC}   $1"; }

# ==============================================================================
# CONFIGURATION
# ==============================================================================
LOG_DIR="./data/logs/security_audits"
REPORT_FILE="$LOG_DIR/audit_report_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "$LOG_DIR"
touch "$REPORT_FILE"

echo "ALPHA SOVEREIGN SECURITY AUDIT REPORT" > "$REPORT_FILE"
echo "Date: $(date)" >> "$REPORT_FILE"
echo "---------------------------------------------------" >> "$REPORT_FILE"

# ==============================================================================
# PHASE 1: PYTHON ECOSYSTEM (Brain)
# ==============================================================================
log_info "Phase 1: Auditing Python Dependencies (Pip)..."

# التحقق من وجود أداة pip-audit
if ! command -v pip-audit &> /dev/null; then
    log_warn "Installing pip-audit tool..."
    pip install pip-audit
fi

log_info "Scanning Python environment against PyPI Vulnerability DB..."
echo -e "\n[PYTHON AUDIT]" >> "$REPORT_FILE"

# تشغيل الفحص
# --desc: إظهار وصف الثغرة
# tee: للكتابة في الملف وعلى الشاشة في نفس الوقت
pip-audit --desc | tee -a "$REPORT_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_ok "Python Dependencies are clean."
else
    log_err "VULNERABILITIES FOUND IN PYTHON PACKAGES! CHECK REPORT."
fi

# ==============================================================================
# PHASE 2: RUST ECOSYSTEM (Engine)
# ==============================================================================
log_info "Phase 2: Auditing Rust Dependencies (Cargo)..."

if [ -d "./engine" ]; then
    cd ./engine
    
    # التحقق من وجود cargo-audit
    if ! command -v cargo-audit &> /dev/null; then
        log_warn "Installing cargo-audit (RustSec)..."
        cargo install cargo-audit
    fi

    echo -e "\n[RUST AUDIT]" >> "../$REPORT_FILE"
    
    # الفحص باستخدام قاعدة بيانات RustSec Advisory Database
    cargo audit | tee -a "../$REPORT_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_ok "Rust Dependencies are clean."
    else
        log_err "VULNERABILITIES FOUND IN RUST CRATES! CHECK REPORT."
    fi
    
    cd ..
else
    log_warn "Engine directory missing. Skipping Rust audit."
fi

# ==============================================================================
# PHASE 3: FLUTTER/DART ECOSYSTEM (UI)
# ==============================================================================
log_info "Phase 3: Auditing Flutter Dependencies (Pub)..."

if [ -d "./ui" ]; then
    cd ./ui
    
    echo -e "\n[FLUTTER AUDIT]" >> "../$REPORT_FILE"
    
    # فحص المكتبات القديمة (Outdated) والتي غالباً ما تكون مدخلاً للثغرات
    # Flutter ليس لديه أداة audit رسمية قوية مثل cargo-audit، لذا نعتمد على outdated
    flutter pub outdated --transitive | tee -a "../$REPORT_FILE"
    
    log_info "Flutter audit complete (Check for major version mismatches)."
    
    cd ..
else
    log_warn "UI directory missing. Skipping Flutter audit."
fi

# ==============================================================================
# PHASE 4: SUMMARY & FORENSICS
# ==============================================================================
echo "---------------------------------------------------"
log_info "Audit Complete."
echo "Audit Report Saved to: $REPORT_FILE"
echo "---------------------------------------------------"

# تحليل سريع للنتائج
VULN_COUNT=$(grep -c "Vulnerability" "$REPORT_FILE")
if [ "$VULN_COUNT" -gt 0 ]; then
    echo -e "${RED}CRITICAL: $VULN_COUNT potential vulnerabilities detected!${NC}"
    echo -e "${RED}ACTION REQUIRED: Update affected packages immediately.${NC}"
    exit 1 # نخرج برمز خطأ لمنع عملية البناء (CI/CD Blocking)
else
    echo -e "${GREEN}System appears secure. No known vulnerabilities detected.${NC}"
    exit 0
fi