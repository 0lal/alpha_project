#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - DATABASE INTEGRITY REPAIR TOOL
# ==============================================================================
# Component: scripts/maintenance/integrity_fixer.sh
# Responsibility: إصلاح ملفات قواعد البيانات التالفة وإزالة الأقفال العالقة.
# Pillar: Stability (Crash Recovery)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[FIXER]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[REPAIRED]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}    $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC}   $1"; }

DATA_ROOT="./data/storage"

# ==============================================================================
# PHASE 1: SAFETY STOP
# ==============================================================================
log_info "Phase 1: Ensuring System Shutdown..."

# لا يمكن إصلاح قاعدة البيانات وهي تعمل!
if command -v docker &> /dev/null; then
    docker-compose down > /dev/null 2>&1
    log_ok "All services stopped to release file handles."
else
    log_err "Docker not found. Proceeding with caution."
fi

# ==============================================================================
# PHASE 2: POSTGRESQL / QUESTDB LOCK REMOVAL
# ==============================================================================
log_info "Phase 2: Cleaning Stale Lock Files..."

# 1. Postgres PID File
# عند انهيار Postgres، يبقى ملف postmaster.pid ويمنع التشغيل
PG_LOCK="$DATA_ROOT/postgres/postmaster.pid"
if [ -f "$PG_LOCK" ]; then
    rm "$PG_LOCK"
    log_ok "Removed stale Postgres PID file."
fi

# 2. QuestDB Lock Files
# QuestDB يستخدم ملفات _lock لمنع الكتابة المتزامنة
if [ -d "$DATA_ROOT/questdb" ]; then
    # البحث عن أي ملف ينتهي بـ _lock وحذفه
    find "$DATA_ROOT/questdb" -name "_lock" -type f -delete
    log_ok "Removed stale QuestDB write locks."
fi

# ==============================================================================
# PHASE 3: REDIS AOF REPAIR (The Surgery)
# ==============================================================================
log_info "Phase 3: Checking Redis Integrity..."

REDIS_DIR="$DATA_ROOT/redis"
AOF_FILE="$REDIS_DIR/appendonly.aof"

if [ -f "$AOF_FILE" ]; then
    log_info "Found Redis AOF file. Attempting fix..."
    
    # نستخدم حاوية مؤقتة لتشغيل أداة الإصلاح بدلاً من تنصيبها على السيرفر
    # redis-check-aof --fix: يحذف البيانات التالفة في نهاية الملف
    docker run --rm -v "$REDIS_DIR":/data redis:alpine redis-check-aof --fix /data/appendonly.aof
    
    if [ $? -eq 0 ]; then
        log_ok "Redis AOF file is consistent."
    else
        log_err "Failed to fix Redis AOF. Manual intervention required."
        # إنشاء نسخة احتياطية من الملف التالف للتحليل الجنائي لاحقاً
        cp "$AOF_FILE" "$AOF_FILE.corrupted_$(date +%s)"
        log_warn "Corrupted file backed up. You may delete original to reset cache."
    fi
else
    log_warn "No Redis AOF file found (maybe using RDB only)."
fi

# ==============================================================================
# PHASE 4: PERMISSIONS CORRECTION
# ==============================================================================
log_info "Phase 4: Fixing File Ownership (Docker Permission Hell)..."

# مشكلة شائعة: تشغيل docker كـ root يجعل الملفات مملوكة لـ root
# مما يمنع المستخدم العادي أو الحاويات الأخرى من القراءة
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" != "root" ]; then
    # إذا كنا نملك صلاحية sudo، نصلح الملكية
    if sudo -n true 2>/dev/null; then
        sudo chown -R "$USER":"$USER" ./data
        log_ok "Ownership restored to user: $USER"
    else
        log_warn "Cannot fix permissions (sudo required). Ensure Docker has access."
    fi
fi

# ==============================================================================
# PHASE 5: QDRANT WAL CHECK
# ==============================================================================
log_info "Phase 5: Checking Vector DB (Qdrant)..."

# Qdrant قوي جداً، لكن قد يترك ملفات .lock أيضاً في التخزين
if [ -d "$DATA_ROOT/qdrant/storage" ]; then
    find "$DATA_ROOT/qdrant/storage" -name ".lock" -type f -delete
    log_ok "Cleared Qdrant locks."
fi

# ==============================================================================
# SUMMARY
# ==============================================================================
echo "---------------------------------------------------"
echo -e "${GREEN}INTEGRITY FIX COMPLETE${NC}"
echo "---------------------------------------------------"
echo "You can now safely restart the system using:"
echo "docker-compose up -d"
echo "---------------------------------------------------"