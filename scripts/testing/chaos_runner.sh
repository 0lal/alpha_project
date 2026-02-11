#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - CHAOS ENGINEERING RUNNER
# ==============================================================================
# Component: scripts/testing/chaos_runner.sh
# Responsibility: حقن أعطال متعمدة (Process Kill, Network Partition) لاختبار التعافي.
# Pillar: Stability (Antifragility & Self-Healing Verification)
# Author: Chief Chaos Engineer
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[CHAOS]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[HEALED]${NC} $1"; }
log_err()  { echo -e "${RED}[DIED]${NC}   $1"; }
log_warn() { echo -e "${YELLOW}[ATTACK]${NC} $1"; }

# ==============================================================================
# SAFETY PROTOCOL (The Kill Switch)
# ==============================================================================
if grep -q "ALPHA_ENV=production" .env 2>/dev/null; then
    echo -e "${RED}CRITICAL: YOU ARE TARGETING PRODUCTION!${NC}"
    echo "This script will indiscriminately KILL active services."
    read -p "Type 'I ACCEPT THE RISK' to proceed: " confirmation
    if [ "$confirmation" != "I ACCEPT THE RISK" ]; then
        exit 1
    fi
fi

# ==============================================================================
# CHAOS TOOLKIT
# ==============================================================================

# دالة انتظار التعافي
wait_for_recovery() {
    local container=$1
    local max_retries=10
    local count=0
    
    log_info "Waiting for $container to self-heal..."
    
    while [ $count -lt $max_retries ]; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
            return 0 # Container is back online
        fi
        sleep 2
        ((count++))
    done
    return 1 # Failed to recover
}

# ==============================================================================
# SCENARIO 1: THE ASSASSINATION (Container Kill)
# ==============================================================================
log_info "Scenario 1: Simulating Sudden Process Death (SIGKILL)..."

TARGET="alpha_redis"
log_warn "Injecting Failure: Killing $TARGET..."

# قتل الحاوية فوراً (بدون إغلاق آمن)
docker kill $TARGET > /dev/null 2>&1

# التحقق: هل قام Docker Restart Policy أو HealthRecoveryNode بإعادتها؟
if wait_for_recovery "$TARGET"; then
    log_ok "System survived the assassination of $TARGET."
else
    log_err "System FAILED to recover $TARGET. Manual intervention required."
    exit 1
fi

# ==============================================================================
# SCENARIO 2: THE NETWORK BLACKOUT (Partitioning)
# ==============================================================================
log_info "Scenario 2: Simulating Network Partition (Severing Connection)..."

TARGET="alpha_questdb"
NETWORK="alpha_net" # الشبكة الافتراضية

log_warn "Injecting Failure: Disconnecting $TARGET from network..."
docker network disconnect $NETWORK $TARGET > /dev/null 2>&1

log_info "Network is DOWN. App should queue writes, not crash."
sleep 5 # محاكاة انقطاع لمدة 5 ثوانٍ

log_info "Restoring Network..."
docker network connect $NETWORK $TARGET > /dev/null 2>&1

# التحقق: هل قاعدة البيانات قابلة للوصول مجدداً؟
sleep 2
if curl -s "http://localhost:9000" > /dev/null; then
    log_ok "Connectivity restored. System allows reconnection."
else
    log_err "$TARGET did not recover from network partition."
fi

# ==============================================================================
# SCENARIO 3: THE ZOMBIE FREEZE (SIGSTOP)
# ==============================================================================
log_info "Scenario 3: Simulating Frozen Process (The Hang)..."

# سنستهدف الحاويات إن وجدت، أو نعطي مثالاً نظرياً
TARGET="alpha_redis"

log_warn "Injecting Failure: Freezing $TARGET (CPU Pause)..."
docker pause $TARGET > /dev/null 2>&1

log_info "Service is FROZEN. Requests should timeout."
sleep 5

log_warn "Unfreezing service..."
docker unpause $TARGET > /dev/null 2>&1

if docker ps | grep -q "$TARGET"; then
    log_ok "$TARGET resumed operation successfully."
else
    log_err "$TARGET crashed after unpause."
fi

# ==============================================================================
# SCENARIO 4: FILE SYSTEM CORRUPTION (Simulated)
# ==============================================================================
log_info "Scenario 4: Simulating Lock File Leftover..."

# محاكاة وجود ملف قفل قديم يمنع التشغيل
touch "./data/storage/postgres/postmaster.pid"
log_warn "Created fake stale lock file."

log_info "Running Integrity Fixer to heal..."
./scripts/maintenance/integrity_fixer.sh > /dev/null 2>&1

if [ ! -f "./data/storage/postgres/postmaster.pid" ]; then
    log_ok "Integrity Fixer successfully removed the blockage."
else
    log_err "Integrity Fixer FAILED to clean up."
fi

# ==============================================================================
# SUMMARY
# ==============================================================================
echo "---------------------------------------------------"
echo -e "${GREEN}CHAOS DRILL COMPLETE${NC}"
echo "---------------------------------------------------"
echo "If all tests passed, the system is officially ANTIFRAGILE."
echo "It can sustain: Kills, Network Drops, and Freezes."
echo "---------------------------------------------------"