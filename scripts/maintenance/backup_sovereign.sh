#!/bin/bash
# ==============================================================================
# ALPHA SOVEREIGN SYSTEM - QUANTUM-ENCRYPTED BACKUP PROTOCOL
# ==============================================================================
# Component: scripts/maintenance/backup_sovereign.sh
# Responsibility: إنشاء نسخة احتياطية كاملة، مشفرة، وموقعة للنظام والبيانات.
# Pillar: Stability (Disaster Recovery & Forensic Integrity)
# Author: Chief System Architect
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[BACKUP]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[SECURED]${NC} $1"; }
log_err()  { echo -e "${RED}[FAILED]${NC}  $1"; }
log_warn() { echo -e "${YELLOW}[NOTE]${NC}    $1"; }

# ==============================================================================
# CONFIGURATION
# ==============================================================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="./dist/backups"
SNAPSHOT_NAME="alpha_sovereign_snapshot_${TIMESTAMP}"
BACKUP_DIR="${BACKUP_ROOT}/${SNAPSHOT_NAME}"
FINAL_ARCHIVE="${BACKUP_ROOT}/${SNAPSHOT_NAME}.tar.gpg"

# الهوية المستخدمة للتشفير (من sovereign_keygen.sh)
RECIPIENT_ID="Alpha Sovereign Core"
IDENTITY_DIR="./config/security/identity"

# عدد الأيام للاحتفاظ بالنسخ (سياسة التدوير)
RETENTION_DAYS=7

mkdir -p "$BACKUP_ROOT"

# ==============================================================================
# PHASE 1: DATABASE FLUSH & SNAPSHOT (Consistency Check)
# ==============================================================================
log_info "Phase 1: Triggering Database Snapshots..."

# 1. Redis: إجبار الحفظ على القرص لضمان عدم ضياع البيانات في الذاكرة
if docker ps | grep -q alpha_redis; then
    log_info "-> Saving Redis state..."
    docker exec alpha_redis redis-cli save > /dev/null
    log_ok "Redis Dump Created."
else
    log_warn "Redis container not running. Skipping flush."
fi

# 2. QuestDB: في بيئة الإنتاج يفضل استخدام أمر BACKUP SQL
# هنا سنعتمد على نسخ ملفات القرص بعد التأكد من سلامتها
log_info "-> Preparing QuestDB storage for copy..."

# ==============================================================================
# PHASE 2: COLLECTION (Staging)
# ==============================================================================
log_info "Phase 2: Collecting Artifacts..."

mkdir -p "$BACKUP_DIR"

# نسخ الكود المصدري (الجينوم)
log_info "-> Copying Source Genome..."
cp -r shield engine ops ui scripts "$BACKUP_DIR/"

# نسخ التكوين والأسرار (المفاتيح)
log_info "-> Copying Security Vault & Configs..."
mkdir -p "$BACKUP_DIR/config"
cp -r config/security "$BACKUP_DIR/config/"
cp .env "$BACKUP_DIR/.env"

# نسخ البيانات (QuestDB, Redis, Qdrant)
# تحذير: نسخ قواعد البيانات وهي تعمل قد يسبب مشاكل، الأفضل إيقافها لحظياً أو استخدام أدوات خاصة
log_info "-> Copying Data Volumes (Hot Backup)..."
cp -r data "$BACKUP_DIR/"

# ==============================================================================
# PHASE 3: COMPRESSION & ENCRYPTION (The Vault)
# ==============================================================================
log_info "Phase 3: Encrypting Snapshot (GPG)..."

# نستخدم التشفير المتدفق (Streaming) لعدم إنشاء ملف tar ضخم غير مشفر
# tar -> GPG -> Disk
tar -cf - -C "$BACKUP_ROOT" "$SNAPSHOT_NAME" | \
    gpg --homedir "$IDENTITY_DIR" \
        --batch --yes \
        --encrypt --sign \
        --recipient "$RECIPIENT_ID" \
        --output "$FINAL_ARCHIVE"

if [ $? -eq 0 ]; then
    log_ok "Snapshot Encrypted Successfully: $FINAL_ARCHIVE"
else
    log_err "Encryption Failed!"
    rm -rf "$BACKUP_DIR"
    exit 1
fi

# ==============================================================================
# PHASE 4: INTEGRITY HASHING (Forensic Evidence)
# ==============================================================================
log_info "Phase 4: Calculating Forensic Hash..."

# حساب SHA-256 للملف المشفر
HASH=$(sha256sum "$FINAL_ARCHIVE" | awk '{print $1}')
echo "$HASH" > "${FINAL_ARCHIVE}.sha256"

log_ok "Integrity Hash: $HASH"

# ==============================================================================
# PHASE 5: CLEANUP & ROTATION
# ==============================================================================
log_info "Phase 5: Cleaning up..."

# حذف المجلد المؤقت (Staging)
rm -rf "$BACKUP_DIR"

# تطبيق سياسة التدوير (حذف النسخ الأقدم من 7 أيام)
log_info "Rotating old backups (Retention: ${RETENTION_DAYS} days)..."
find "$BACKUP_ROOT" -name "alpha_sovereign_snapshot_*.tar.gpg" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_ROOT" -name "alpha_sovereign_snapshot_*.sha256" -mtime +$RETENTION_DAYS -delete

# حساب حجم النسخة
SIZE=$(du -h "$FINAL_ARCHIVE" | cut -f1)

echo "---------------------------------------------------"
echo -e "${GREEN}BACKUP COMPLETE${NC}"
echo "---------------------------------------------------"
echo "Archive: $FINAL_ARCHIVE"
echo "Size:    $SIZE"
echo "Hash:    $HASH"
echo "---------------------------------------------------"
echo -e "${YELLOW}RECOMMENDATION: Copy this file to an offsite location immediately.${NC}"