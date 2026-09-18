from copy import deepcopy
from datetime import date
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.main import app
from backend.workspace import session, parse_csv, company_summary
from scripts.report_worker import due_anchor

CID='11111111-1111-4111-8111-111111111111'
OTHER='22222222-2222-4222-8222-222222222222'
SALE='33333333-3333-4333-8333-333333333333'
CSV='external_id,sold_on,product,category,quantity,revenue,cmv,tax,card,commission,installments\nv1,2026-09-18,Produto,Loja,1,200.00,140.00,12.00,23.50,8.00,12\n'

class FakeDB:
    user={'id':'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','email':'owner@example.com','email_confirmed_at':'2026-01-01'}
    def __init__(self):
        self.tables={t:[] for t in ['products','expenses','adjustments','settlements','payment_terms','report_history','report_schedules']}
        self.tables['companies']=[{'id':CID,'name':'Empresa & Filhos','owner_id':self.user['id']}]
        sale=parse_csv(CSV)[0][0]
        self.tables['sales']=[dict(sale,id=SALE,company_id=CID)]
    def company(self,cid):
        if cid!=CID:raise HTTPException(404,'Sem acesso')
        return self.tables['companies'][0]
    def rows(self,table,company_id=None,**filters):
        rows=deepcopy(self.tables[table])
        if company_id:rows=[r for r in rows if r.get('company_id')==company_id]
        for key,value in filters.items():
            if key in ('id','external_id'):rows=[r for r in rows if r.get(key)==value[3:]]
        return rows
    def insert(self,table,payload):
        row={**payload,'id':str(uuid4()),'created_at':'2026-09-18T12:00:00Z'}
        self.tables[table].append(row)
        return row
    def request(self,method,path,params=None,payload=None,prefer=None):
        if method=='POST' and path=='sales':
            existing={s['external_id'] for s in self.tables['sales']}
            if any(s['external_id'] in existing for s in payload):raise HTTPException(409,'Duplicado')
            self.tables['sales'].extend(deepcopy(payload))
            return None
        raise AssertionError('Unexpected request')

@pytest.fixture
def workspace():
    db=FakeDB()
    app.dependency_overrides[session]=lambda:db
    try:yield TestClient(app),db
    finally:app.dependency_overrides.clear()

def test_auth_is_required(monkeypatch):
    monkeypatch.setenv('NEON_AUTH_URL','https://example.neonauth.test/auth')
    monkeypatch.setenv('DATABASE_URL','postgresql://test')
    assert TestClient(app).get('/api/workspace/companies').status_code==401

def test_unconfigured_is_not_silently_demo(monkeypatch):
    monkeypatch.delenv('NEON_AUTH_URL',raising=False)
    assert TestClient(app).get('/api/workspace/companies').status_code==503

def test_other_company_not_accessible(workspace):
    client,db=workspace
    for endpoint in ['dashboard','records/sales','reports','reconciliation']:
        assert client.get(f'/api/workspace/{OTHER}/{endpoint}').status_code==404
    assert client.post(f'/api/workspace/{OTHER}/imports/confirm',json={'content':CSV}).status_code==404

def test_csv_exact_cents_and_validation():
    rows,errors=parse_csv(CSV)
    assert not errors and rows[0]['card']==2350
    for bad in ['NaN','Infinity','1.001','-1']:
        assert parse_csv(CSV.replace('200.00',bad))[1]
    assert parse_csv(CSV+CSV.splitlines()[1]+'\n')[1]
    with pytest.raises(HTTPException):parse_csv('bad,header\n1,2')

def test_import_duplicate_and_atomic_commit(workspace):
    client,db=workspace
    preview=client.post(f'/api/workspace/{CID}/imports/preview',json={'content':CSV}).json()
    assert preview['duplicates']==['v1'] and not preview['can_import']
    assert client.post(f'/api/workspace/{CID}/imports/confirm',json={'content':CSV}).status_code==409
    assert len(db.tables['sales'])==1
    new=CSV.replace('v1,','v2,')
    assert client.post(f'/api/workspace/{CID}/imports/confirm',json={'content':new}).json()=={'imported':1}

def test_operating_result_refunds_expenses(workspace):
    client,db=workspace
    db.tables['expenses']=[{'company_id':CID,'amount':500}]
    db.tables['adjustments']=[{'company_id':CID,'amount':2000,'cost_recovered':1400}]
    result=company_summary(db,CID,'monthly',date(2026,9,18))
    assert result['totals']['net']==1650
    assert result['totals']['operating']==550
    assert result['company']=='Empresa & Filhos'

def test_report_snapshot_does_not_change(workspace):
    client,db=workspace
    report=client.post(f'/api/workspace/{CID}/reports',json={'period':'monthly','anchor':'2026-09-18'}).json()
    db.tables['sales'].clear()
    assert report['snapshot']['totals']['revenue']==20000
    response=client.get(f'/api/workspace/{CID}/reports/{report["id"]}/pdf')
    assert response.status_code==200 and response.content.startswith(b'%PDF-')

def test_financial_records_immutable_and_unknown_fields_rejected(workspace):
    client,db=workspace
    assert client.patch(f'/api/workspace/{CID}/records/sales/{SALE}',json={}).status_code==405
    assert client.post(f'/api/workspace/{CID}/records/expenses',json={'description':'x','category':'x','incurred_on':'2026-09-18','amount':100,'company_id':OTHER}).status_code==422

def test_report_recipient_bound_to_verified_user(workspace):
    client,db=workspace
    r=client.post(f'/api/workspace/{CID}/records/report_schedules',json={'period':'weekly'})
    assert r.status_code==201
    assert r.json()['recipient']==db.user['email']
    assert client.post(f'/api/workspace/{CID}/records/report_schedules',json={'period':'weekly','recipient':'other@example.com'}).status_code==422

def test_reconciliation(workspace):
    client,db=workspace
    db.tables['settlements']=[{'company_id':CID,'sale_id':SALE,'amount':17650}]
    result=client.get(f'/api/workspace/{CID}/reconciliation').json()[0]
    assert result['expected']==17650 and result['status']=='reconciled'

def test_schedule_closed_period():
    assert due_anchor('daily',date(2026,9,18))==date(2026,9,17)
    assert due_anchor('weekly',date(2026,9,21))==date(2026,9,20)
    assert due_anchor('weekly',date(2026,9,18)) is None
    assert due_anchor('monthly',date(2026,10,1))==date(2026,9,30)
