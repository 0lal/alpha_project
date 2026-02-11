-- TimescaleDB Hypertable

-- ALPHA SOVEREIGN - MARKET DATA ANALYTICAL SCHEMA
-- =================================================================
-- Component Name: data/db/models/market_data_schema.sql
-- Core Responsibility: تحديد هيكلية بيانات السوق اللحظية والتاريخية (تحويل النبضات إلى شموع).
-- Database Engine: PostgreSQL 14+ with TimescaleDB Continuous Aggregates.
-- Forensic Impact: يوفر "ملخصاً زمنياً" غير قابل للتلاعب لحركة السوق، يستخدم للمقارنة مع البيانات الخام لكشف الفجوات.
-- =================================================================

-- 1. المظهر المادي للشموع دقيقة واحدة (1-Minute Candles)
-- -----------------------------------------------------------------
-- هذا ليس جدولاً عادياً، بل هو "تجميع مستمر" (Continuous Aggregate).
-- قاعدة البيانات تقوم بتحويل الـ Ticks إلى شموع OHLCV تلقائياً وبسرعة البرق.
CREATE MATERIALIZED VIEW IF NOT EXISTS market_candles_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket, -- تقسيم الوقت لbuckets بحجم دقيقة
    symbol,
    source,
    
    -- حسابات الشموع اليابانية القياسية
    FIRST(price, time)  AS open,
    MAX(price)          AS high,
    MIN(price)          AS low,
    LAST(price, time)   AS close,
    
    -- حساب الحجم الإجمالي
    SUM(quantity)       AS volume,
    
    -- حساب عدد الصفقات (لتحليل السيولة)
    COUNT(*)            AS trade_count,
    
    -- المتوسط المرجح بالحجم (VWAP) لهذه الدقيقة
    SUM(price * quantity) / NULLIF(SUM(quantity), 0) AS vwap
    
FROM market_ticks
GROUP BY bucket, symbol, source
WITH NO DATA; -- سيتم ملء البيانات لاحقاً عبر السياسة

-- 2. المظهر المادي للشموع ساعة واحدة (1-Hour Candles)
-- -----------------------------------------------------------------
-- يتم بناؤه فوق جدول الدقائق لتوفير الأداء (Hierarchical Aggregation).
CREATE MATERIALIZED VIEW IF NOT EXISTS market_candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', bucket) AS hour_bucket,
    symbol,
    source,
    
    FIRST(open, bucket)  AS open,
    MAX(high)            AS high,
    MIN(low)             AS low,
    LAST(close, bucket)  AS close,
    
    SUM(volume)          AS volume,
    SUM(trade_count)     AS trade_count,
    
    -- إعادة حساب VWAP للساعة
    SUM(vwap * volume) / NULLIF(SUM(volume), 0) AS vwap
    
FROM market_candles_1m
GROUP BY hour_bucket, symbol, source
WITH NO DATA;


-- 3. سياسات التحديث التلقائي (Refresh Policies)
-- -----------------------------------------------------------------
-- نخبر قاعدة البيانات بتحديث الشموع الجديدة باستمرار.

-- تحديث شموع الدقيقة: ابدأ من دقيقتين في الماضي حتى اللحظة الحالية
-- (التأخير البسيط لضمان وصول كل التيكات المتأخرة عبر الشبكة)
SELECT add_continuous_aggregate_policy('market_candles_1m',
    start_offset => INTERVAL '10 minutes',
    end_offset   => INTERVAL '10 seconds',
    schedule_interval => INTERVAL '1 minute');

-- تحديث شموع الساعة
SELECT add_continuous_aggregate_policy('market_candles_1h',
    start_offset => INTERVAL '2 hours',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 hour');


-- 4. وجهات نظر جنائية (Forensic Views)
-- -----------------------------------------------------------------
-- عرض لكشف الفجوات الزمنية (Data Gaps) التي تزيد عن 5 دقائق.
-- يساعد المحقق في معرفة متى انقطع الاتصال بالسوق.
CREATE OR REPLACE VIEW forensic_data_gaps AS
SELECT
    symbol,
    bucket AS gap_start,
    LEAD(bucket) OVER (PARTITION BY symbol ORDER BY bucket) AS next_candle,
    LEAD(bucket) OVER (PARTITION BY symbol ORDER BY bucket) - bucket AS gap_duration
FROM market_candles_1m
WHERE volume = 0 OR trade_count = 0; -- أو يمكن استخدام منطق فقدان الصفوف

-- =================================================================
-- END OF SCHEMA
-- =================================================================