#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - EMERGENCY FAILOVER PROTOCOL (DEFCON 1)
# ==============================================================================
# Component: scripts/lifecycle/deploy_emergency.sh
# Responsibility: النشر الفوري للنظام على خادم الطوارئ عند سقوط العقدة الرئيسية.
# Pillar: Stability (Disaster Recovery & Business Continuity)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[DEFCON-1]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[LIVE]${NC}     $1"; }
log_err()  { echo -e "${RED}[FATAL]${NC}    $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}     $1"; }

# ==============================================================================
# CONFIGURATION (THE ESCAPE ROUTE)
# ==============================================================================
# مسار كبسولات الإنقاذ (من sovereign_deployer.py)
CAPSULE_DIR="./dist/capsules"

# إعدادات الخادم البديل (يجب أن تكون معدة مسبقاً في .env أو هنا)
# في الواقع، هذه القيم تأتي من Vault آمن
FAILOVER_HOST="192.168.100.99" # عنوان IP للخادم الاحتياطي
FAILOVER_USER="alpha_admin"
SSH_KEY="./config/security/transport/alpha_transport_id"
REMOTE_DEST="/opt/alpha_sovereign"

# ==============================================================================
# PHASE 1: IDENTIFY THE SURVIVOR (Find latest capsule)
# ==============================================================================
log_info "Phase 1: Locating latest Rescue Capsule..."

# العثور على أحدث ملف tar.gz
LATEST_CAPSULE=$(ls -t "$CAPSULE_DIR"/alpha_rescue_capsule_*.tar.gz 2>/dev/null | head -n 1)

if [ -z "$LATEST_CAPSULE" ]; then
    log_err "No Rescue Capsule found! Run 'ops/orchestration/sovereign_deployer.py' first."
    exit 1
fi

CAPSULE_NAME=$(basename "$LATEST_CAPSULE")
log_ok "Selected Capsule: $CAPSULE_NAME"

# ==============================================================================
# PHASE 2: ESTABLISH SECURE LINK (SSH Handshake)
# ==============================================================================
log_info "Phase 2: Pinging Failover Node ($FAILOVER_HOST)..."

# التحقق من مفتاح SSH
if [ ! -f "$SSH_KEY" ]; then
    log_err "Transport Key not found at $SSH_KEY."
    exit 1
fi

# تعديل صلاحيات المفتاح (للتأكد)
chmod 600 "$SSH_KEY"

# فحص الاتصال (Ping بسيط)
if ! ping -c 1 -W 2 "$FAILOVER_HOST" &> /dev/null; then
    log_warn "Failover host unreachable via ICMP. Trying SSH directly..."
fi

# ==============================================================================
# PHASE 3: TRANSMIT PAYLOAD (The Evacuation)
# ==============================================================================
log_info "Phase 3: Transmitting Capsule (SCP)..."

# نقل الملف
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -q \
    "$LATEST_CAPSULE" \
    "${FAILOVER_USER}@${FAILOVER_HOST}:/tmp/"

if [ $? -eq 0 ]; then
    log_ok "Payload delivered to /tmp/$CAPSULE_NAME"
else
    log_err "Transmission Failed! Check network or keys."
    exit 1
fi

# ==============================================================================
# PHASE 4: REMOTE ACTIVATION (The Resurrection)
# ==============================================================================
log_info "Phase 4: Remote Activation Sequence..."

# ننفذ سلسلة أوامر على الخادم البعيد:
# 1. إنشاء المجلد
# 2. فك الضغط
# 3. بناء الحاويات وتشغيلها
# 4. التحقق من الحالة

REMOTE_CMD="
    echo '[REMOTE] Preparing Directory...';
    sudo mkdir -p $REMOTE_DEST && sudo chown $FAILOVER_USER $REMOTE_DEST;
    
    echo '[REMOTE] Extracting Capsule...';
    tar -xzf /tmp/$CAPSULE_NAME -C $REMOTE_DEST;
    
    echo '[REMOTE] Loading Environment...';
    cd $REMOTE_DEST;
    
    # في حالة الطوارئ، قد نحتاج لتوليد .env جديد إذا لم يكن في الكبسولة
    # هنا نفترض وجوده أو نقله بشكل منفصل للأمان
    
    echo '[REMOTE] Igniting Systems (Docker)...';
    docker-compose up -d --build;
    
    echo '[REMOTE] Verifying Pulse...';
    sleep 5;
    if docker ps | grep -q alpha_brain; then
        echo 'SUCCESS: BRAIN IS ALIVE';
    else
        echo 'FAILURE: BRAIN DID NOT START';
        exit 1;
    fi
"

# تنفيذ الأوامر
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "${FAILOVER_USER}@${FAILOVER_HOST}" "$REMOTE_CMD"

if [ $? -eq 0 ]; then
    log_ok "FAILOVER SUCCESSFUL. SYSTEM IS RUNNING ON BACKUP NODE."
else
    log_err "Remote Activation Failed."
    exit 1
fi

# ==============================================================================
# PHASE 5: DNS SWITCHOVER (Simulated)
# ==============================================================================
log_info "Phase 5: Routing Traffic to New Node..."
# هنا عادة نستخدم API لخدمة مثل Cloudflare لتغيير الـ A Record
# curl -X PUT "https://api.cloudflare.com/..." -d '{"content": "'$FAILOVER_HOST'"}'

log_warn "MANUAL STEP: Update your DNS/Proxy to point to $FAILOVER_HOST immediately."
echo "---------------------------------------------------"
echo -e "${GREEN}EMERGENCY DEPLOYMENT COMPLETE${NC}"
echo "---------------------------------------------------"