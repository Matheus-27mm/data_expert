import os
from uuid import uuid4,UUID
from datetime import date
import pytest
from fastapi import HTTPException
from backend.neon_repository import Session
from backend.trading import Checkout,Line,checkout,return_sale,Return,receivables,limits,StockLimits,export_inventory,sale_quote
from backend.workspace import inventory,create_record

@pytest.fixture
def store():
    url=os.getenv('NEON_TEST_DATABASE_URL')
    if not url:pytest.skip('Disposable PostgreSQL required')
    old=os.environ.get('DATABASE_URL');os.environ['DATABASE_URL']=url
    from scripts.migrate import main
    main()
    db=Session('',{'id':str(uuid4())})
    c=db.insert('companies',{'name':'Loja teste integrada','owner_id':db.user['id']});cid=UUID(c['id'])
    p=db.insert('products',{'company_id':str(cid),'name':'Camiseta','sku':'P1','category':'Roupas','unit_cost':2000,'unit_price':5990})
    db.insert('stock_movements',{'company_id':str(cid),'product_id':p['id'],'occurred_on':'2026-01-01','direction':'in','quantity':10,'reference':'initial','description':'Inicial'})
    yield db,cid,p
    if old is None:os.environ.pop('DATABASE_URL',None)
    else:os.environ['DATABASE_URL']=old

def order(p,**extra):
    return Checkout(reference=uuid4(),sold_on=date(2026,1,31),first_due_on=date(2026,1,31),lines=[Line(product_id=UUID(p['id']),quantity=2)],installments=3,**extra)

def test_checkout_snapshots_stock_receivables_and_returns(store):
    db,cid,p=store;body=order(p)
    result=checkout(cid,body,db);sid=UUID(result['sales'][0]['id'])
    assert inventory(cid,db)[0]['balance']==8
    with pytest.raises(HTTPException) as dup:checkout(cid,body,db)
    assert dup.value.status_code==409 and inventory(cid,db)[0]['balance']==8
    db.request('PATCH','products',params={'id':'eq.'+p['id']},payload={'unit_cost':3000,'unit_price':7000})
    row=receivables(cid,db)[0]
    assert row['cmv']==4000 and row['revenue']==11980
    assert [x['due_on'] for x in row['parts']]==['2026-01-31','2026-02-28','2026-03-31']
    assert sum(x['amount'] for x in row['parts'])==11980
    create_record(cid,'settlements',{'sale_id':str(sid),'reference':'receipt','received_on':'2026-02-01','amount':3000},db)
    with pytest.raises(HTTPException):create_record(cid,'settlements',{'sale_id':str(sid),'reference':'excess','received_on':'2026-02-01','amount':12000},db)
    ret=Return(reference=uuid4(),quantity=1,occurred_on=date(2026,2,1),description='Devolução')
    return_sale(cid,sid,ret,db)
    assert inventory(cid,db)[0]['balance']==9
    assert receivables(cid,db)[0]['balance']==2990
    with pytest.raises(HTTPException):return_sale(cid,sid,ret,db)
    with pytest.raises(HTTPException):return_sale(cid,sid,Return(reference=uuid4(),quantity=2,occurred_on=date(2026,2,1),description='Excesso'),db)
    assert inventory(cid,db)[0]['balance']==9

def test_checkout_rollback_and_tenant_isolation(store):
    db,cid,p=store;body=order(p);body.lines.append(Line(product_id=UUID(p['id']),quantity=20))
    with pytest.raises(HTTPException):checkout(cid,body,db)
    assert not db.rows('sales',str(cid)) and inventory(cid,db)[0]['balance']==10
    other=Session('',{'id':str(uuid4())})
    with pytest.raises(HTTPException):checkout(cid,order(p),other)
    c=other.insert('companies',{'name':'Outra loja','owner_id':other.user['id']})
    with pytest.raises(HTTPException):checkout(UUID(c['id']),order(p),other)

def test_terms_limits_and_exports(store):
    db,cid,p=store
    t=db.insert('payment_terms',{'company_id':str(cid),'name':'Cartão','installments':2,'tax_rate':6,'commission_rate':4,'card_base':2,'anticipation_rate':0})
    body=order(p,terms_id=UUID(t['id']),received=True)
    q=sale_quote(cid,body,db)
    assert q['totals']['revenue']==11980 and q['rows'][0]['installments']==2
    checkout(cid,body,db)
    assert receivables(cid,db)[0]['balance']==0
    limits(cid,UUID(p['id']),StockLimits(min_stock=9,max_stock=20),db)
    assert inventory(cid,db)[0]['min_stock']==9
    assert export_inventory(cid,'xlsx',db).body.startswith(b'PK')
    assert export_inventory(cid,'pdf',db).body.startswith(b'%PDF')

def test_concurrent_checkouts_cannot_oversell(store):
    from concurrent.futures import ThreadPoolExecutor
    db,cid,p=store
    def buy():
        body=order(p);body.lines=[Line(product_id=UUID(p['id']),quantity=6)]
        try:
            checkout(cid,body,db)
            return True
        except HTTPException as e:
            assert e.status_code==422
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(lambda _:buy(),range(2)))
    assert sum(results)==1
    assert inventory(cid,db)[0]['balance']==4
    assert len(db.rows('sales',str(cid)))==1
