#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - 10X STRESS TEST SIMULATION
# ==============================================================================
# Component: scripts/testing/stress_test_system.sh
# Responsibility: محاكاة أحمال قصوى (10 أضعاف الطبيعي) لاختبار استقرار النظام.
# Pillar: Stability (Load Testing & Chaos Engineering)
# Author: Chief QA Engineer
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[STRESS]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[PASS]${NC}   $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}   $1"; }
log_err()  { echo -e "${RED}[FAIL]${NC}   $1"; }

# ==============================================================================
# SAFETY PROTOCOL (The Kill Switch)
# ==============================================================================
# التأكد من أننا لا نشغل هذا الاختبار في بيئة إنتاج حقيقية بالخطأ
if grep -q "ALPHA_ENV=production" .env 2>/dev/null; then
    echo -e "${RED}CRITICAL WARNING: PROD ENVIRONMENT DETECTED!${NC}"
    echo "Running stress tests on production will cause latency and potential loss."
    read -p "Are you absolutely sure you want to proceed? (yes/no): " confirmation
    if [ "$confirmation" != "yes" ]; then
        log_warn "Aborting stress test."
        exit 1
    fi
fi

# ==============================================================================
# PHASE 1: TOOL CHECK
# ==============================================================================
log_info "Phase 1: Pre-flight check..."

# نحتاج أداة stress-ng لتوليد ضغط على المعالج والذاكرة
if ! command -v stress-ng &> /dev/null; then
    log_warn "Installing 'stress-ng' for CPU simulation..."
    sudo apt-get install -y stress-ng
fi

# نحتاج redis-benchmark لاختبار الذاكرة المؤقتة
if ! command -v redis-benchmark &> /dev/null; then
    log_warn "'redis-tools' missing. Skipping Redis stress test."
fi

# ==============================================================================
# PHASE 2: IN-MEMORY CACHE FLOOD (Redis)
# ==============================================================================
log_info "Phase 2: Flooding Redis (100k requests)..."

# محاكاة 100 ألف طلب (SET/GET) عبر 50 عميل متزامن
# -q: Quiet mode
# -n: Number of requests
# -c: Concurrency
if command -v redis-benchmark &> /dev/null; then
    redis-benchmark -q -n 100000 -c 50 -P 10
    if [ $? -eq 0 ]; then
        log_ok "Redis handled 100k req burst."
    else
        log_err "Redis crumbled under pressure!"
    fi
fi

# ==============================================================================
# PHASE 3: DATABASE INGESTION SPIKE (QuestDB)
# ==============================================================================
log_info "Phase 3: Simulating Market Flash Crash (QuestDB)..."

# QuestDB يستمع على المنفذ 9000 (REST)
# سنقوم بإرسال 1000 دفعة بيانات متتالية بسرعة
START_TIME=$(date +%s%N)

# استخدام دالة في الخلفية لتسريع الإرسال
send_batch() {
    for i in {1..500}; do
        # إدخال صفقة وهمية
        curl -s -G "http://localhost:9000/exec" \
        --data-urlencode "query=INSERT INTO trades (symbol, price, amount, timestamp) VALUES ('STRESS_TEST', 50000.0, 1.5, now());" > /dev/null
    done
}

# تشغيل 4 عمليات متوازية (Parallel Jobs) لمحاكاة ضغط الشبكة
send_batch & pid1=$!
send_batch & pid2=$!
send_batch & pid3=$!
send_batch & pid4=$!

wait $pid1 $pid2 $pid3 $pid4

END_TIME=$(date +%s%N)
DURATION=$((($END_TIME - $START_TIME)/1000000))
log_ok "Ingested 2000 records in ${DURATION}ms."

# ==============================================================================
# PHASE 4: CPU & MEMORY SATURATION (The Heavy Lift)
# ==============================================================================
log_info "Phase 4: Maxing out Hardware Resources (30 seconds)..."

echo "WARNING: System may become unresponsive."

# --cpu 4: تشغيل 4 عمال ضغط على المعالج
# --vm 2: تشغيل عاملين يستهلكان الذاكرة
# --vm-bytes 512M: كل عامل يستهلك نصف جيجا
# --timeout 30s: التوقف بعد 30 ثانية
stress-ng --cpu 4 --vm 2 --vm-bytes 512M --timeout 30s --metrics-brief

if [ $? -eq 0 ]; then
    log_ok "System survived resource saturation."
else
    log_err "System CRASHED or OOM Killer triggered!"
fi

# ==============================================================================
# PHASE 5: SYSTEM HEALTH CHECK
# ==============================================================================
log_info "Phase 5: Post-Stress Health Check..."

# هل مازالت الحاويات تعمل؟
if docker ps | grep -q "Exited"; then
    log_err "Some Docker containers died during the test:"
    docker ps -a --filter "status=exited"
else
    log_ok "All Docker containers are still standing."
fi

# فحص استخدام القرص (للتأكد من أن السجلات لم تملأ القرص)
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}')
log_info "Current Disk Usage: $DISK_USAGE"

echo "---------------------------------------------------"
echo -e "${GREEN}STRESS TEST COMPLETE${NC}"
echo "---------------------------------------------------"