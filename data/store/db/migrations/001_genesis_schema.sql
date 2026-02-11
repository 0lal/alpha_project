-- ALPHA SOVEREIGN - GENESIS SCHEMA MIGRATION
-- =================================================================
-- Component Name: data/db/migrations/001_genesis_schema.sql
-- Core Responsibility: تحديد المخطط الجيني: جداول النواة والحالة الحيوية للمنظومة (Governance Pillar).
-- Database Engine: PostgreSQL 14+ with TimescaleDB Extension.
-- Forensic Impact: هيكلة البيانات بطريقة تضمن سلامة التسلسل الزمني وتمنع تضارب البيانات.
-- =================================================================

-- 1. تفعيل الامتدادات الضرورية (Extensions)
-- -----------------------------------------------------------------
-- TimescaleDB: لتحويل الجداول العادية إلى جداول فائقة السرعة للسلاسل الزمنية.
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- pgcrypto: لتوليد معرفات UUID العشوائية والمشفرة (أفضل جنائياً من الأرقام المتسلسلة).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. جدول نبضات السوق (Market Ticks - Hypertable)
-- -----------------------------------------------------------------
-- هذا الجدول سيخزن ملايين الصفوف يومياً.
-- ملاحظة هندسية: نستخدم DOUBLE PRECISION للسعر للحفاظ على الدقة العلمية.
CREATE TABLE IF NOT EXISTS market_ticks (
    time            TIMESTAMPTZ NOT NULL, -- الوقت بصيغة UTC بدقة ميكروثانية
    symbol          TEXT        NOT NULL, -- رمز العملة (مثلاً BTCUSDT)
    price           DOUBLE PRECISION  NOT NULL,
    quantity        DOUBLE PRECISION  NOT NULL,
    source          TEXT        NOT NULL, -- مصدر البيانات (Binance, Kraken...)
    is_anomalous    BOOLEAN     DEFAULT FALSE, -- علامة جنائية: هل السعر مشبوه؟
    
    -- مفتاح مركب لضمان عدم تكرار نفس النبضة من نفس المصدر في نفس اللحظة
    UNIQUE (time, symbol, source)
);

-- تحويل الجدول إلى Hypertable (تقسيم البيانات زمنياً لأداء خارق)
-- يتم تقسيم البيانات إلى قطع (Chunks) كل قطعة تحتوي على بيانات يوم واحد.
SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);

-- إضافة فهرس (Index) للبحث السريع عن العملات
CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol ON market_ticks (symbol, time DESC);


-- 3. جدول السجل الجنائي للنظام (System Audit Log)
-- -----------------------------------------------------------------
-- لا يتم حذف أي شيء من هنا أبداً. هذا هو الصندوق الأسود.
CREATE TABLE IF NOT EXISTS system_audit_log (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    component       TEXT        NOT NULL, -- اسم الملف أو الوحدة التي سجلت الحدث
    severity        TEXT        NOT NULL, -- INFO, WARNING, CRITICAL, FATAL
    message         TEXT        NOT NULL, -- نص الرسالة
    metadata        JSONB,                -- بيانات إضافية (مثل Snapshot من الذاكرة)
    
    -- حقل لضمان عدم التلاعب (Checksum) - سيتم ملؤه لاحقاً بواسطة التطبيق
    integrity_hash  TEXT
);

-- تحويله لجدول زمني أيضاً لأن البحث فيه يكون دائماً بالوقت
SELECT create_hypertable('system_audit_log', 'timestamp', if_not_exists => TRUE);


-- 4. جدول إشارات الذكاء الاصطناعي (Strategy Signals)
-- -----------------------------------------------------------------
-- يوثق "لماذا" قرر النظام الشراء أو البيع.
CREATE TABLE IF NOT EXISTS strategy_signals (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    generated_at    TIMESTAMPTZ NOT NULL,
    strategy_id     TEXT        NOT NULL, -- اسم الاستراتيجية (مثلاً DeepSeek_Scalper_V1)
    symbol          TEXT        NOT NULL,
    signal_type     TEXT        NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD', 'KILL')),
    confidence      FLOAT       NOT NULL, -- نسبة الثقة (0.0 - 1.0)
    
    -- ربط الإشارة بالسياق السوقي (سعر السوق لحظة الإشارة)
    market_price_at_signal DOUBLE PRECISION NOT NULL
);


-- 5. جدول أوامر التداول (Trade Orders)
-- -----------------------------------------------------------------
-- سجل التنفيذ الفعلي.
CREATE TABLE IF NOT EXISTS trade_orders (
    internal_id     UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    exchange_id     TEXT,       -- المعرف القادم من Binance (يملأ بعد التنفيذ)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    symbol          TEXT        NOT NULL,
    side            TEXT        NOT NULL CHECK (side IN ('BUY', 'SELL')),
    type            TEXT        NOT NULL DEFAULT 'LIMIT',
    
    quantity        DOUBLE PRECISION NOT NULL,
    price           DOUBLE PRECISION, -- يمكن أن يكون NULL في أوامر السوق (Market Orders)
    
    status          TEXT        NOT NULL DEFAULT 'NEW' 
                                CHECK (status IN ('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED')),
    
    -- الربط الجنائي: ما هي الإشارة التي تسببت في هذا الأمر؟
    signal_ref_id   UUID        REFERENCES strategy_signals(id)
);

-- فهرس للبحث عن الأوامر المفتوحة بسرعة
CREATE INDEX IF NOT EXISTS idx_orders_status ON trade_orders (status) WHERE status IN ('NEW', 'PARTIALLY_FILLED');

-- =================================================================
-- END OF MIGRATION
-- =================================================================