-- أرشيف الصفقات المنفذة (execution-grade with analytics-friendly indexes)
create table if not exists trade_history (
  trade_id                 text primary key,
  venue_trade_id           text,
  order_id                 text not null,
  client_order_id          text,
  parent_order_id          text,
  execution_id             text,

  account_id               text not null,
  portfolio_id             text,
  strategy_id              text,
  trader_id                text,

  symbol                   text not null,
  asset_class              text not null check (asset_class in ('SPOT','FUTURES','OPTIONS','FX','EQUITY','BOND')),
  side                     text not null check (side in ('BUY','SELL')),
  quantity                 numeric(30,12) not null check (quantity > 0),
  price                    numeric(30,12) not null check (price > 0),
  notional                 numeric(30,12) generated always as (quantity * price) stored,

  fee                      numeric(30,12) default 0,
  fee_currency             text,
  commission               numeric(30,12) default 0,
  tax                      numeric(30,12) default 0,
  slippage_bps             numeric(12,6),
  liquidity_flag           text check (liquidity_flag in ('MAKER','TAKER','UNKNOWN')),

  execution_time_utc       timestamptz not null,
  receive_time_utc         timestamptz,
  settlement_date          date,

  venue                    text,
  venue_region             text,
  book_type                text check (book_type in ('LIT','DARK','OTC')),

  trace_id                 text,
  request_id               text,
  metadata                 jsonb not null default '{}'::jsonb,
  created_at               timestamptz not null default now()
);

create index if not exists idx_trade_history_symbol_time
  on trade_history (symbol, execution_time_utc desc);

create index if not exists idx_trade_history_strategy_time
  on trade_history (strategy_id, execution_time_utc desc);

create index if not exists idx_trade_history_account_time
  on trade_history (account_id, execution_time_utc desc);

create index if not exists idx_trade_history_execution_id
  on trade_history (execution_id);

create index if not exists idx_trade_history_metadata_gin
  on trade_history using gin (metadata);
