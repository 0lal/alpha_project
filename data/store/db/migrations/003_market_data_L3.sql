-- Initial Database Schema

-- ALPHA SOVEREIGN - LEVEL 3 MARKET DATA (ORDER BOOK)
-- =================================================================
-- Component Name: data/db/migrations/003_market_data_L3.sql
-- Core Responsibility: تحديد هياكل بيانات عمق السوق (L3) المحسنة للأداء العالي (Performance Pillar).
-- Database Engine: PostgreSQL 14+ with TimescaleDB & JSONB.
-- Forensic Impact: القدرة على "إعادة تمثيل الجريمة" (Market Replay) بإعادة بناء شكل دفتر الأوامر في أي لحظة في الماضي.
-- =================================================================

-- 1. جدول لقطات دفتر الأوامر (Order Book Snapshots)
-- -----------------------------------------------------------------
-- هذا الجدول يخزن "صورة كاملة" لدفتر الأوامر (مثلاً أفضل 50 مستوى) كل ثانية.
-- الهدف: نقطة استعادة سريعة (Recovery Point) دون الحاجة لإعادة حساب ملايين التحديثات من الصفر.
CREATE TABLE IF NOT EXISTS ob_snapshots (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT        NOT NULL,
    exchange        TEXT        NOT NULL,
    
    -- تخزين العروض والطلبات كبيانات ثنائية مضغوطة (JSONB)
    -- الهيكل: [[price, qty], [price, qty], ...]
    -- هذا أسرع 10 مرات من إنشاء جدول منفصل للصفوف في عمليات القراءة الكتلية.
    bids            JSONB       NOT NULL,
    asks            JSONB       NOT NULL,
    
    -- الرقم التسلسلي القادم من البورصة لضمان التزامن الجنائي
    last_update_id  BIGINT      NOT NULL,
    
    -- مفتاح مركب للأداء
    UNIQUE (time, symbol, exchange)
);

-- تحويل الجدول إلى Hypertable (تقطيع زمني)
SELECT create_hypertable('ob_snapshots', 'time', if_not_exists => TRUE);

-- تفعيل ضغط البيانات (Compression) لأن هذه البيانات تستهلك مساحة ضخمة
ALTER TABLE ob_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

-- إضافة سياسة ضغط تلقائي للبيانات التي مر عليها أكثر من يوم
SELECT add_compression_policy('ob_snapshots', INTERVAL '1 day');


-- 2. جدول تحديثات الأوامر الفردية (L3 Order Updates)