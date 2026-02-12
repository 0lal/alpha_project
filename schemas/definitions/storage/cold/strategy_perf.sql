-- Goal: قياس أداء الاستراتيجيات ومخاطرها عبر الزمن.
-- Dependencies: Strategy Engine, Backtest, Risk Analytics.

-- سجل أداء الاستراتيجيات (institutional KPI + risk factor snapshot)
create table if not exists strategy_perf (
  perf_id                  bigserial primary key,
  strategy_id              text not null,
  strategy_version         text,
  portfolio_id             text,
  benchmark_symbol         text,

  period_start_utc         timestamptz not null,
  period_end_utc           timestamptz not null,
  timeframe                text not null check (timeframe in ('1m','5m','15m','1h','1d','1w','1mo','1q')),

  pnl_realized             numeric(30,12) default 0,
  pnl_unrealized           numeric(30,12) default 0,
  gross_pnl                numeric(30,12),
  net_pnl                  numeric(30,12),

  return_pct               numeric(18,8),
  benchmark_return_pct     numeric(18,8),
  alpha_pct                numeric(18,8),
  beta                     numeric(18,8),
  sharpe_ratio             numeric(18,8),
  sortino_ratio            numeric(18,8),
  calmar_ratio             numeric(18,8),

  max_drawdown_pct         numeric(18,8),
  value_at_risk_99         numeric(30,12),
  expected_shortfall_99    numeric(30,12),

  win_rate_pct             numeric(18,8),
  profit_factor            numeric(18,8),
  turnover                 numeric(30,12),
  gross_exposure           numeric(30,12),
  net_exposure             numeric(30,12),
  trade_count              integer default 0,
  risk_events_count        integer default 0,

  diagnostics              jsonb not null default '{}'::jsonb,
  created_at               timestamptz not null default now(),
  unique (strategy_id, strategy_version, period_start_utc, period_end_utc, timeframe)
);

create index if not exists idx_strategy_perf_sid_period
  on strategy_perf (strategy_id, period_end_utc desc);

create index if not exists idx_strategy_perf_portfolio_period
  on strategy_perf (portfolio_id, period_end_utc desc);

create index if not exists idx_strategy_perf_diag_gin
  on strategy_perf using gin (diagnostics);
