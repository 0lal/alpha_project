#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - ENVIRONMENT CONFIGURATION GENERATOR
# ==============================================================================
# Component: scripts/setup/env_generator.sh
# Responsibility: توليد ملفات التكوين الحساسة (.env) بناءً على بصمة العتاد.
# Pillar: Stability (Adaptive Configuration)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_gen() { echo -e "${GREEN}[GENERATED]${NC} $1"; }

# ==============================================================================
# PHASE 1: HARDWARE FINGERPRINTING (تشخيص العتاد)
# ==============================================================================
log_info "Analyzing Hardware to determine optimal configuration..."

# كشف عدد الأنوية
CPU_CORES=$(nproc)
# كشف حجم الرامات (GB)
TOTAL_RAM_GB=$(grep MemTotal /proc/meminfo | awk '{print $2}' | awk '{print int($1/1024/1024)}')

log_info "Detected: ${CPU_CORES} CPU Cores | ${TOTAL_RAM_GB} GB RAM"

# تحديد ملف التعريف (Profile)
if [ "$TOTAL_RAM_GB" -ge 32 ]; then
    PROFILE="TITAN"
    DB_WORK_MEM="64MB"
    BATCH_SIZE="64"
    LLM_LAYERS="35" # تشغيل الموديل كاملاً على GPU
elif [ "$TOTAL_RAM_GB" -ge 16 ]; then
    PROFILE="STANDARD"
    DB_WORK_MEM="16MB"
    BATCH_SIZE="32"
    LLM_LAYERS="20" # توزيع الحمل
else
    PROFILE="LITE"
    DB_WORK_MEM="4MB"
    BATCH_SIZE="8"
    LLM_LAYERS="0"  # الاعتماد على CPU فقط
fi

log_info "Selected Profile: [${YELLOW}${PROFILE}${NC}]"

# ==============================================================================
# PHASE 2: SECRET GENERATION (توليد المفاتيح)
# ==============================================================================
log_info "Generating Cryptographic Secrets..."

# توليد مفاتيح عشوائية قوية باستخدام OpenSSL
JWT_SECRET=$(openssl rand -hex 32)
PG_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | cut -c 1-20)
REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | cut -c 1-20)
SYSTEM_SALT=$(openssl rand -hex 16)

# ==============================================================================
# PHASE 3: WRITE .ENV FILE
# ==============================================================================
ENV_FILE=".env"
BACKUP_FILE=".env.bak.$(date +%s)"

if [ -f "$ENV_FILE" ]; then
    log_info "Existing .env found. Backing up to ${BACKUP_FILE}..."
    mv "$ENV_FILE" "$BACKUP_FILE"
fi

cat <<EOF > "$ENV_FILE"
# ALPHA SOVEREIGN - GENERATED CONFIGURATION
# Generated on: $(date)
# Hardware Profile: ${PROFILE}
# ======================================================

# --- 1. SYSTEM IDENTITY ---
ALPHA_ENV=production
ALPHA_NODE_ID=$(uuidgen)
ALPHA_PROFILE=${PROFILE}
LOG_LEVEL=INFO
SYSTEM_SALT=${SYSTEM_SALT}

# --- 2. SECURITY SECRETS (DO NOT SHARE) ---
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY_PATH=config/security/master.key

# --- 3. DATABASE CONFIGURATION (Auto-Tuned) ---
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alpha_sovereign
POSTGRES_USER=alpha_admin
POSTGRES_PASSWORD=${PG_PASSWORD}
# Optimized for ${TOTAL_RAM_GB}GB RAM
PG_WORK_MEM=${DB_WORK_MEM}
PG_MAX_CONNECTIONS=100

# --- 4. REDIS CONFIGURATION ---
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}

# --- 5. BRAIN & AI ENGINE ---
# DeepSeek Model Path (Update this path)
MODEL_PATH=./data/models/deepseek-coder-v2.gguf
# Layers offloaded to GPU based on RAM
MODEL_GPU_LAYERS=${LLM_LAYERS}
MODEL_CTX_SIZE=4096
INFERENCE_BATCH_SIZE=${BATCH_SIZE}

# --- 6. EXTERNAL APIs (PLACEHOLDERS) ---
# Fill these manually
OPENROUTER_API_KEY=
BINANCE_API_KEY=
BINANCE_SECRET_KEY=

# --- 7. NETWORK PORTS ---
PORT_ZMQ_PUB=5555
PORT_ZMQ_REP=5556
PORT_UI_HTTP=8080
EOF

# ==============================================================================
# PHASE 4: PERMISSIONS & CLEANUP
# ==============================================================================

# تأمين الملف (قراءة/كتابة للمالك فقط)
chmod 600 "$ENV_FILE"

log_gen ".env file created successfully."
log_info "Security: File permissions set to 600 (Owner Read/Write only)."
echo -e "${YELLOW}IMPORTANT: Update the 'EXTERNAL APIs' section in .env manually.${NC}"