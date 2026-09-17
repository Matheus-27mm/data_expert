from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.main import app
from backend.finance import demo_sales, summarize, period_bounds, simulate

client = TestClient(app)

def test_month_reconciles():
    data = summarize(demo_sales(), 'monthly', date(2026,8,31))
    t = data['totals']
    assert t['revenue'] == 15000000
    assert t['cmv'] == 10500000
    assert t['estimated'] == 4500000
    assert t['net'] == 1820000
    assert t['hidden'] == 2680000
    assert sum(p['net'] for p in data['products']) == t['net']
    assert sum(d['net'] for d in data['daily']) == t['net']
    assert len([p for p in data['products'] if p['net'] < 0]) == 3

def test_empty_and_daily():
    assert client.get('/api/dashboard?anchor=2027-01-01').json()['totals']['net'] == 0
    assert len(client.get('/api/dashboard?period=daily').json()['daily']) == 1
    assert len(client.get('/api/dashboard?period=weekly').json()['daily']) == 7
    assert period_bounds('weekly', date(2026,8,31)) == (date(2026,8,31),date(2026,9,6))
    assert period_bounds('monthly', date(2024,2,1))[1] == date(2024,2,29)

def test_daily_sums_equal_month():
    df = demo_sales()
    summed = sum(summarize(df,'daily',date(2026,8,d))['totals']['net'] for d in range(1,32))
    assert summed == summarize(df,'monthly',date(2026,8,1))['totals']['net']

def test_simulation_and_rounding():
    base = {'price':200,'cost':180,'installments':12}
    r = client.post('/api/simulate',json=base).json()
    assert r['net'] == -2350
    assert r['card_rate'] == 11.75
    assert r['price'] - r['cost'] - r['tax'] - r['card'] - r['commission'] == r['net']
    for field,value in [('price',0),('cost',-1),('installments',13),('price',200.001)]:
        assert client.post('/api/simulate',json={**base,field:value}).status_code == 422

def test_no_possible_breakeven():
    r = client.post('/api/simulate',json={'price':100,'cost':10,'installments':12,'tax_rate':50,'commission_rate':50}).json()
    assert r['breakeven'] is None

def test_report_and_validation():
    for period in ['daily','weekly','monthly']:
        r = client.get('/api/reports/pdf',params={'period':period})
        assert r.status_code == 200
        assert r.content.startswith(b'%PDF-')
        assert 'attachment' in r.headers['content-disposition']
    assert client.get('/api/dashboard?period=invalid').status_code == 422
    assert client.get('/api/dashboard?anchor=nope').status_code == 422
