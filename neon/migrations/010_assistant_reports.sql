-- Additive: history of AI analyses per company (append-only, like other reports).
create table public.assistant_reports (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.companies(id),
 question text not null check (length(question) between 3 and 1000),
 period text not null check (period in ('daily','weekly','monthly')),
 anchor date not null,
 answer jsonb not null,
 model text not null,
 input_tokens integer not null default 0,
 output_tokens integer not null default 0,
 created_at timestamptz not null default now(),
 created_by text default lucra_private.user_id(),
 unique(company_id,id)
);
alter table public.assistant_reports enable row level security;
create policy owner_read on public.assistant_reports for select to lucra_app
 using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())));
create policy owner_insert on public.assistant_reports for insert to lucra_app
 with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())));
grant select,insert on public.assistant_reports to lucra_app;
create index assistant_reports_company_created_idx on public.assistant_reports(company_id,created_at desc);
