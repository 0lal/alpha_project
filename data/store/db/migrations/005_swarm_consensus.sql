-- ALPHA SOVEREIGN - SWARM CONSENSUS MATRIX (DEMOCRATIC AI)
-- =================================================================
-- Component Name: data/db/migrations/005_swarm_consensus.sql
-- Core Responsibility: إنشاء مصفوفة قرارات الوكلاء وسجل التصويت المرجح لذكاء السرب (Governance Pillar).
-- Database Engine: PostgreSQL 14+ with TimescaleDB.
-- Forensic Impact: يوثق "النية الجماعية" (Collective Intent). يجيب على سؤال: "لماذا وافق السرب على هذه المخاطرة؟".
-- =================================================================

-- 1. جدول المقترحات (Swarm Proposals)
-- -----------------------------------------------------------------
-- يمثل "مشروع قانون" أو "اقتراح صفقة" يطرحه أحد الوكلاء للنقاش.
CREATE TABLE IF NOT EXISTS swarm_proposals (
    proposal_id     UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- الوكيل الذي طرح الاقتراح (The Initiator)
    proposer_agent  TEXT        NOT NULL, 
    
    -- موضوع الاقتراح
    symbol          TEXT        NOT NULL,
    action          TEXT        NOT NULL CHECK (action IN ('BUY', 'SELL', 'CLOSE', 'HEDGE')),
    
    -- المعايير المقترحة
    suggested_price DOUBLE PRECISION,
    stop_loss       DOUBLE PRECISION,
    take_profit     DOUBLE PRECISION,
    
    -- حالة الاقتراح
    status          TEXT        NOT NULL DEFAULT 'VOTING_OPEN'
                                CHECK (status IN ('VOTING_OPEN', 'APPROVED', 'REJECTED', 'EXPIRED', 'EXECUTED')),
    
    -- النتيجة النهائية للتصويت
    final_score     DOUBLE PRECISION DEFAULT 0.0,
    required_threshold DOUBLE PRECISION NOT NULL, -- عتبة النجاح المطلوبة في تلك اللحظة
    
    -- المهلة الزمنية للتصويت (بعدها يعتبر الاقتراح لاغياً)
    expires_at      TIMESTAMPTZ NOT NULL
);

-- تحويل الجدول لجدول زمني لسرعة البحث في الأرشيف
SELECT create_hypertable('swarm_proposals', 'created_at', if_not_exists => TRUE);


-- 2. جدول أصوات الوكلاء (Agent Votes)
-- -----------------------------------------------------------------
-- يسجل صوت كل وكيل متخصص.
-- ملاحظة: الوكلاء لديهم "أوزان" مختلفة. صوت "مدير المخاطر" قد يزن 3 أضعاف صوت "محلل تويتر".
CREATE TABLE IF NOT EXISTS swarm_votes (
    vote_id         UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    proposal_id     UUID        NOT NULL, -- لا نستخدم REFERENCES هنا لأن الجدول المقسم (Hypertable) يفرض قيوداً على المفاتيح الأجنبية
    
    voted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- الوكيل المصوت
    voter_agent     TEXT        NOT NULL,
    
    -- القرار (-1 = رفض، 0 = حياد، 1 = موافقة)
    sentiment       INT         NOT NULL CHECK (sentiment BETWEEN -1 AND 1),
    
    -- وزن الوكيل *وقت التصويت* (لتوثيق القوة التصويتية تاريخياً)
    agent_weight    DOUBLE PRECISION NOT NULL,
    
    -- النتيجة المحسوبة لهذا الصوت (sentiment * weight)
    weighted_score  DOUBLE PRECISION NOT NULL,
    
    -- التبرير النصي (Explainability): لماذا صوتت هكذا؟
    -- مثال: "Rejected due to high volatility"
    justification   TEXT,
    
    -- البيانات التي استند عليها الوكيل (Snapshot)
    context_data    JSONB
);

-- فهرس لربط الأصوات بالمقترحات بسرعة
CREATE INDEX IF NOT EXISTS idx_votes_proposal ON swarm_votes (proposal_id, voted_at);


-- 3. سجل سمعة الوكلاء (Agent Reputation Ledger)
-- -----------------------------------------------------------------
-- نظام مكافأة وعقاب للوكلاء.
-- إذا اقترح وكيل صفقة وخسرت، يتم خفض وزنه التصويتي في المستقبل.
CREATE TABLE IF NOT EXISTS agent_reputation_ledger (
    entry_id        UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    agent_name      TEXT        NOT NULL,
    
    -- التغيير في السمعة (مثلاً +0.1 أو -0.5)
    score_delta     DOUBLE PRECISION NOT NULL,
    
    -- السمعة الجديدة بعد التعديل
    new_score       DOUBLE PRECISION NOT NULL,
    
    -- سبب التعديل (رقم الصفقة الخاسرة/الرابحة)
    reason_ref      TEXT        NOT NULL
);

-- =================================================================
-- END OF MIGRATION
-- =================================================================