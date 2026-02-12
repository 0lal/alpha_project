-- Goal: بيانات تعريف العملاء والمحافظ مع ضوابط الامتثال.
-- Dependencies: KYC Service, Access Control, CRM.

-- بيانات المستخدمين والمحافظ (compliance + portfolio governance)
create table if not exists user_profiles (
  user_id                  text primary key,
  tenant_id                text,

  email                    text not null,
  email_verified           boolean not null default false,
  phone                    text,
  phone_verified           boolean not null default false,

  full_name                text,
  date_of_birth            date,
  country_code             text,
  tax_residency            text,

  kyc_status               text not null check (kyc_status in ('PENDING','VERIFIED','REJECTED','EXPIRED')),
  aml_risk_score           numeric(10,4),
  sanctions_screening      text check (sanctions_screening in ('CLEAR','REVIEW','BLOCKED')),

  risk_tier                text not null check (risk_tier in ('LOW','MEDIUM','HIGH','INSTITUTIONAL')),
  account_status           text not null check (account_status in ('ACTIVE','SUSPENDED','CLOSED')),
  preferred_base_ccy       text,

  last_login_at            timestamptz,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),

  metadata                 jsonb not null default '{}'::jsonb,
  unique (email)
);

create table if not exists user_portfolios (
  portfolio_id             text primary key,
  user_id                  text not null references user_profiles(user_id),
  name                     text not null,
  mandate                  text,

  base_currency            text not null,
  leverage_limit           numeric(12,4) not null default 1 check (leverage_limit >= 1),
  max_drawdown_limit       numeric(12,6) not null default 0.2 check (max_drawdown_limit >= 0 and max_drawdown_limit <= 1),
  max_notional_limit       numeric(30,12),

  is_default               boolean not null default false,
  archived                 boolean not null default false,

  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  settings                 jsonb not null default '{}'::jsonb
);

create index if not exists idx_user_portfolios_user
  on user_portfolios (user_id);

create unique index if not exists uq_user_default_portfolio
  on user_portfolios (user_id)
  where is_default = true and archived = false;

create index if not exists idx_user_profiles_metadata_gin
  on user_profiles using gin (metadata);
