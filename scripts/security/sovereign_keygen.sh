#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - CRYPTOGRAPHIC KEY GENERATION
# ==============================================================================
# Component: scripts/security/sovereign_keygen.sh
# Responsibility: توليد مفاتيح التشفير والهوية (PGP, SSH, Quantum Seed).
# Pillar: Security (Sovereign Identity & Encryption)
# Author: Chief Security Officer
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[SEC-INIT]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[SEC-OK]${NC}   $1"; }
log_warn() { echo -e "${YELLOW}[SEC-WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[SEC-ERR]${NC}  $1"; }

# التأكد من وجود أدوات التشفير
if ! command -v gpg &> /dev/null || ! command -v ssh-keygen &> /dev/null; then
    log_err "Required tools (gpg, ssh-keygen) are missing!"
    exit 1
fi

# ==============================================================================
# PHASE 1: SECURE VAULT CREATION
# ==============================================================================
log_info "Initializing Quantum Vault Directories..."

VAULT_DIR="./config/security"
IDENTITY_DIR="$VAULT_DIR/identity"
TRANSPORT_DIR="$VAULT_DIR/transport"
QUANTUM_DIR="$VAULT_DIR/quantum"

mkdir -p "$IDENTITY_DIR"
mkdir -p "$TRANSPORT_DIR"
mkdir -p "$QUANTUM_DIR"

# تطبيق صلاحيات صارمة فوراً (للمالك فقط)
chmod 700 "$VAULT_DIR"
chmod 700 "$IDENTITY_DIR"
chmod 700 "$TRANSPORT_DIR"
chmod 700 "$QUANTUM_DIR"

log_ok "Vault structure created with Mode 700."

# ==============================================================================
# PHASE 2: SSH TRANSPORT KEYS (Ed25519)
# ==============================================================================
log_info "Generating Sovereign Transport Keys (SSH - Ed25519)..."

SSH_KEY_PATH="$TRANSPORT_DIR/alpha_transport_id"

if [ -f "$SSH_KEY_PATH" ]; then
    log_warn "SSH Keys already exist. Skipping generation to preserve identity."
else
    # استخدام Ed25519 لأنه أسرع وأكثر أماناً من RSA
    # -N "" يعني بدون كلمة مرور (لأن النظام يعمل آلياً)، الأمان يعتمد على حماية الملف
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -C "alpha_sovereign_node_$(date +%s)" -N "" -q
    log_ok "Ed25519 Transport Keys Generated."
fi

# ==============================================================================
# PHASE 3: PGP IDENTITY KEYS (The Code Signer)
# ==============================================================================
log_info "Generating System Identity (PGP)..."

PGP_KEY_PATH="$IDENTITY_DIR"
GPG_CONF="$IDENTITY_DIR/gpg_batch.conf"

# التحقق مما إذا كان لدينا مفتاح بالفعل
EXISTING_KEYS=$(gpg --homedir "$IDENTITY_DIR" --list-keys 2>/dev/null)

if [[ -z "$EXISTING_KEYS" ]]; then
    # إنشاء ملف تكوين دفعي (Batch Config) لـ GPG
    cat > "$GPG_CONF" <<EOF
Key-Type: EDDSA
Key-Curve: ed25519
Key-Usage: sign
Subkey-Type: ECDH
Subkey-Curve: cv25519
Subkey-Usage: encrypt
Name-Real: Alpha Sovereign Core
Name-Email: system@alpha.sovereign
Expire-Date: 0
%no-protection
%commit
EOF

    # توليد المفتاح
    gpg --homedir "$IDENTITY_DIR" --batch --generate-key "$GPG_CONF" 2>/dev/null
    
    # تصدير المفتاح العام
    gpg --homedir "$IDENTITY_DIR" --export --armor "Alpha Sovereign Core" > "$IDENTITY_DIR/public.asc"
    
    # تنظيف
    rm "$GPG_CONF"
    log_ok "PGP Identity Generated (Alpha Sovereign Core)."
else
    log_warn "PGP Identity already exists."
fi

# ==============================================================================
# PHASE 4: QUANTUM ENTROPY SEED (For Kyber)
# ==============================================================================
log_info "Generating High-Entropy Quantum Seed..."

SEED_FILE="$QUANTUM_DIR/master_seed.hex"

if [ -f "$SEED_FILE" ]; then
    log_warn "Quantum Seed exists. PRESERVING ORIGINAL SEED."
else
    # توليد 64 بايت (512 بت) من العشوائية المشفرة
    # سيتم استخدام هذا الملف بواسطة Python Brain لتوليد مفاتيح Kyber-1024
    openssl rand -hex 64 > "$SEED_FILE"
    
    # حماية قصوى: قراءة فقط للمالك
    chmod 400 "$SEED_FILE"
    log_ok "512-bit Quantum Entropy Seed Generated."
fi

# ==============================================================================
# PHASE 5: FINAL REPORT
# ==============================================================================
echo "---------------------------------------------------"
echo -e "${GREEN}SOVEREIGN KEYGEN COMPLETE${NC}"
echo "---------------------------------------------------"
echo "Transport Key: $SSH_KEY_PATH"
echo "Identity Key:  $IDENTITY_DIR/public.asc"
echo "Quantum Seed:  $SEED_FILE"
echo "---------------------------------------------------"
log_warn "KEEP THE 'config/security' DIRECTORY SAFE. IT IS THE SYSTEM'S SOUL."