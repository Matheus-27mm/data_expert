-- Integration checks on a disposable PostgreSQL database, after migrations.
begin;
insert into public.companies(id,name,owner_id) values
 ('11111111-1111-4111-8111-111111111111','A','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
 ('22222222-2222-4222-8222-222222222222','B','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
set local role lucra_app;
select set_config('lucra.claims','{"id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","email":"a@example.com"}',true);
do $$ begin
  if (select count(*) from public.companies)<>1 then raise exception 'Company isolation failed'; end if;
  begin
    insert into public.expenses(company_id,description,category,incurred_on,amount)
      values('22222222-2222-4222-8222-222222222222','Forbidden','Test',current_date,100);
    raise exception 'Cross-company insert unexpectedly succeeded';
  exception when insufficient_privilege then null; end;
end $$;
insert into public.sales(id,company_id,external_id,sold_on,product,category,quantity,revenue,cmv,tax,card,commission,installments)
  values('33333333-3333-4333-8333-333333333333','11111111-1111-4111-8111-111111111111','sale-1',current_date,'Test','Test',1,10000,6000,600,200,400,1);
insert into public.adjustments(company_id,sale_id,occurred_on,kind,amount,cost_recovered,description)
  values('11111111-1111-4111-8111-111111111111','33333333-3333-4333-8333-333333333333',current_date,'refund',5000,3000,'Half return');
do $$ begin
  begin
    insert into public.adjustments(company_id,sale_id,occurred_on,kind,amount,cost_recovered,description)
      values('11111111-1111-4111-8111-111111111111','33333333-3333-4333-8333-333333333333',current_date,'refund',6000,0,'Over return');
    raise exception 'Excessive return unexpectedly succeeded';
  exception when invalid_parameter_value then null; end;
  begin
    insert into public.report_schedules(company_id,period,recipient,created_by)
      values('11111111-1111-4111-8111-111111111111','daily','other@example.com','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
    raise exception 'Arbitrary recipient succeeded';
  exception when raise_exception then
    if sqlerrm <> 'Recipient must be your lucra_app email' then raise; end if;
  end;
end $$;
select set_config('lucra.claims','{"id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","email":"b@example.com"}',true);
do $$ begin
  if exists(select 1 from public.sales) or exists(select 1 from public.adjustments) then
    raise exception 'Cross-company read leaked data';
  end if;
end $$;
rollback;