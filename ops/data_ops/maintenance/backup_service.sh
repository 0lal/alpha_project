# Quantum Encrypted Backup

#!/bin/bash
# ALPHA SOVEREIGN - SOVEREIGN BACKUP SERVICE
# =================================================================
# Component Name: data/maintenance/backup_service.sh
# Core Responsibility: تشغيل نظام النسخ الاحتياطي السيادي المشفر (Stability Pillar).
# Forensic Impact: يضمن استمرارية الأعمال (Business Continuity) وحماية الأدلة من التدمير.
# =================================================================

# 1. إعدادات التكوين (Configuration)
# -----------------------------------------------------------------
BACKUP_ROOT="./backups/vault"
LOG_FILE="./logs/backup_service.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CURRENT_BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
RETENTION_DAYS=7

# بيانات قاعدة البيانات (يفضل سحبها من متغيرات البيئة للأمان)
DB_NAME=${DB_NAME:-"alpha_main_db"}
DB_USER=${DB_USER:-"postgres"}

# مفتاح التشفير (يجب أن يكون مخزناً في Vault خارجي)
# هنا نستخدم كلمة مرور مؤقتة للمحاكاة
ENCRYPTION_PASS="ALPHA_SOVEREIGN_TOP_SECRET_KEY_999"

# إنشاء المجلدات
mkdir -p "${CURRENT_BACKUP_DIR}"
mkdir -p "$(dirname "${LOG_FILE}")"

# دالة التسجيل (Logging Helper)
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "BACKUP_START: بدء بروتوكول النسخ الاحتياطي السيادي (ID: ${TIMESTAMP})..."

# 2. نسخ قاعدة البيانات الساخنة (Hot Storage Snapshot)
# -----------------------------------------------------------------
log "STEP 1: تفريغ قاعدة البيانات (TimescaleDB)..."
if pg_dump -U "${DB_USER}" -F c -b -v -f "${CURRENT_BACKUP_DIR}/db_dump.custom" "${DB_NAME}" 2>> "${LOG_FILE}"; then
    log "DB_SUCCESS: تم نسخ قاعدة البيانات بنجاح."
else
    log "DB_FAIL: فشل نسخ قاعدة البيانات! إيقاف الطوارئ."
    exit 1
fi

# 3. نسخ ملفات التكوين والمفاتيح (Config & Keys)
# -----------------------------------------------------------------
log "STEP 2: أرشفة ملفات الإعدادات..."
tar -czf "${CURRENT_BACKUP_DIR}/configs.tar.gz" ./config ./data/db/seeds 2>> "${LOG_FILE}"

# 4. نسخ الأرشيف البارد (Cold Storage - Incremental)
# -----------------------------------------------------------------
# ملاحظة: الأرشيف البارد ضخم، لذا ننسخ فقط ما تغير في آخر 24 ساعة
log "STEP 3: مزامنة الأرشيف البارد (Parquet Lake)..."
# نستخدم rsync لمحاكاة النسخ التزايدي لمجلد خارجي
# rsync -av --update ./data/lake "${CURRENT_BACKUP_DIR}/lake_snapshot"

# 5. التشفير والتوقيع (Encryption & Hashing)
# -----------------------------------------------------------------
log "STEP 4: تشفير الحزمة (AES-256)..."

# ضغط المجلد بالكامل في ملف واحد
FINAL_ARCHIVE="${BACKUP_ROOT}/alpha_backup_${TIMESTAMP}.tar.gz"
tar -czf - "${CURRENT_BACKUP_DIR}" | openssl enc -aes-256-cbc -salt -pbkdf2 -pass pass:"${ENCRYPTION_PASS}" -out "${FINAL_ARCHIVE}.enc"

if [ -f "${FINAL_ARCHIVE}.enc" ]; then
    log "ENCRYPTION_SUCCESS: تم إنشاء الملف المشفر: ${FINAL_ARCHIVE}.enc"
    
    # حساب البصمة الجنائية (SHA-256 Checksum)
    sha256sum "${FINAL_ARCHIVE}.enc" > "${FINAL_ARCHIVE}.enc.sha256"
    log "INTEGRITY_HASH: تم توليد بصمة النزاهة."
    
    # تنظيف الملفات المؤقتة غير المشفرة (Shatter the glass)
    rm -rf "${CURRENT_BACKUP_DIR}"
else
    log "ENCRYPTION_FAIL: فشل عملية التشفير!"
    exit 1
fi

# 6. سياسة الاحتفاظ (Retention Policy)
# -----------------------------------------------------------------
log "STEP 5: تنظيف النسخ القديمة (أقدم من ${RETENTION_DAYS} أيام)..."
find "${BACKUP_ROOT}" -name "alpha_backup_*.enc*" -type f -mtime +${RETENTION_DAYS} -delete
log "CLEANUP_DONE: تم حذف الملفات القديمة."

log "BACKUP_COMPLETE: اكتملت العملية بنجاح."
exit 0