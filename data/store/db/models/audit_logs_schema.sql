-- Immutable Forensic Logs

-- ALPHA SOVEREIGN - OPERATIONAL AUDIT LOGS SCHEMA
-- =================================================================
-- Component Name: data/db/models/audit_logs_schema.sql
-- Core Responsibility: تحديد هيكلية سجلات التدقيق التشغيلية ومراقبة الوصول (Explainability Pillar).
-- Database Engine: PostgreSQL 14+ with TimescaleDB & Partitioning.
-- Forensic Impact: يوفر رؤية كاملة لمن دخل للنظام، ماذا طلب، وهل نجح أم فشل (Access & Error Logs).
-- =================================================================

-- 1. سجل طلبات الوصول (API Access Logs)
-- -----------------------------------------------------------------
-- يسجل كل طلب HTTP يرد إلى النظام.
-- هذا الجدول ضخم جداً (High Volume)، لذا يجب تصميمه للكتابة السريعة.
CREATE TABLE IF NOT EXISTS api_access_logs (
    request_id      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- هوية الطالب
    client_ip       INET        NOT NULL,
    user_agent      TEXT,
    api_key_id      TEXT,       -- إذا كان الطلب موثقاً
    
    -- تفاصيل الطلب
    method          TEXT        NOT NULL, -- GET, POST, DELETE
    endpoint        TEXT        NOT NULL, -- /api/v1/orders
    params          JSONB,      -- Parameters (Sanitized)
    
    -- تفاصيل الاستجابة
    status_code     INT         NOT NULL,
    latency_ms      DOUBLE PRECISION, -- زمن الاستجابة
    
    -- العلامات الأمنية
    is_suspicious   BOOLEAN     DEFAULT FALSE, -- هل تم تعليمه كطلب مشبوه بواسطة WAF؟
    geo_location    TEXT        -- الدولة/المدينة (يتم ملؤه لاحقاً)
);

-- تحويله لجدول زمني (حذف البيانات القديمة تلقائياً بعد 30 يوم لتوفير المساحة)
SELECT create_hypertable('api_access_logs', 'timestamp', if_not_exists => TRUE);
SELECT add_retention_policy('api_access_logs', INTERVAL '30 days');


-- 2. سجل أخطاء التطبيق (Application Error Logs)
-- -----------------------------------------------------------------
-- يختلف عن System Audit بأنه يحتوي على التفاصيل التقنية الكاملة (Traceback).
-- يستخدمه المطورون لتصحيح الأخطاء (Debugging).
CREATE TABLE IF NOT EXISTS app_error_logs (
    error_id        UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    service_name    TEXT        NOT NULL, -- e.g., 'ingestion_service', 'strategy_engine'
    error_type      TEXT        NOT NULL, -- e.g., 'ValueError', 'ConnectionTimeout'
    error_message   TEXT        NOT NULL,
    
    -- تتبع المكدس (Stack Trace) - يخزن كنص
    stack_trace     TEXT,
    
    -- حالة المعالجة (هل تم إصلاح الخطأ؟)
    resolution_status TEXT      DEFAULT 'OPEN' CHECK (resolution_status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'IGNORED'))
);

SELECT create_hypertable('app_error_logs', 'timestamp', if_not_exists => TRUE);


-- 3. سجل نشاط المستخدمين (User Activity Logs)
-- -----------------------------------------------------------------
-- يسجل تفاعلات المستخدم مع الواجهة (UI Clicks, Page Views).
-- مهم لتحليل سلوك المشغل (Behavioral Analytics).
CREATE TABLE IF NOT EXISTS user_activity_logs (
    activity_id     UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    user_id         UUID        NOT NULL, -- يمكن ربطه بجدول sovereign_identities
    session_id      UUID,
    
    action_category TEXT        NOT NULL, -- e.g., 'NAVIGATION', 'BUTTON_CLICK', 'FORM_SUBMIT'
    element_id      TEXT,                 -- العنصر الذي تم التفاعل معه
    description     TEXT,
    
    -- السياق (Metadata)
    screen_resolution TEXT,
    device_type       TEXT
);

SELECT create_hypertable('user_activity_logs', 'timestamp', if_not_exists => TRUE);


-- 4. وجهات النظر الأمنية (Security Views)
-- -----------------------------------------------------------------

-- عرض لكشف هجمات التخمين (Brute Force)
-- يجمع عدد المحاولات الفاشلة (401/403) لكل IP في آخر ساعة
CREATE OR REPLACE VIEW view_suspicious_ips AS
SELECT
    client_ip,
    COUNT(*) as failed_attempts,
    MAX(timestamp) as last_attempt,
    array_agg(distinct endpoint) as targeted_endpoints
FROM api_access_logs
WHERE status_code IN (401, 403) 
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY client_ip
HAVING COUNT(*) > 10; -- أكثر من 10 محاولات فاشلة يعتبر مشبوهاً


-- عرض لكشف بطء النظام (Performance Bottlenecks)
-- يظهر نقاط النهاية (Endpoints) التي تستغرق وقتاً طويلاً
CREATE OR REPLACE VIEW view_slow_endpoints AS
SELECT
    endpoint,
    AVG(latency_ms) as avg_latency,
    MAX(latency_ms) as max_latency,
    COUNT(*) as request_count
FROM api_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY endpoint
HAVING AVG(latency_ms) > 500; -- أي شيء أبطأ من 500ms يحتاج تحسين

-- =================================================================
-- END OF SCHEMA
-- =================================================================