-- Purchases of goods for resale are inventory: their cost reaches the result
-- as CMV when each item is sold. Booking the supplier bill as an operating
-- expense too counted the same cost twice. Such bills stay payable (cash
-- forecast, payments) but no longer create an expense. Forward-only: bills
-- already booked keep their expense rows (ledgers are append-only).
create or replace function public.book_bill_expense() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if pg_catalog.lower(new.category) like '%mercadoria%' or pg_catalog.lower(new.category) like '%revenda%' then
  return new;
 end if;
 insert into public.expenses(company_id,bill_id,description,category,incurred_on,amount)
 values(new.company_id,new.id,new.description,new.category,new.incurred_on,new.amount);
 return new;
end $$;
