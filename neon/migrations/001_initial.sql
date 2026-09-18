-- Apply with the Neon database owner. This role is used only inside FastAPI transactions.
create role lucra_app nologin nosuperuser nobypassrls;
do $$ begin execute format('grant lucra_app to %I',current_user); end $$;
create schema lucra_private;
create function lucra_private.claims() returns jsonb language sql stable as $$
 select coalesce(nullif(current_setting('lucra.claims',true),''),'{}')::jsonb
$$;
create function lucra_private.user_id() returns text language sql stable as $$
 select lucra_private.claims()->>'id'
$$;
grant usage on schema public,lucra_private to lucra_app;
-- Foundation for real multi-company data. The current dashboard uses demo data.
create table public.companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_id text not null
);
create table public.sales (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  sold_on date not null,
  product text not null,
  category text not null,
  quantity integer not null check (quantity > 0),
  revenue bigint not null check (revenue >= 0),
  cmv bigint not null check (cmv >= 0),
  tax bigint not null check (tax >= 0),
  card bigint not null check (card >= 0),
  commission bigint not null check (commission >= 0),
  installments integer not null check (installments between 1 and 12)
);
create index sales_company_date_idx on public.sales(company_id, sold_on);
alter table public.companies enable row level security;
alter table public.sales enable row level security;
create policy "Owner manages company" on public.companies for all to lucra_app
  using (owner_id = (select lucra_private.user_id())) with check (owner_id = (select lucra_private.user_id()));
create policy "Owner manages sales" on public.sales for all to lucra_app
  using (exists (select 1 from public.companies c where c.id = company_id and c.owner_id = (select lucra_private.user_id())))
  with check (exists (select 1 from public.companies c where c.id = company_id and c.owner_id = (select lucra_private.user_id())));
