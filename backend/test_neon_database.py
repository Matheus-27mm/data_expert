"""Integration tests: set NEON_TEST_DATABASE_URL to a disposable PostgreSQL database."""
import os
from pathlib import Path
from uuid import UUID,uuid4
import psycopg
import pytest
from fastapi import HTTPException
from backend.neon_repository import Session
from backend.workspace import company_summary, inventory, payables, bank_preview
from datetime import date

@pytest.fixture(scope='module')
def database():
    url=os.getenv('NEON_TEST_DATABASE_URL')
    if not url: pytest.skip('Disposable PostgreSQL not configured')
    previous=os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL']=url
    try:
        from scripts.migrate import main
        main()
        main()  # Repeated migrations must not recreate objects.
        yield url
    finally:
        if previous is None: os.environ.pop('DATABASE_URL',None)
        else: os.environ['DATABASE_URL']=previous

def test_database_rls_policies(database):
    with psycopg.connect(database) as connection:
        connection.execute(Path('neon/tests/rls.sql').read_text())

def test_adapter_transactions_and_tenant_isolation(database):
    user={'id':str(uuid4()),'email':'owner@example.test','email_confirmed_at':True}
    db=Session('',user)
    other=Session('',{'id':str(uuid4()),'email':'other@example.test'})
    company=db.insert('companies',{'name':'Integration','owner_id':user['id']})
    cid=company['id']
    assert other.rows('companies',id='eq.'+cid)==[]
    sale={'company_id':cid,'external_id':'first','sold_on':'2026-09-18','product':'Test','category':'Test',
          'quantity':1,'revenue':10000,'cmv':6000,'tax':600,'card':200,'commission':400,'installments':1}
    db.insert('sales',sale)
    with pytest.raises(HTTPException) as denied: other.insert('sales',{**sale,'external_id':'forbidden'})
    assert denied.value.status_code==403
    with pytest.raises(HTTPException) as duplicate:
        db.request('POST','sales',payload=[{**sale,'external_id':'second'},sale])
    assert duplicate.value.status_code==409
    assert len(db.rows('sales',cid))==1  # Entire batch rolled back.
    db.insert('expenses',{'company_id':cid,'description':'Rent','category':'Fixed','incurred_on':'2026-09-18','amount':1000})
    summary=company_summary(db,cid,'monthly',date(2026,9,18))
    assert summary['totals']['operating']==1800
    assert company_summary(db,cid,'monthly',date(2026,8,18))['totals']['revenue']==0
    report=db.insert('report_history',{'company_id':cid,'period':'monthly','anchor':'2026-09-18','snapshot':summary,'created_by':user['id']})
    assert db.rows('report_history',cid,id='eq.'+report['id'])[0]['snapshot']==summary
    product=db.insert('products',{'company_id':cid,'name':'Test','category':'Test','sku':'sku','unit_cost':6000,'unit_price':10000})
    changed=db.request('PATCH','products',params={'id':'eq.'+product['id']},payload={'active':False})
    assert changed[0]['active'] is False
    schedule=db.insert('report_schedules',{'company_id':cid,'period':'monthly','recipient':user['email'],'created_by':user['id']})
    assert schedule['enabled'] is True

def test_inventory_bills_and_bank_import(database):
    user={'id':str(uuid4()),'email':'basic@example.test','email_confirmed_at':True}
    db=Session('',user)
    cid=db.insert('companies',{'name':'Basic control','owner_id':user['id']})['id']
    product=db.insert('products',{'company_id':cid,'name':'Mug','category':'Home','sku':'mug','unit_cost':1000,'unit_price':2000})
    movement={'company_id':cid,'product_id':product['id'],'occurred_on':'2026-09-18','direction':'in','quantity':5,'reference':'in-1','description':'Initial'}
    db.insert('stock_movements',movement)
    db.insert('stock_movements',{**movement,'direction':'out','quantity':2,'reference':'out-1'})
    with pytest.raises(HTTPException) as negative:
        db.insert('stock_movements',{**movement,'direction':'out','quantity':4,'reference':'out-2'})
    assert negative.value.status_code==422
    assert inventory(cid,db)[0]['balance']==3
    bill=db.insert('bills',{'company_id':cid,'reference':'rent','supplier':'Landlord','description':'Rent','category':'Fixed','incurred_on':'2026-09-01','due_on':'2026-09-10','amount':10000})
    payment={'company_id':cid,'bill_id':bill['id'],'reference':'paid-1','paid_on':'2026-09-10','amount':6000}
    db.insert('bill_payments',payment)
    assert payables(cid,db)[0]['balance']==4000
    with pytest.raises(HTTPException): db.insert('bill_payments',{**payment,'reference':'overpaid','amount':5000})
    db.insert('bill_payments',{**payment,'reference':'paid-2','amount':4000})
    assert payables(cid,db)[0]['status']=='paid'
    assert len(db.rows('expenses',cid))==1
    assert company_summary(db,cid,'monthly',date(2026,9,18))['totals']['expenses']==10000
    sale=db.insert('sales',{'company_id':cid,'external_id':'v1','sold_on':'2026-09-18','product':'Mug','category':'Home','quantity':1,'revenue':2000,'cmv':1000,'tax':100,'card':50,'commission':100,'installments':1})
    csv='reference,external_id,received_on,amount\nbank1,v1,2026-09-18,19.50\n'
    preview=bank_preview(db,cid,csv)
    assert preview['can_import'] and preview['rows'][0]['sale_id']==sale['id']
    db.request('POST','settlements',payload=[{**r,'company_id':cid} for r in preview['rows']])
    assert not bank_preview(db,cid,csv)['can_import']
    assert not bank_preview(db,cid,csv.replace('v1','unknown'))['can_import']
    other=Session('',{'id':str(uuid4()),'email':''})
    for table in ('stock_movements','bills','bill_payments'):
        assert other.rows(table,cid)==[]

def test_history_rls_and_composite_links(database):
    a=Session('',{'id':str(uuid4())});b=Session('',{'id':str(uuid4())})
    ca=a.insert('companies',{'name':'History A','owner_id':a.user['id']})['id']
    cb=b.insert('companies',{'name':'History B','owner_id':b.user['id']})['id']
    plan=a.insert('action_plans',{'company_id':ca,'title':'Review margin','priority':'high'})
    customer=a.insert('customers',{'company_id':ca,'name':'Customer A'})
    for table,values in [('plan_updates',{'plan_id':plan['id'],'message':'Reviewed'}),('customer_contacts',{'customer_id':customer['id'],'channel':'store','message':'Visited','response':'Will return'})]:
        a.insert(table,{'company_id':ca,**values})
        assert b.rows(table,ca)==[]
        with pytest.raises(HTTPException): b.insert(table,{'company_id':cb,**values})
        with pytest.raises(HTTPException): b.insert(table,{'company_id':ca,**values})
    assert b.rows('customers',ca)==[] and b.rows('action_plans',ca)==[]
    assert b.request('PATCH','action_plans',params={'id':'eq.'+plan['id']},payload={'status':'done'})==[]
    assert a.request('PATCH','action_plans',params={'id':'eq.'+plan['id']},payload={'status':'done'})[0]['status']=='done'
    expense={'company_id':ca,'external_id':'expense-1','description':'Import','category':'Test','incurred_on':'2026-09-22','amount':100}
    a.insert('expenses',expense)
    with pytest.raises(HTTPException): a.request('POST','expenses',payload=[{**expense,'external_id':'expense-2'},expense])
    assert not a.rows('expenses',ca,external_id='eq.expense-2')

def test_integrations_audit_and_company_backup_roundtrip(database):
    import base64,copy,gzip,json
    from backend.spreadsheets import Spreadsheet,import_sheet
    from backend.integrations import Mapping,save_mapping,overview
    from backend.company_backup import snapshot,encode_snapshot,record_backup
    from scripts.restore_company import restore_data
    a=Session('',{'id':str(uuid4())});b=Session('',{'id':str(uuid4())})
    cid=a.insert('companies',{'name':'Backup company','owner_id':a.user['id']})['id']
    other=b.insert('companies',{'name':'Other company','owner_id':b.user['id']})['id']
    source=a.insert('integration_sources',{'company_id':cid,'name':'ERP export','provider':'test','mode':'file'})
    mapping=Mapping(source_id=source['id'],kind='products',name='Daily export',mapping={k:k for k in ['sku','name','category','unit_cost','unit_price']})
    save_mapping(UUID(cid),mapping,a)
    with pytest.raises(HTTPException):save_mapping(UUID(other),mapping,b)
    data=Spreadsheet(kind='products',source_id=source['id'],filename='catalog.csv',content=base64.b64encode(b'sku,name,category,unit_cost,unit_price\nA,Test,General,1.00,2.00').decode())
    assert import_sheet(UUID(cid),'confirm',data,a)['imported']==1
    with pytest.raises(HTTPException):import_sheet(UUID(cid),'confirm',data,a)
    jobs=overview(UUID(cid),a)['jobs']
    assert len([j for j in jobs if j['status']=='imported'])==1
    assert len([j for j in jobs if j['status']=='rejected'])==1
    assert len(a.rows('source_records',cid))==1
    assert b.rows('source_records',cid)==[] and b.rows('import_jobs',cid)==[]
    assert b.rows('import_mappings',cid)==[] and b.rows('integration_sources',cid)==[]
    a.insert('bills',{'company_id':cid,'reference':'B1','supplier':'Landlord','description':'Rent','category':'Fixed','incurred_on':'2026-09-22','due_on':'2026-09-30','amount':1000})
    product=a.rows('products',cid)[0]
    for ref,direction in [('I','in'),('O','out')]:
        a.insert('stock_movements',{'company_id':cid,'product_id':product['id'],'occurred_on':'2026-09-22','direction':direction,'quantity':1,'reference':ref,'description':'Test'})
    original=snapshot(a,cid);content,checksum=encode_snapshot(original)
    assert json.loads(gzip.decompress(content))==original
    record_backup(a,original,checksum,'test.json.gz','download')
    assert b.rows('company_backups',cid)==[]
    with pytest.raises(HTTPException):snapshot(b,cid)
    restored=restore_data(original,UUID(cid))
    assert restored!=cid and b.rows('companies',id='eq.'+restored)==[]
    copy_snapshot=snapshot(a,restored)
    assert {t:len(r) for t,r in original['records'].items()}=={t:len(r) for t,r in copy_snapshot['records'].items()}
    assert a.rows('expenses',restored)[0]['amount']==1000
    assert inventory(UUID(restored),a)[0]['balance']==0
    assert a.rows('source_records',restored)[0]['record_id']==a.rows('products',restored)[0]['id']
    corrupted=copy.deepcopy(original);corrupted['records']['products'][0]['company_id']=other
    count=len(a.rows('companies'))
    with pytest.raises(ValueError):restore_data(corrupted,UUID(cid))
    assert len(a.rows('companies'))==count


def test_import_audit_rollback_on_late_conflict(database):
    from backend.spreadsheets import Spreadsheet,import_sheet
    import base64
    user={'id':str(uuid4())};db=Session('',user)
    cid=db.insert('companies',{'name':'Rollback','owner_id':user['id']})['id']
    db.insert('products',{'company_id':cid,'sku':'EXISTS','name':'Old','category':'C','unit_cost':100,'unit_price':200})
    # Simulate a conflict that arrives after the preflight lookup.
    class RacingSession(Session):
        def rows(self,table,*args,**kwargs):
            if table=='products':return []
            return super().rows(table,*args,**kwargs)
    racing=RacingSession('',user)
    content='sku,name,category,unit_cost,unit_price\nNEW,New,C,1,2\nEXISTS,Old,C,1,2'
    with pytest.raises(HTTPException):import_sheet(UUID(cid),'confirm',Spreadsheet(kind='products',filename='race.csv',content=base64.b64encode(content.encode()).decode()),racing)
    assert len(db.rows('products',cid))==1
    jobs=db.rows('import_jobs',cid)
    assert len(jobs)==1 and jobs[0]['status']=='rejected'

def test_catalog_details_and_customer_update_isolation(database):
    from backend.workspace import Customer, Product, update_record
    owner={'id':str(uuid4()),'email':'catalog@example.test'}
    db=Session('',owner)
    other=Session('',{'id':str(uuid4()),'email':'other@example.test'})
    cid=db.insert('companies',{'name':'Catalog','owner_id':owner['id']})['id']
    data=Customer(name='Cliente teste',document='123.456.789-00',pix_key='pix@example.test',address='Rua Um, 10',city='Manaus',notes='Prefere contato por telefone').model_dump()
    customer=db.insert('customers',{'company_id':cid,**data})
    result=update_record(UUID(cid),'customers',UUID(customer['id']),{**data,'city':'Belém'},db)
    assert result['city']=='Belém' and result['notes']==data['notes']
    assert other.request('PATCH','customers',params={'id':'eq.'+customer['id']},payload={'notes':'intrusion'})==[]
    assert other.rows('customers',cid)==[]
    assert db.rows('customers',cid)[0]['notes']==data['notes']
    product=db.insert('products',{'company_id':cid,**Product(name='Caneca',sku='C1',category='Casa',unit_cost=1000,unit_price=2000,notes='Embalagem individual').model_dump()})
    assert db.rows('products',cid)[0]['notes']==product['notes']
