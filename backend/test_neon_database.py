"""Integration tests: set NEON_TEST_DATABASE_URL to a disposable PostgreSQL database."""
import os
from pathlib import Path
from uuid import uuid4
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
