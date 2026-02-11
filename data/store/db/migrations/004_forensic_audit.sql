-- ALPHA SOVEREIGN - FORENSIC AUDIT TRAIL (IMMUTABLE LEDGER)
-- =================================================================
-- Component Name: data/db/migrations/004_forensic_audit.sql
-- Core Responsibility: إنشاء سجلات التحقيق الجنائي غير القابلة للتلاعب أو المسح (Explainability Pillar).
-- Database Engine: PostgreSQL 14+ with Row-Level Security.
-- Forensic Impact: يطبق مبدأ "سلسلة الحراسة" (Chain of Custody) ويمنع إنكار التصرفات (Non-Repudiation).
-- =================================================================

-- 1. الجدول المركزي للدفتر الجنائي (Forensic Ledger)
-- -----------------------------------------------------------------
-- هذا الجدول يسجل كل "تغيير حالة" (State Change) في النظام.
-- يتميز بوجود "تجزئة" (Hash) تربط كل سجل بالسجل الذي قبله (مثل البلوكشين) لكشف أي تلاعب.
CREATE TABLE IF NOT EXISTS forensic_ledger (
    -- المعرف التسلسلي (BigSerial) لضمان الترتيب الصارم
    seq_id          BIGSERIAL   PRIMARY KEY,
    
    event_id        UUID        DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- الفاعل: من قام بالفعل؟ (بوت، إنسان، وظيفة مجدولة)
    actor_id        UUID        NOT NULL, -- يمكن ربطه بجدول الهويات
    actor_role      TEXT        NOT NULL,
    
    -- الفعل: ماذا حدث؟
    action_type     TEXT        NOT NULL, -- e.g., 'OVERRIDE_RISK', 'DEPLOY_STRATEGY'
    target_resource TEXT        NOT NULL, -- e.g., 'config/risk_limits.yaml'
    
    -- الأدلة: الحالة قبل وبعد (لإثبات التغيير)
    state_before    JSONB,      -- Snapshot of data before change
    state_after     JSONB,      -- Snapshot of data after change
    
    -- السياق: IP، الموقع الجغرافي، بصمة الجهاز
    context_meta    JSONB       NOT NULL,
    
    -- التشفير والنزاهة
    prev_hash       TEXT,       -- تجزئة السجل السابق (لإنشاء سلسلة مترابطة)
    curr_hash       TEXT        -- تجزئة السجل الحالي (يتم حسابها بالتطبيق)
);

-- تقسيم الجدول زمنياً لأنه سينمو بسرعة هائلة
SELECT create_hypertable('forensic_ledger', 'timestamp', if_not_exists => TRUE);


-- 2. ميكانيكية "منع التدمير" (Anti-Destruction Mechanism)
-- -----------------------------------------------------------------
-- إنشاء دالة تمنع التعديل أو الحذف نهائياً.
CREATE OR REPLACE FUNCTION prevent_ledger_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        RAISE EXCEPTION 'SECURITY ALERT: Illegal attempt to DELETE forensic evidence! User: %', current_user;
    ELSIF (TG_OP = 'UPDATE') THEN
        RAISE EXCEPTION 'SECURITY ALERT: Illegal attempt to MODIFY forensic evidence! User: %', current_user;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- تفعيل الزناد (Trigger) على الجدول
DROP TRIGGER IF EXISTS trg_protect_ledger ON forensic_ledger;
CREATE TRIGGER trg_protect_ledger
BEFORE DELETE OR UPDATE ON forensic_ledger
FOR EACH ROW EXECUTE FUNCTION prevent_ledger_tampering();


-- 3. جدول تقارير الحوادث (Incident Reports)
-- -----------------------------------------------------------------
-- لتجميع الأدلة عند اكتشاف اختراق أو شذوذ.
CREATE TABLE IF NOT EXISTS incident_case_files (
    case_id         TEXT        PRIMARY KEY, -- e.g., 'INC-2026-001'
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT        NOT NULL DEFAULT 'OPEN',
    
    risk_score      INT         NOT NULL,
    
    -- قائمة معرفات الأحداث المرتبطة بهذه القضية (Evidence Bag)
    linked_event_ids UUID[]     NOT NULL,
    
    automatic_analysis TEXT,    -- تحليل النظام الأولي
    human_notes        TEXT     -- ملاحظات المحقق البشري
);


-- 4. إعدادات الأمان الصارمة (Hardening)
-- -----------------------------------------------------------------
-- سحب صلاحية تفريغ الجدول (TRUNCATE) من الجميع حتى المالك
REVOKE TRUNCATE ON forensic_ledger FROM PUBLIC;
REVOKE TRUNCATE ON forensic_ledger FROM CURRENT_USER;

-- إنشاء فهرس للبحث عن تصرفات فاعل معين بسرعة
CREATE INDEX IF NOT EXISTS idx_forensic_actor ON forensic_ledger (actor_id, timestamp DESC);

-- =================================================================
-- END OF MIGRATION
-- =================================================================