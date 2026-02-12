-- دفتر الأستاذ المالي (double-entry capable with reconciliation fields)
create table if not exists ledger_entries (
  entry_id                 text primary key,
  transaction_id           text not null,
  transaction_group_id     text,
  account_id               text not null,
  wallet_id                text,
  subaccount_id            text,

  currency                 text not null,
  amount                   numeric(30,12) not null,
  entry_type               text not null check (entry_type in ('DEBIT','CREDIT')),
  direction                text check (direction in ('IN','OUT','INTERNAL')),

  balance_before           numeric(30,12),
  balance_after            numeric(30,12),
  available_before         numeric(30,12),
  available_after          numeric(30,12),

  source_type              text not null check (source_type in ('TRADE','TRANSFER','FEE','ADJUSTMENT','FUNDING','SETTLEMENT','LIQUIDATION')),
  source_ref               text,
  counterparty_account_id  text,

  posted_at                timestamptz not null,
  effective_at             timestamptz,
  value_date               date,

  reconciliation_status    text not null default 'PENDING' check (reconciliation_status in ('PENDING','MATCHED','MISMATCH','WAIVED')),
  reconciliation_batch_id  text,

  trace_id                 text,
  request_id               text,
  metadata                 jsonb not null default '{}'::jsonb,
  created_at               timestamptz not null default now(),

  unique (transaction_id, account_id, entry_type, currency, amount, posted_at)
);

create index if not exists idx_ledger_account_currency_time
  on ledger_entries (account_id, currency, posted_at desc);

create index if not exists idx_ledger_transaction
  on ledger_entries (transaction_id);

create index if not exists idx_ledger_reco_status
  on ledger_entries (reconciliation_status, posted_at desc);

create index if not exists idx_ledger_metadata_gin
  on ledger_entries using gin (metadata);
