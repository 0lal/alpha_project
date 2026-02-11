#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - AUTOMATED DATA PURGER
# ==============================================================================
# Component: scripts/maintenance/data_purger.sh
# Responsibility: تنظيف البيانات القديمة، السجلات المتضخمة، ومخلفات البناء.
# Pillar: Efficiency (Storage Optimization)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[PURGE]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[CLEANED]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[SKIP]${NC}    $1"; }

# ==============================================================================
# CONFIGURATION (RETENTION POLICY)
# ==============================================================================
# الأيام التي نحتفظ فيها بالسجلات النصية (Logs)
LOG_RETENTION_DAYS=7

# الأيام التي نحتفظ فيها بالبيانات المؤقتة (Temp)
TEMP_RETENTION_HOURS=24

# المسارات المستهدفة
LOG_DIR="./data/logs"
TEMP_DIR="./dist/temp"
BUILD_CACHE="./target" # Rust Cache
PY_CACHE_PATTERN="__pycache__"

# ==============================================================================
# PHASE 1: LOG ROTATION & CLEANUP
# ==============================================================================
log_info "Phase 1: Purging old logs (Older than ${LOG_RETENTION_DAYS} days)..."

if [ -d "$LOG_DIR" ]; then
    # 1. ضغط السجلات القديمة (أكثر من يوم واحد) لتوفير المساحة
    find "$LOG_DIR" -type f -name "*.log" -mtime +1 -exec gzip {} \; 2>/dev/null
    log_ok "Compressed logs older than 24h."

    # 2. حذف السجلات المضغوطة القديمة جداً (أكثر من فترة الاحتفاظ)
    find "$LOG_DIR" -type f -name "*.gz" -mtime +$LOG_RETENTION_DAYS -delete
    log_ok "Deleted log archives older than ${LOG_RETENTION_DAYS} days."
else
    log_warn "Log directory not found."
fi

# ==============================================================================
# PHASE 2: CODE ARTIFACTS CLEANUP
# ==============================================================================
log_info "Phase 2: Cleaning Python & Build Artifacts..."

# حذف مجلدات __pycache__ (تتراكم وتسبب مشاكل أحياناً بعد التحديثات)
find . -type d -name "$PY_CACHE_PATTERN" -exec rm -rf {} + 2>/dev/null
log_ok "Removed Python bytecode caches (__pycache__)."

# حذف ملفات .pytest_cache
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
log_ok "Removed Test caches."

# تنظيف الملفات المؤقتة
if [ -d "$TEMP_DIR" ]; then
    find "$TEMP_DIR" -type f -mmin +$((TEMP_RETENTION_HOURS * 60)) -delete
    log_ok "Cleared temp directory."
fi

# ==============================================================================
# PHASE 3: DOCKER SYSTEM PRUNE (The Heavy Duty)
# ==============================================================================
log_info "Phase 3: Pruning Docker Artifacts..."

if command -v docker &> /dev/null; then
    # حذف الحاويات المتوقفة، الشبكات غير المستخدمة، والصور المعلقة (Dangling)
    # -f: Force (بدون تأكيد)
    # --volumes: تنظيف الـ Volumes غير المستخدمة (خطر، لذا نستخدمه بحذر)
    
    # نكتفي بتنظيف الصور المعلقة والحاويات المتوقفة لتوفير المساحة
    docker container prune -f > /dev/null 2>&1
    docker image prune -f > /dev/null 2>&1
    
    log_ok "Docker Dangling Images & Stopped Containers pruned."
else
    log_warn "Docker not found. Skipping."
fi

# ==============================================================================
# PHASE 4: DATABASE MAINTENANCE (QuestDB Vacuum)
# ==============================================================================
log_info "Phase 4: Database Maintenance..."

# QuestDB يقوم بحفظ البيانات في مجلدات يومية.
# لإزالة البيانات القديمة جداً (مثلاً أقدم من 90 يوم)، يمكننا استخدام SQL
# لكن سنفترض هنا أننا نعتمد على سياسة الحذف اليدوي أو عبر API

# مثال: حذف ملفات الاستيراد المؤقتة التي تتركها QuestDB أحياناً
if [ -d "./data/storage/questdb" ]; then
    # البحث عن ملفات مؤقتة قديمة داخل مجلد البيانات
    find "./data/storage/questdb" -name "*.tmp" -mtime +2 -delete
    log_ok "Cleaned QuestDB temp files."
fi

# ==============================================================================
# PHASE 5: DISK USAGE REPORT
# ==============================================================================
echo "---------------------------------------------------"
echo -e "${GREEN}PURGE COMPLETE${NC}"
echo "---------------------------------------------------"
echo "Current Disk Usage:"
du -sh ./data 2>/dev/null
du -sh ./dist 2>/dev/null
echo "---------------------------------------------------"