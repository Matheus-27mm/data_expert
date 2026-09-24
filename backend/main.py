from datetime import date
import os
from decimal import Decimal
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .finance import demo_sales, summarize, simulate
from .report import report_pdf
from .workspace import router as workspace_router
from . import integrations, company_backup, trading
from . import spreadsheets  # register spreadsheet routes before mounting
from .observability import request_log
from .security import SecurityMiddleware

api_docs = os.getenv('ENABLE_API_DOCS') == '1'
app = FastAPI(title='Lucra API', version='1.0.0', docs_url='/api/docs' if api_docs else None, redoc_url='/api/redoc' if api_docs else None, openapi_url='/api/openapi.json' if api_docs else None)
app.middleware('http')(request_log)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['GET','POST','PATCH'], allow_headers=['Content-Type','Authorization'])
app.add_middleware(SecurityMiddleware)
sales = demo_sales()
app.include_router(workspace_router)

@app.get('/api/config')
def configuration():
    url = os.getenv('NEON_AUTH_URL','')
    return {'configured':bool(url and os.getenv('DATABASE_URL')),'neon_auth_url':url}

class Simulation(BaseModel):
    price: Decimal = Field(gt=0, le=10000000, max_digits=12, decimal_places=2)
    cost: Decimal = Field(ge=0, le=10000000, max_digits=12, decimal_places=2)
    installments: int = Field(ge=1, le=12)
    tax_rate: Decimal = Field(default=Decimal('6'), ge=0, le=50)
    commission_rate: Decimal = Field(default=Decimal('4'), ge=0, le=50)
    card_base: Decimal = Field(default=Decimal('2'), ge=0, le=50)
    anticipation_rate: Decimal = Field(default=Decimal('1.5'), ge=0, le=20)

@app.get('/api/health')
def health():
    return {'status':'ok','mode':'neon' if os.getenv('DATABASE_URL') else 'demo'}

@app.get('/api/ready')
def readiness():
    if not os.getenv('DATABASE_URL'):
        return {'status':'ok','mode':'demo'}
    import psycopg
    from fastapi.responses import JSONResponse
    try:
        with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=5) as conn:
            applied={r[0] for r in conn.execute('select name from public.lucra_migrations').fetchall()}
        if not {'001_initial.sql','002_workspace.sql','003_inventory_payables.sql','004_business_history.sql','005_integrations_backups.sql','006_catalog_details.sql','007_import_options.sql','008_integrated_sales.sql'}<=applied:
            return JSONResponse({'status':'unavailable'},status_code=503)
        return {'status':'ok','mode':'neon'}
    except psycopg.Error:
        return JSONResponse({'status':'unavailable'},status_code=503)

@app.get('/api/dashboard')
def dashboard(period: Literal['daily','weekly','monthly']='monthly', anchor: date=date(2026,8,31)):
    return summarize(sales, period, anchor)

@app.post('/api/simulate')
def simulation(body: Simulation):
    return simulate(**body.model_dump())

@app.get('/api/reports/pdf')
def download_report(period: Literal['daily','weekly','monthly']='monthly', anchor: date=date(2026,8,31)):
    content = report_pdf(summarize(sales, period, anchor))
    return Response(content, media_type='application/pdf', headers={'Content-Disposition':f'attachment; filename="lucra-{period}-{anchor}.pdf"'})

# Docker serves the compiled React app on the same origin as its API.
# Vercel serves dist through its CDN and leaves this environment variable unset.
if static_dir := os.environ.get('STATIC_DIR'):
    app.mount('/', StaticFiles(directory=static_dir, html=True), name='frontend')
