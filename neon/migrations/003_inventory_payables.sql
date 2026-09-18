-- Inventory is a movement ledger; sales do not silently change stock.
alter table public.products add constraint products_company_id_unique unique(company_id,id);
create table public.stock_movements (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 product_id uuid not null, occurred_on date not null,
 direction text not null check(direction in ('in','out')), quantity integer not null check(quantity>0),
 reference text not null, description text not null,
 unique(company_id,reference), foreign key(company_id,product_id) references public.products(company_id,id)
);
create table public.bills (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 reference text not null, supplier text not null, description text not null, category text not null,
 incurred_on date not null, due_on date not null, amount bigint not null check(amount>0),
 unique(company_id,reference), unique(company_id,id)
);
create table public.bill_payments (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 bill_id uuid not null, reference text not null, paid_on date not null, amount bigint not null check(amount>0),
 unique(company_id,reference), foreign key(company_id,bill_id) references public.bills(company_id,id)
);
alter table public.expenses add column bill_id uuid unique references public.bills(id);
do $$ declare t text; begin
 foreach t in array array['stock_movements','bills','bill_payments'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('create policy owner_read on public.%I for select to lucra_app using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
  execute format('create policy owner_insert on public.%I for insert to lucra_app with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
  execute format('grant select,insert on public.%I to lucra_app',t);
  execute format('create index on public.%I(company_id)',t);
 end loop;
end $$;
create function public.validate_stock() returns trigger language plpgsql security invoker set search_path='' as $$
declare balance bigint; begin
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.product_id::text,1));
 select coalesce(sum(case direction when 'in' then quantity else -quantity end),0) into balance
 from public.stock_movements where product_id=new.product_id and company_id=new.company_id;
 if new.direction='out' and new.quantity>balance then
  raise exception 'Insufficient stock' using errcode='22023';
 end if;
 return new;
end $$;
create trigger stock_bounds before insert on public.stock_movements for each row execute function public.validate_stock();
create function public.validate_bill_payment() returns trigger language plpgsql security invoker set search_path='' as $$
declare total bigint; paid bigint; begin
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.bill_id::text,2));
 select amount into total from public.bills where id=new.bill_id and company_id=new.company_id;
 select coalesce(sum(amount),0) into paid from public.bill_payments where bill_id=new.bill_id;
 if total is null or paid+new.amount>total then
  raise exception 'Payment exceeds bill balance' using errcode='22023';
 end if;
 return new;
end $$;
create trigger bill_payment_bounds before insert on public.bill_payments for each row execute function public.validate_bill_payment();
create function public.book_bill_expense() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 insert into public.expenses(company_id,bill_id,description,category,incurred_on,amount)
 values(new.company_id,new.id,new.description,new.category,new.incurred_on,new.amount);
 return new;
end $$;
create trigger bill_expense after insert on public.bills for each row execute function public.book_bill_expense();
