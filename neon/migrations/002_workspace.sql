-- Apply after 001_initial.sql. Monetary fields store integer cents.
alter table public.sales add column external_id text;
update public.sales set external_id = id::text where external_id is null;
alter table public.sales alter column external_id set not null;
alter table public.sales add constraint sales_external_unique unique(company_id,external_id);
alter table public.sales add constraint sales_company_id_unique unique(company_id,id);

create table public.products (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id),
  name text not null, category text not null, sku text not null,
  unit_cost bigint not null check(unit_cost >= 0),
  unit_price bigint not null check(unit_price > 0), active boolean not null default true,
  unique(company_id,sku)
);
create table public.expenses (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id),
  description text not null, category text not null, incurred_on date not null,
  amount bigint not null check(amount > 0)
);
create table public.adjustments (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id), sale_id uuid not null,
  occurred_on date not null, kind text not null check(kind in ('refund','chargeback')),
  amount bigint not null check(amount > 0), cost_recovered bigint not null default 0 check(cost_recovered >= 0),
  description text not null,
  foreign key(company_id,sale_id) references public.sales(company_id,id)
);
create table public.settlements (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id), sale_id uuid not null,
  reference text not null, received_on date not null, amount bigint not null check(amount > 0),
  unique(company_id,reference),
  foreign key(company_id,sale_id) references public.sales(company_id,id)
);
create table public.payment_terms (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id), name text not null,
  installments integer not null check(installments between 1 and 12),
  tax_rate numeric not null check(tax_rate between 0 and 50),
  commission_rate numeric not null check(commission_rate between 0 and 50),
  card_base numeric not null check(card_base between 0 and 50),
  anticipation_rate numeric not null check(anticipation_rate between 0 and 20)
);
create table public.report_history (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id),
  period text not null check(period in ('daily','weekly','monthly')), anchor date not null,
  snapshot jsonb not null, created_by text not null,
  created_at timestamptz not null default now()
);
create table public.report_schedules (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id),
  period text not null check(period in ('daily','weekly','monthly')),
  recipient text not null, created_by text not null,
  enabled boolean not null default true,
  unique(company_id,period,recipient)
);
create table public.report_deliveries (
  id uuid primary key default gen_random_uuid(),
  schedule_id uuid not null references public.report_schedules(id),
  anchor date not null, status text not null check(status in ('processing','sent','failed')),
  created_at timestamptz not null default now(),
  unique(schedule_id,anchor)
);
alter table public.report_deliveries enable row level security;
revoke all on public.report_deliveries from public, lucra_app;

-- Financial records are append-only. Corrections are explicit adjustment records.
drop policy "Owner manages sales" on public.sales;
create policy "Owner reads sales" on public.sales for select to lucra_app
  using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())));
create policy "Owner inserts sales" on public.sales for insert to lucra_app
  with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())));

do $$
declare t text;
begin
  foreach t in array array['products','expenses','adjustments','settlements','payment_terms','report_history','report_schedules'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('create policy owner_read on public.%I for select to lucra_app using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
    execute format('create policy owner_insert on public.%I for insert to lucra_app with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
    execute format('grant select,insert on public.%I to lucra_app',t);
    execute format('create index on public.%I(company_id)',t);
  end loop;
  foreach t in array array['products','payment_terms','report_schedules'] loop
    execute format('create policy owner_update on public.%I for update to lucra_app using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id()))) with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
    execute format('grant update on public.%I to lucra_app',t);
  end loop;
end $$;
grant select,insert on public.sales to lucra_app;
grant select,insert,update on public.companies to lucra_app;

-- Lock the sale while checking cumulative returns, including simultaneous requests.
create function public.validate_adjustment() returns trigger language plpgsql security invoker set search_path='' as $$
declare sale public.sales; returned bigint; recovered bigint;
begin
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.sale_id::text,0));
  select * into sale from public.sales where id=new.sale_id and company_id=new.company_id;
  if not found then raise exception 'Sale unavailable'; end if;
  select coalesce(sum(amount),0),coalesce(sum(cost_recovered),0) into returned,recovered
    from public.adjustments where sale_id=new.sale_id;
  if returned+new.amount>sale.revenue or recovered+new.cost_recovered>sale.cmv then
    raise exception 'Return exceeds original revenue or cost' using errcode='22023';
  end if;
  return new;
end $$;
create trigger adjustment_bounds before insert on public.adjustments for each row execute function public.validate_adjustment();

-- Prevent users bypassing the API to send mail to arbitrary addresses.
create function public.validate_schedule() returns trigger language plpgsql security invoker set search_path='' as $$
begin
  if new.created_by is distinct from lucra_private.user_id() or new.recipient is distinct from (lucra_private.claims()->>'email') then
    raise exception 'Recipient must be your lucra_app email';
  end if;
  return new;
end $$;
create trigger schedule_owner before insert or update on public.report_schedules for each row execute function public.validate_schedule();
