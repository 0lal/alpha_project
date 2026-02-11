#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - AUTOMATED CERTIFICATE ROTATOR
# ==============================================================================
# Component: scripts/security/certificate_rotator.sh
# Responsibility: تدوير شهادات TLS ورموز المصادقة الداخلية (Zero Trust Maintenance).
# Pillar: Security (Forward Secrecy & Key Management)
# Author: Chief Security Officer
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[ROTATOR]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}    $1"; }

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SEC_DIR="./config/security"
TLS_DIR="$SEC_DIR/tls"
IPC_DIR="$SEC_DIR/ipc"
ARCHIVE_DIR="$SEC_DIR/archive/$(date +%Y%m%d_%H%M%S)"

# مدة صلاحية الشهادات (أيام) - قصيرة جداً للأمان العالي
CA_DAYS=365
CERT_DAYS=30 

mkdir -p "$TLS_DIR"
mkdir -p "$IPC_DIR"
mkdir -p "$ARCHIVE_DIR"

# ==============================================================================
# PHASE 1: BACKUP (Safety First)
# ==============================================================================
log_info "Phase 1: Backing up existing credentials..."

if [ "$(ls -A $TLS_DIR)" ]; then
    cp -r "$TLS_DIR/"* "$ARCHIVE_DIR/"
    log_ok "Old TLS certificates archived."
fi

if [ "$(ls -A $IPC_DIR)" ]; then
    cp -r "$IPC_DIR/"* "$ARCHIVE_DIR/"
    log_ok "Old IPC tokens archived."
fi

# ==============================================================================
# PHASE 2: INTERNAL CA MANAGEMENT (Sovereign Authority)
# ==============================================================================
log_info "Phase 2: Checking Certificate Authority (CA)..."

CA_KEY="$TLS_DIR/ca.key"
CA_CERT="$TLS_DIR/ca.crt"

# إذا لم يكن الـ CA موجوداً، ننشئه (يحدث مرة واحدة أو عند انتهاء الصلاحية)
if [ ! -f "$CA_KEY" ]; then
    log_warn "No Internal CA found. Establishing Sovereign Authority..."
    
    # استخدام Curve P-384 (أقوى وأسرع من RSA-4096)
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:secp384r1 \
        -keyout "$CA_KEY" -out "$CA_CERT" -days "$CA_DAYS" -nodes \
        -subj "/CN=Alpha Sovereign Root CA/O=Alpha Systems/C=XX" \
        -addext "basicConstraints=critical,CA:TRUE"
        
    log_ok "Root CA Established."
else
    log_info "Root CA is valid."
fi

# ==============================================================================
# PHASE 3: CERTIFICATE ROTATION (TLS)
# ==============================================================================
log_info "Phase 3: Rotating Service Certificates..."

generate_cert() {
    local name=$1
    local cn=$2
    
    local key="$TLS_DIR/$name.key"
    local csr="$TLS_DIR/$name.csr"
    local crt="$TLS_DIR/$name.crt"
    
    # 1. توليد مفتاح خاص وطلب توقيع (CSR)
    openssl req -newkey ec -pkeyopt ec_paramgen_curve:secp384r1 \
        -keyout "$key" -out "$csr" -nodes \
        -subj "/CN=$cn/O=Alpha Node"

    # 2. توقيع الطلب بواسطة الـ CA الخاص بنا
    openssl x509 -req -in "$csr" -CA "$CA_CERT" -CAkey "$CA_KEY" -CAcreateserial \
        -out "$crt" -days "$CERT_DAYS" -sha256
        
    # تنظيف
    rm "$csr"
    chmod 600 "$key"
    log_ok "Rotated Certificate for: $name"
}

# تدوير شهادة العقل (Brain - Python)
generate_cert "brain" "alpha-brain.internal"

# تدوير شهادة المحرك (Engine - Rust)
generate_cert "engine" "alpha-engine.internal"

# تدوير شهادة قاعدة البيانات
generate_cert "database" "alpha-db.internal"

# ==============================================================================
# PHASE 4: IPC TOKEN ROTATION (ZeroMQ & APIs)
# ==============================================================================
log_info "Phase 4: Rotating IPC Secrets..."

# 1. ZMQ Shared Secret (CurveZMQ Key or Shared Password)
# هنا نولد مفتاح عشوائي 64 بايت (Hex)
openssl rand -hex 64 > "$IPC_DIR/zmq_shared_secret.key"
chmod 600 "$IPC_DIR/zmq_shared_secret.key"
log_ok "ZMQ Shared Secret Rotated."

# 2. Internal API Token (JWT Secret)
openssl rand -base64 48 > "$IPC_DIR/jwt_signing_key.secret"
chmod 600 "$IPC_DIR/jwt_signing_key.secret"
log_ok "JWT Signing Key Rotated."

# ==============================================================================
# PHASE 5: SIGNALING & CLEANUP
# ==============================================================================
# حماية المجلدات
chmod 700 "$TLS_DIR"
chmod 700 "$IPC_DIR"

echo "---------------------------------------------------"
echo -e "${GREEN}ROTATION COMPLETE${NC}"
echo "---------------------------------------------------"
echo "New artifacts located in: $SEC_DIR"
echo -e "${YELLOW}IMPORTANT: Services (Brain, Engine) must be restarted to load new keys.${NC}"
echo "You can trigger a rolling restart via 'ops/orchestration/health_recovery_node.py'"
echo "---------------------------------------------------"