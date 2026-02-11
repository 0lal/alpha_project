#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - SEQUENCED REBOOT PROTOCOL
# ==============================================================================
# Component: scripts/lifecycle/alpha_reboot.sh
# Responsibility: إعادة تشغيل النظام بترتيب صارم لضمان سلامة الذاكرة (Pillar: Stability).
# Pillar: Stability (Graceful Shutdown & Cold Start)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[LIFECYCLE]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[ONLINE]${NC}    $1"; }
log_warn() { echo -e "${YELLOW}[WAIT]${NC}      $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC}     $1"; }

# ==============================================================================
# PHASE 1: PRE-FLIGHT CHECK
# ==============================================================================
# التأكد من وجود ملف البيئة
if [ ! -f ".env" ]; then
    log_err "Configuration file (.env) is missing! Cannot boot."
    exit 1
fi

log_info "Initiating Alpha Sovereign Reboot Sequence..."

# ==============================================================================
# PHASE 2: GRACEFUL SHUTDOWN (The Coma)
# ==============================================================================
log_info "Phase 2: Stopping Services (Gracefully)..."

# 1. إيقاف العقل والمحرك أولاً (لمنع اتخاذ قرارات جديدة)
if docker ps | grep -q alpha_brain; then
    log_warn "Stopping Brain (Python)..."
    docker stop alpha_brain
fi

if docker ps | grep -q alpha_engine; then
    log_warn "Stopping Engine (Rust)..."
    docker stop alpha_engine
fi

# 2. إجبار قواعد البيانات على الحفظ (Flush to Disk)
# هذا يمنع فقدان البيانات الموجودة في RAM
if docker ps | grep -q alpha_redis; then
    log_warn "Flushing Redis Memory to Disk..."
    docker exec alpha_redis redis-cli save > /dev/null
fi

# 3. إيقاف البنية التحتية بالكامل
docker-compose down --remove-orphans
log_ok "All Systems Halted Safely."

# ==============================================================================
# PHASE 3: INTEGRITY & MAINTENANCE (The Surgery)
# ==============================================================================
log_info "Phase 3: Running Maintenance Checks..."

# إزالة ملفات القفل القديمة وإصلاح أي تلف محتمل
./scripts/maintenance/integrity_fixer.sh > /dev/null 2>&1
./scripts/maintenance/data_purger.sh > /dev/null 2>&1

log_ok "System Integrity Verified."

# ==============================================================================
# PHASE 4: SEQUENCED BOOT (The Awakening)
# ==============================================================================
log_info "Phase 4: Booting Infrastructure..."

# دالة انتظار الخدمة
wait_for_port() {
    local host=$1
    local port=$2
    local name=$3
    local retries=30
    
    echo -n "Waiting for $name ($host:$port)... "
    for ((i=0; i<retries; i++)); do
        # استخدام nc (netcat) لفحص المنفذ
        if nc -z "$host" "$port" 2>/dev/null; then
            echo -e "${GREEN}READY${NC}"
            return 0
        fi
        sleep 1
    done
    echo -e "${RED}TIMEOUT${NC}"
    return 1
}

# 1. تشغيل قواعد البيانات أولاً (القلب)
docker-compose up -d redis questdb qdrant

# الانتظار حتى تصبح جاهزة
wait_for_port localhost 6379 "Redis (Cache)"
wait_for_port localhost 9000 "QuestDB (Time-Series)"
wait_for_port localhost 6333 "Qdrant (Vector Memory)"

# 2. تشغيل المحرك (العضلات)
log_info "Booting Engine (Rust)..."
docker-compose up -d engine
# المحرك ليس له منفذ خارجي عادة، ننتظر قليلاً
sleep 2

# 3. تشغيل العقل (الروح)
log_info "Awakening Brain (Python AI)..."
docker-compose up -d brain

# 4. تشغيل الواجهة (الوجه)
log_info "Loading UI (Flutter Web)..."
docker-compose up -d ui

# ==============================================================================
# PHASE 5: POST-BOOT VERIFICATION
# ==============================================================================
echo "---------------------------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo "---------------------------------------------------"

if docker ps | grep -q "Restarting"; then
    log_err "Some containers are in a crash loop! Check logs."
    exit 1
else
    log_ok "SYSTEM REBOOT SUCCESSFUL. ALPHA IS LIVE."
fi