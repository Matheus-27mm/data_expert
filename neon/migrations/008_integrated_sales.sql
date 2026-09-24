alter table public.sales add column product_id uuid;
alter table public.sales add constraint sales_product_company_fk foreign key(company_id,product_id) references public.products(company_id,id);
alter table public.sales add column batch_reference text;
alter table public.sales add column first_due_on date;
alter table public.sales add column stock_managed boolean not null default false;
alter table public.adjustments add column returned_quantity integer not null default 0 check(returned_quantity>=0);
alter table public.adjustments add column reference text;
create unique index adjustments_reference_unique on public.adjustments(company_id,reference) where reference is not null;
alter table public.products add column min_stock integer not null default 0 check(min_stock>=0);
alter table public.products add column max_stock integer not null default 0 check(max_stock>=min_stock);
create function public.validate_integrated_settlement() returns trigger language plpgsql security invoker set search_path='' as $$
declare s public.sales; paid bigint; refunds bigint;
begin
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.sale_id::text,0));
 select * into s from public.sales where id=new.sale_id and company_id=new.company_id;
 if s.product_id is not null then
  select coalesce(sum(amount),0) into paid from public.settlements where sale_id=s.id;
  select coalesce(sum(amount),0) into refunds from public.adjustments where sale_id=s.id;
  if new.received_on<s.sold_on or paid+new.amount>greatest(0,s.revenue-s.card-refunds) then
   raise exception 'Receipt exceeds balance or predates sale' using errcode='22023';
  end if;
 end if;
 return new;
end $$;
create trigger integrated_settlement_bounds before insert on public.settlements for each row execute function public.validate_integrated_settlement();
