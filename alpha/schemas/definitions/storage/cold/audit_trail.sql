-- سجل جنائي لكل حركة في النظام (forensics + compliance ready)
create table if not exists audit_trail (
  audit_id                 bigserial primary key,
  event_id                 text not null,
  event_type               text not null,
  event_category           text not null check (event_category in ('AUTH','TRADING','RISK','ADMIN','DATA','SYSTEM')),

  actor_type               text not null check (actor_type in ('USER','SERVICE','SYSTEM')),
  actor_id                 text,
  actor_role               text,
  actor_tenant_id          text,

  target_type              text,
  target_id                text,
  action                   text not null,
  outcome                  text not null check (outcome in ('SUCCESS','FAILURE','DENIED')),
  severity                 text not null check (severity in ('INFO','WARNING','ERROR','CRITICAL')),

  source_ip                inet,
  source_geo               text,
  user_agent               text,
  session_id               text,

  request_id               text,
  trace_id                 text,
  correlation_id           text,

  before_state             jsonb,
  after_state              jsonb,
  details                  jsonb not null default '{}'::jsonb,

  event_time_utc           timestamptz not null,
  recorded_at              timestamptz not null default now(),
  retention_class          text not null default 'STANDARD' check (retention_class in ('SHORT','STANDARD','LONG','LEGAL_HOLD')),

  unique (event_id)
);

create index if not exists idx_audit_event_time
  on audit_trail (event_time_utc desc);

create index if not exists idx_audit_target
  on audit_trail (target_type, target_id, event_time_utc desc);

create index if not exists idx_audit_actor_time
  on audit_trail (actor_id, event_time_utc desc);

create index if not exists idx_audit_details_gin
  on audit_trail using gin (details);
