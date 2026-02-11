-- ALPHA SOVEREIGN - IDENTITY VAULT MIGRATION
-- =================================================================
-- Component Name: data/db/migrations/002_identity_vault.sql
-- Core Responsibility: إنشاء سجل الهويات السيادية ومفاتيح التشفير الكمي (Security Pillar).
-- Database Engine: PostgreSQL 14+ with pgcrypto.
-- Forensic Impact: يضمن أن كل فاعل في النظام (إنسان أو بوت) معروف، وأن المفاتيح مخزنة بطبقات تشفير متعددة.
-- =================================================================

-- 1. جدول الهويات السيادية (Sovereign Identities)
-- -----------------------------------------------------------------
-- هذا الجدول لا يخزن "مستخدمين" عاديين، بل "كيانات" (Entities).
-- الكيان قد يكون المشغل البشري (أنت)، أو النظام نفسه (Alpha Core)، أو استراتيجية فرعية.
CREATE TABLE IF NOT EXISTS sovereign_identities (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- الاسم الرمزي للكيان (مثل: 'OVERLORD', 'ALPHA_PRIME')
    codename        TEXT        NOT NULL UNIQUE,
    
    -- نوع الكيان: هل هو بشر أم ذكاء اصطناعي؟
    entity_type     TEXT        NOT NULL CHECK (entity_type IN ('HUMAN_OPERATOR', 'AI_AGENT', 'SYSTEM_DAEMON')),
    
    -- مستوى التصريح الأمن (0 = مراقب، 5 = تحكم كامل)
    clearance_level INT         NOT NULL DEFAULT 0,
    
    -- الحالة الحالية (نشط، مجمد، محظور جنائياً)
    status          TEXT        NOT NULL DEFAULT 'ACTIVE' 
                                CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REVOKED', 'BANNED')),
                                
    -- بصمة الجهاز الموثوق (Hardware Fingerprint Hash) لربط الهوية بالجهاز الفيزيائي
    trusted_device_hash TEXT,
    
    -- آخر ظهور (للتتبع الجنائي)
    last_seen_at    TIMESTAMPTZ
);

-- فهرس للبحث السريع عن الكيانات النشطة
CREATE INDEX IF NOT EXISTS idx_identities_codename ON sovereign_identities (codename) WHERE status = 'ACTIVE';


-- 2. مخزن المفاتيح الكمومية (Quantum Key Store)
-- -----------------------------------------------------------------
-- تحذير: هذا الجدول هو أخطر مكان في قاعدة البيانات.
-- لا يتم تخزين المفاتيح كنص واضح أبداً. يتم تشفيرها باستخدام مفتاح رئيسي (Master Key) خارج قاعدة البيانات.
CREATE TABLE IF NOT EXISTS quantum_key_store (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    owner_id        UUID        NOT NULL REFERENCES sovereign_identities(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- خوارزمية التشفير المستخدمة (مثل: 'Kyber-1024', 'Dilithium-3')
    algo_type       TEXT        NOT NULL,
    
    -- المفتاح العام (يمكن نشره)
    public_key      TEXT        NOT NULL,
    
    -- المفتاح الخاص المشفر (Encrypted Private Key Blob)
    -- يتم فك تشفيره فقط داخل الذاكرة العشوائية (RAM) عند الحاجة الملحة
    encrypted_priv_key BYTEA    NOT NULL,
    
    -- تاريخ انتهاء صلاحية المفتاح (Rotation Policy)
    expires_at      TIMESTAMPTZ NOT NULL,
    
    -- حالة المفتاح (لإبطال المفاتيح المخترقة)
    is_revoked      BOOLEAN     DEFAULT FALSE,
    revocation_reason TEXT
);

-- فهرس لضمان عدم وجود مفاتيح نشطة لنفس الخوارزمية لنفس المستخدم (فرض التدوير)
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_keys 
ON quantum_key_store (owner_id, algo_type) 
WHERE is_revoked = FALSE AND expires_at > NOW();


-- 3. سجل جلسات الوصول (Access Sessions)
-- -----------------------------------------------------------------
-- كل مرة يقوم فيها كيان بتسجيل الدخول، يتم فتح "جلسة".
-- هذا الجدول يحل محل الـ JWT التقليدي ليكون قابلاً للمراجعة الجنائية.
CREATE TABLE IF NOT EXISTS access_sessions (
    session_id      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    identity_id     UUID        NOT NULL REFERENCES sovereign_identities(id),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ, -- إذا تم طرد المستخدم يدوياً
    
    -- عنوان IP (للمطابقة مع الموقع الجغرافي المسموح)
    ip_address      INET        NOT NULL,
    
    -- توقيع الجهاز (User Agent / Device ID)
    user_agent      TEXT,
    
    -- رمز التحقق من النزاهة (Session Integrity Token)
    integrity_token TEXT        NOT NULL
);

-- تنظيف الجلسات القديمة تلقائياً يتطلب Job خارجي، لكننا نفهرس البحث عنها
CREATE INDEX IF NOT EXISTS idx_sessions_active 
ON access_sessions (identity_id) 
WHERE revoked_at IS NULL AND expires_at > NOW();

-- =================================================================
-- END OF MIGRATION
-- =================================================================