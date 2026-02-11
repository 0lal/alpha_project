-- ALPHA SOVEREIGN - FISCAL LEDGER (FINANCIAL INTEGRITY)
-- =================================================================
-- Component Name: data/db/migrations/006_fiscal_ledger.sql
-- Core Responsibility: إنشاء السجل المالي السيادي وإدارة المحفظة التشغيلية (Governance Pillar).
-- Database Engine: PostgreSQL 14+ with TimescaleDB.
-- Forensic Impact: يمنع "اختلاس" الأموال أو ضياعها حسابياً. يطبق قاعدة: (الأصول = الالتزامات + حقوق الملكية).
-- =================================================================

-- 1. جدول الحسابات والمحافظ (Accounts & Wallets)
-- -----------------------------------------------------------------
-- يعرف كل "جيب" يملك النظام فيه مالاً.
CREATE TABLE IF NOT EXISTS fiscal_accounts (
    account_id      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- اسم الحساب (مثلاً: 'Binance_Spot_Main', 'Operational_Reserve', 'Cold_Storage_1')
    account_name    TEXT        NOT NULL UNIQUE,
    
    -- نوع الحساب
    account_type    TEXT        NOT NULL 
                                CHECK (account_type IN ('EXCHANGE', 'BANK', 'WALLET', 'VIRTUAL_RESERVE')),
    
    -- العملة الأساسية للحساب
    currency        TEXT        NOT NULL,
    
    -- الرصيد الحالي (يتم تحديثه دورياً بعد مطابقة السجل)
    current_balance DOUBLE PRECISION DEFAULT 0.0,
    
    -- حالة الحساب
    is_frozen       BOOLEAN     DEFAULT FALSE,
    
    -- التوقيع الأمني (Hash) للرصيد الأخير لمنع التلاعب المباشر بقاعدة البيانات
    last_integrity_hash TEXT
);

-- 2. السجل المالي العام (General Ledger - Transactions)
-- -----------------------------------------------------------------
-- هذا الجدول يسجل تدفق الأموال. لا يتم حذف أي صف منه أبداً.
-- كل عملية تداول ناجحة تولد قيداً هنا (إضافة ربح أو خصم خسارة).
CREATE TABLE IF NOT EXISTS general_ledger (
    tx_id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- الحساب المتأثر
    account_id      UUID        NOT NULL REFERENCES fiscal_accounts(account_id),
    
    -- نوع العملية
    tx_type         TEXT        NOT NULL 
                                CHECK (tx_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRADE_REALIZED_PNL', 'FEE', 'INTERNAL_TRANSFER')),
    
    -- المبلغ (سالب للخروج، موجب للدخول)
    amount          DOUBLE PRECISION NOT NULL,
    
    -- الرصيد بعد العملية (للمراجعة السريعة)
    balance_after   DOUBLE PRECISION NOT NULL,
    
    -- المرجع الجنائي: ما هو الأمر أو السبب الذي أنشأ هذه الحركة؟
    reference_id    TEXT,       -- e.g., Order ID, Transfer Hash
    description     TEXT,
    
    -- التصنيف المالي (للتقارير)
    category        TEXT        DEFAULT 'TRADING' -- or 'OPEX', 'CAPEX'
);

-- تحويله لجدول زمني للأرشفة طويلة المدى
SELECT create_hypertable('general_ledger', 'timestamp', if_not_exists => TRUE);


-- 3. جدول المصاريف التشغيلية (Operational Expenses - OpEx)
-- -----------------------------------------------------------------
-- لأن النظام يمول نفسه ذاتياً، يجب أن يسجل تكاليفه (سيرفرات، بيانات، كهرباء).
CREATE TABLE IF NOT EXISTS operational_expenses (
    expense_id      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    due_date        TIMESTAMPTZ NOT NULL,
    
    vendor_name     TEXT        NOT NULL, -- e.g., 'AWS', 'OpenAI', 'Bloomberg'
    amount_usd      DOUBLE PRECISION NOT NULL,
    
    status          TEXT        NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PAID', 'OVERDUE')),
    paid_at         TIMESTAMPTZ,
    
    -- هل تم الدفع من أرباح التداول؟
    funding_source  UUID        REFERENCES fiscal_accounts(account_id)
);


-- 4. تقارير الأداء المالي (Performance Snapshots)
-- -----------------------------------------------------------------
-- لقطة يومية لأداء المحفظة الكلي (NAV - Net Asset Value).
CREATE TABLE IF NOT EXISTS performance_snapshots (
    date            DATE        NOT NULL PRIMARY KEY,
    
    total_equity_usd DOUBLE PRECISION NOT NULL, -- القيمة الإجمالية للأصول
    daily_pnl_usd    DOUBLE PRECISION NOT NULL, -- الربح/الخسارة اليومية
    
    -- مقاييس المخاطر المالية
    drawdown_pct     DOUBLE PRECISION, -- نسبة التراجع من القمة
    sharpe_ratio     DOUBLE PRECISION, -- نسبة العائد للمخاطرة
    
    high_water_mark  DOUBLE PRECISION  -- أعلى قيمة وصلتها المحفظة (لحساب عمولات النجاح)
);

-- =================================================================
-- END OF MIGRATION
-- =================================================================