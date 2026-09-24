alter table public.products add column notes text not null default '';
alter table public.customers
 add column document text not null default '',
 add column pix_key text not null default '',
 add column address text not null default '',
 add column city text not null default '',
 add column notes text not null default '';
grant update on public.customers to lucra_app;
create policy owner_update on public.customers for update to lucra_app
 using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))
 with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())));
