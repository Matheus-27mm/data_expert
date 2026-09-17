-- Foundation for real multi-company data. The current dashboard uses demo data.
create table public.companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_id uuid not null references auth.users(id)
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
create policy "Owner manages company" on public.companies for all to authenticated
  using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "Owner manages sales" on public.sales for all to authenticated
  using (exists (select 1 from public.companies c where c.id = company_id and c.owner_id = (select auth.uid())))
  with check (exists (select 1 from public.companies c where c.id = company_id and c.owner_id = (select auth.uid())));
