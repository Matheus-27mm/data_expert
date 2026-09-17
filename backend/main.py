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

app = FastAPI(title='Lucra API', version='1.0.0', docs_url='/api/docs', redoc_url='/api/redoc', openapi_url='/api/openapi.json')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['GET','POST'], allow_headers=['Content-Type'])
sales = demo_sales()

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
    return {'status':'ok','mode':'demo'}

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
