-- Additive only: compatible with the code already deployed (expand step).

-- Ledger lookups by parent entity: the invariant triggers and the SQL
-- aggregations filter on these columns, which composite FKs do not index.
create index if not exists settlements_sale_idx on public.settlements(sale_id);
create index if not exists adjustments_sale_idx on public.adjustments(sale_id);
create index if not exists stock_movements_product_idx on public.stock_movements(product_id);
create index if not exists bill_payments_bill_idx on public.bill_payments(bill_id);
create index if not exists plan_updates_plan_idx on public.plan_updates(plan_id);
create index if not exists customer_contacts_customer_idx on public.customer_contacts(customer_id);

-- Authorship of records. The default reads the transaction-local RLS identity,
-- so every insert made through the API is attributed without code changes.
-- Rows that predate this migration, and worker inserts, stay null.
do $$ declare t text; begin
 foreach t in array array['products','sales','expenses','adjustments','settlements','stock_movements','bills','bill_payments'] loop
  execute format('alter table public.%I add column if not exists created_at timestamptz default now()',t);
  execute format('alter table public.%I add column if not exists created_by text default lucra_private.user_id()',t);
 end loop;
end $$;

-- Login role for the API (not yet able to log in). NOINHERIT: it holds no table
-- privilege of its own, so a code path that skips SET ROLE lucra_app reads
-- nothing. Activation is an out-of-band step: see docs/adr/0009.
do $$ begin
 if not exists (select 1 from pg_roles where rolname='lucra_api') then
  create role lucra_api nologin noinherit nosuperuser nobypassrls nocreatedb nocreaterole;
 end if;
end $$;
grant lucra_app to lucra_api;
grant select on public.lucra_migrations to lucra_api;
