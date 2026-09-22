-- Company-scoped action plans and append-only customer/owner history.
create table public.action_plans (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 title text not null, description text not null default '', priority text not null check(priority in ('high','medium','low')),
 status text not null default 'pending' check(status in ('pending','progress','done')),
 due_on date, created_at timestamptz not null default now(), unique(company_id,id)
);
create table public.plan_updates (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 plan_id uuid not null, message text not null, created_at timestamptz not null default now(),
 foreign key(company_id,plan_id) references public.action_plans(company_id,id)
);
create table public.customers (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 name text not null, email text not null default '', phone text not null default '',
 created_at timestamptz not null default now(), unique(company_id,id)
);
create table public.customer_contacts (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 customer_id uuid not null, channel text not null check(channel in ('phone','email','whatsapp','store','other')),
 message text not null, response text not null default '', next_on date,
 created_at timestamptz not null default now(), foreign key(company_id,customer_id) references public.customers(company_id,id)
);
alter table public.expenses add column external_id text;
create unique index expenses_import_reference on public.expenses(company_id,external_id);
do $$ declare t text; begin
 foreach t in array array['action_plans','plan_updates','customers','customer_contacts'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('create policy owner_read on public.%I for select to lucra_app using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
  execute format('create policy owner_insert on public.%I for insert to lucra_app with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
  execute format('grant select,insert on public.%I to lucra_app',t);
  execute format('create index on public.%I(company_id)',t);
 end loop;
end $$;
grant update on public.action_plans to lucra_app;
create policy owner_update on public.action_plans for update to lucra_app
 using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))
 with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())));
