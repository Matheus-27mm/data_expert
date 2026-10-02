"""Authenticated company workspace. Every database request preserves PostgreSQL RLS."""
import csv
import io
import os
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from .finance import summarize, period_bounds
from .report import report_pdf

router = APIRouter(prefix='/api/workspace')
MONEY_MAX = 1_000_000_000_000
COLS = ['sold_on','product','category','quantity','revenue','cmv','tax','card','commission','installments']
Period = Literal['daily','weekly','monthly']

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Company(Input):
    name: str = Field(min_length=2,max_length=120)

class Product(Input):
    name: str = Field(min_length=1,max_length=120)
    category: str = Field(min_length=1,max_length=80)
    sku: str = Field(min_length=1,max_length=80)
    unit_cost: int = Field(ge=0,le=MONEY_MAX)
    unit_price: int = Field(gt=0,le=MONEY_MAX)
    active: bool = True
    notes: str = Field(default="",max_length=4000)

class Sale(Input):
    external_id: str = Field(min_length=1,max_length=120)
    sold_on: date
    product: str = Field(min_length=1,max_length=120)
    category: str = Field(min_length=1,max_length=80)
    quantity: int = Field(gt=0,le=1000000)
    revenue: int = Field(ge=0,le=MONEY_MAX)
    cmv: int = Field(ge=0,le=MONEY_MAX)
    tax: int = Field(ge=0,le=MONEY_MAX)
    card: int = Field(ge=0,le=MONEY_MAX)
    commission: int = Field(ge=0,le=MONEY_MAX)
    installments: int = Field(ge=1,le=12)

class Expense(Input):
    description: str = Field(min_length=1,max_length=200)
    category: str = Field(min_length=1,max_length=80)
    incurred_on: date
    amount: int = Field(gt=0,le=MONEY_MAX)

class Adjustment(Input):
    sale_id: UUID
    occurred_on: date
    kind: Literal['refund','chargeback']
    amount: int = Field(gt=0,le=MONEY_MAX)
    cost_recovered: int = Field(default=0,ge=0,le=MONEY_MAX)
    description: str = Field(min_length=1,max_length=200)

class Settlement(Input):
    sale_id: UUID
    reference: str = Field(min_length=1,max_length=120)
    received_on: date
    amount: int = Field(gt=0,le=MONEY_MAX)

class Terms(Input):
    name: str = Field(min_length=1,max_length=120)
    installments: int = Field(ge=1,le=12)
    tax_rate: Decimal = Field(ge=0,le=50)
    commission_rate: Decimal = Field(ge=0,le=50)
    card_base: Decimal = Field(ge=0,le=50)
    anticipation_rate: Decimal = Field(ge=0,le=20)

class CSVInput(Input):
    content: str = Field(min_length=1,max_length=2_000_000)

class ReportInput(Input):
    period: Period
    anchor: date

class Schedule(Input):
    period: Period
    enabled: bool = True

class StockMovement(Input):
    product_id: UUID
    occurred_on: date
    direction: Literal['in','out']
    quantity: int = Field(gt=0,le=1000000)
    reference: str = Field(min_length=1,max_length=120)
    description: str = Field(min_length=1,max_length=200)

class Bill(Input):
    reference: str = Field(min_length=1,max_length=120)
    supplier: str = Field(min_length=1,max_length=120)
    description: str = Field(min_length=1,max_length=200)
    category: str = Field(min_length=1,max_length=80)
    incurred_on: date
    due_on: date
    amount: int = Field(gt=0,le=MONEY_MAX)

class BillPayment(Input):
    bill_id: UUID
    reference: str = Field(min_length=1,max_length=120)
    paid_on: date
    amount: int = Field(gt=0,le=MONEY_MAX)

from .neon_repository import Session
from .neon_auth import session

def company_summary(db, company_id, period, anchor):
    with db.transaction(snapshot=True) as db:
        company = db.company(company_id)
        start,end = period_bounds(period,anchor)
        dates = f'(sold_on.gte.{start},sold_on.lte.{end})'
        sales = db.rows('sales',company_id,**{'and':dates})
        result = summarize(pd.DataFrame(sales,columns=COLS),period,anchor)
        expenses = db.rows('expenses',company_id,**{'and':f'(incurred_on.gte.{start},incurred_on.lte.{end})'})
        adjustments = db.rows('adjustments',company_id,**{'and':f'(occurred_on.gte.{start},occurred_on.lte.{end})'})
        t = result['totals']
        t['expenses'] = sum(r['amount'] for r in expenses)
        t['refunds'] = sum(r['amount'] for r in adjustments)
        t['cost_recovered'] = sum(r['cost_recovered'] for r in adjustments)
        t['operating'] = t['net'] - t['expenses'] - t['refunds'] + t['cost_recovered']
        t['operating_margin'] = round(t['operating']/t['revenue']*100,2) if t['revenue'] else 0
        result.update(company=company['name'],source='neon')
        return result

@router.get('/companies')
def companies(db: Session = Depends(session)):
    return db.rows('companies')

@router.post('/companies',status_code=201)
def create_company(body: Company,db: Session=Depends(session)):
    return db.insert('companies',{'name':body.name,'owner_id':db.user['id']})

@router.get('/{company_id}/dashboard')
def dashboard(company_id: UUID,period: Period='monthly',anchor: date | None=None,db: Session=Depends(session)):
    return company_summary(db,str(company_id),period,anchor or date.today())

class ActionPlan(Input):
    title: str = Field(min_length=2,max_length=160)
    description: str = Field(default='',max_length=4000)
    priority: Literal['high','medium','low'] = 'medium'
    status: Literal['pending','progress','done'] = 'pending'
    due_on: date | None = None

class PlanUpdate(Input):
    plan_id: UUID
    message: str = Field(min_length=1,max_length=4000)

class Customer(Input):
    name: str = Field(min_length=2,max_length=160)
    email: str = Field(default='',max_length=254)
    phone: str = Field(default='',max_length=40)
    document: str = Field(default='',max_length=30)
    pix_key: str = Field(default='',max_length=254)
    address: str = Field(default='',max_length=300)
    city: str = Field(default='',max_length=120)
    notes: str = Field(default='',max_length=4000)

class CustomerContact(Input):
    customer_id: UUID
    channel: Literal['phone','email','whatsapp','store','other']
    message: str = Field(min_length=1,max_length=4000)
    response: str = Field(default='',max_length=4000)
    next_on: date | None = None

TABLES = {'action_plans':ActionPlan,'plan_updates':PlanUpdate,'customers':Customer,'customer_contacts':CustomerContact,'products':Product,'sales':Sale,'expenses':Expense,'adjustments':Adjustment,
          'settlements':Settlement,'payment_terms':Terms,'report_schedules':Schedule,
          'stock_movements':StockMovement,'bills':Bill,'bill_payments':BillPayment}

@router.get('/{company_id}/records/{table}')
def records(company_id:UUID, table:str, db:Session=Depends(session)):
    if table not in TABLES:
        raise HTTPException(404,'Cadastro não encontrado.')
    db.company(str(company_id))
    return db.rows(table,str(company_id))

@router.post('/{company_id}/records/{table}',status_code=201)
def create_record(company_id:UUID,table:str,body:dict,db:Session=Depends(session)):
    from pydantic import ValidationError
    if table not in TABLES:
        raise HTTPException(404,'Cadastro não encontrado.')
    db.company(str(company_id))
    try:
        values = TABLES[table].model_validate(body).model_dump(mode='json')
    except ValidationError as error:
        raise HTTPException(422, str(error))
    values['company_id'] = str(company_id)
    if table in ('adjustments','settlements'):
        linked_sales=db.rows('sales',str(company_id),id=f"eq.{values['sale_id']}")
        if not linked_sales:
            raise HTTPException(404,'Venda não encontrada nesta empresa.')
        if table=='adjustments' and linked_sales[0].get('product_id'):
            raise HTTPException(422,'Para esta venda, use Devolver na página de Vendas. Assim o estoque também será conferido.')
    if table == 'report_schedules':
        # Delivery can only go to the authenticated, confirmed account email.
        if not db.user.get('email_confirmed_at'):
            raise HTTPException(403,'Confirme seu e-mail antes de agendar relatórios.')
        values.update(recipient=db.user['email'],created_by=db.user['id'])
    return db.insert(table,values)

@router.patch('/{company_id}/records/{table}/{record_id}')
def update_record(company_id:UUID,table:str,record_id:UUID,body:dict,db:Session=Depends(session)):
    from pydantic import ValidationError
    if table not in ('products','payment_terms','report_schedules','action_plans','customers'):
        raise HTTPException(405,'Lançamentos financeiros são imutáveis. Registre um ajuste.')
    db.company(str(company_id))
    try:
        values = TABLES[table].model_validate(body).model_dump(mode='json')
    except ValidationError as error:
        raise HTTPException(422,str(error))
    rows = db.request('PATCH',table,params={'company_id':f'eq.{company_id}','id':f'eq.{record_id}'},payload=values,prefer='return=representation')
    if not rows:
        raise HTTPException(404,'Registro não encontrado.')
    return rows[0]

# Full-history balances are aggregated in PostgreSQL (one round trip, grouped
# per entity) instead of loading every ledger row into Python.
SETTLED = """left join (select sale_id,sum(amount)::bigint received from public.settlements where company_id=%(cid)s group by sale_id) st on st.sale_id=s.id
left join (select sale_id,sum(amount)::bigint refunds,sum(returned_quantity)::bigint returned from public.adjustments where company_id=%(cid)s group by sale_id) a on a.sale_id=s.id"""

@router.get('/{company_id}/reconciliation')
def reconciliation(company_id:UUID,db:Session=Depends(session)):
    cid=str(company_id);db.company(cid)
    rows=db.query("select s.id,s.external_id,s.product,s.revenue,s.card,coalesce(st.received,0) received,coalesce(a.refunds,0) refunds from public.sales s "+SETTLED+" where s.company_id=%(cid)s order by s.id",{'cid':cid})
    result=[]
    for r in rows:
        expected=r['revenue']-r['card']-r['refunds']
        result.append({'id':r['id'],'external_id':r['external_id'],'product':r['product'],'expected':expected,'received':r['received'],
                       'difference':r['received']-expected,'status':'reconciled' if r['received']==expected else 'pending' if r['received']<expected else 'excess'})
    return result

@router.get('/{company_id}/inventory')
def inventory(company_id:UUID,db:Session=Depends(session)):
    cid=str(company_id);db.company(cid)
    return db.query("""select p.*,coalesce(m.balance,0) balance from public.products p
left join (select product_id,sum(case direction when 'in' then quantity else -quantity end)::bigint balance from public.stock_movements where company_id=%(cid)s group by product_id) m on m.product_id=p.id
where p.company_id=%(cid)s order by p.id""",{'cid':cid})

@router.get('/{company_id}/payables')
def payables(company_id:UUID,db:Session=Depends(session)):
    cid=str(company_id);db.company(cid)
    rows=db.query("""select b.*,coalesce(p.paid,0) paid from public.bills b
left join (select bill_id,sum(amount)::bigint paid from public.bill_payments where company_id=%(cid)s group by bill_id) p on p.bill_id=b.id
where b.company_id=%(cid)s order by b.due_on,b.id""",{'cid':cid})
    today=str(date.today())
    return [{**b,'balance':b['amount']-b['paid'],'status':'paid' if b['amount']==b['paid'] else 'overdue' if b['due_on']<today else 'pending'} for b in rows]

def bank_preview(db,cid,content):
    """Map bank credits to sales by external ID; never guess ambiguous matches."""
    reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if set(reader.fieldnames or [])!={'reference','external_id','received_on','amount'}:
        raise HTTPException(422,'Cabeçalho: reference,external_id,received_on,amount')
    sales={s['external_id']:s for s in db.rows('sales',cid)}
    existing={p['reference'] for p in db.rows('settlements',cid)}
    rows,errors,seen=[],[],set()
    for line,row in enumerate(reader,start=2):
        if line>1001: raise HTTPException(413,'Máximo de 1.000 créditos por arquivo.')
        try:
            if None in row or not sales.get(row['external_id']): raise ValueError()
            value=Decimal(row['amount'])
            if not value.is_finite() or value<=0 or value>MONEY_MAX/100 or value.as_tuple().exponent < -2: raise ValueError()
            payment=Settlement.model_validate({'sale_id':sales[row['external_id']]['id'],
                'reference':row['reference'],'received_on':row['received_on'],'amount':int(value*100)}).model_dump(mode='json')
            if payment['reference'] in existing or payment['reference'] in seen: raise ValueError()
            seen.add(payment['reference'])
            rows.append(payment)
        except (ValueError,TypeError,InvalidOperation,KeyError):
            errors.append({'line':line,'message':'Crédito inválido, referência duplicada ou venda não encontrada.'})
    if not rows and not errors: errors.append({'line':2,'message':'Arquivo sem créditos.'})
    return {'rows':rows,'errors':errors,'duplicates':[],'can_import':bool(rows) and not errors}

@router.post('/{company_id}/bank-imports/preview')
def preview_bank(company_id:UUID,body:CSVInput,db:Session=Depends(session)):
    db.company(str(company_id))
    return bank_preview(db,str(company_id),body.content)

@router.post('/{company_id}/bank-imports/confirm')
def confirm_bank(company_id:UUID,body:CSVInput,db:Session=Depends(session)):
    cid=str(company_id)
    db.company(cid)
    preview=bank_preview(db,cid,body.content)
    if not preview['can_import']: raise HTTPException(422,preview['errors'])
    db.request('POST','settlements',payload=[{**r,'company_id':cid} for r in preview['rows']])
    return {'imported':len(preview['rows'])}

@router.post('/{company_id}/reports',status_code=201)
def create_report(company_id:UUID,body:ReportInput,db:Session=Depends(session)):
    snapshot = company_summary(db,str(company_id),body.period,body.anchor)
    return db.insert('report_history',{'company_id':str(company_id),'period':body.period,
        'anchor':str(body.anchor),'snapshot':snapshot,'created_by':db.user['id']})

@router.get('/{company_id}/reports')
def history(company_id:UUID,db:Session=Depends(session)):
    db.company(str(company_id))
    return db.rows('report_history',str(company_id),select='id,period,anchor,created_at',order='created_at.desc')

@router.get('/{company_id}/reports/{report_id}/pdf')
def download(company_id:UUID,report_id:UUID,db:Session=Depends(session)):
    db.company(str(company_id))
    rows = db.rows('report_history',str(company_id),id=f'eq.{report_id}')
    if not rows:
        raise HTTPException(404,'Relatório não encontrado.')
    return Response(report_pdf(rows[0]['snapshot']),media_type='application/pdf',headers={
        'Content-Disposition':f'attachment; filename="sobrevo-{rows[0]["period"]}-{rows[0]["anchor"]}.pdf"'})
