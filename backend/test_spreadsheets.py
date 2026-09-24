import base64
import io
from datetime import datetime
from uuid import uuid4
import pytest
from openpyxl import Workbook
from fastapi import HTTPException
from backend.spreadsheets import Spreadsheet, parse_sheet, read_sheet, import_sheet


def payload(text,kind='products'):
    return Spreadsheet(kind=kind,filename='test.csv',content=base64.b64encode(text.encode()).decode())

def test_csv_mapping_locale_and_duplicates():
    data=payload('Código;Nome;Categoria;Custo;Preço\nA;Caneca;Casa;10,50;25,90\nA;Caneca;Casa;10,50;25,90')
    data.mapping={'sku':'Código','name':'Nome','category':'Categoria','unit_cost':'Custo','unit_price':'Preço'}
    rows,errors=parse_sheet(data)
    assert rows[0]['unit_cost']==1050 and rows[0]['unit_price']==2590
    assert errors[0]['line']==3

def test_xlsx_multiple_sheets_date_and_formula():
    book=Workbook();book.active.title='Produtos';sheet=book.create_sheet('Despesas')
    sheet.append(['external_id','description','category','incurred_on','amount'])
    sheet.append(['REF1','Aluguel','Fixa',datetime(2026,9,22),1500.50])
    out=io.BytesIO();book.save(out)
    data=Spreadsheet(kind='expenses',filename='test.xlsx',sheet='Despesas',content=base64.b64encode(out.getvalue()).decode())
    assert read_sheet(data)[2]==['Produtos','Despesas']
    rows,errors=parse_sheet(data)
    assert not errors and rows[0]['amount']==150050 and rows[0]['incurred_on']=='2026-09-22'
    sheet['E2']='=1+1';out=io.BytesIO();book.save(out);data.content=base64.b64encode(out.getvalue()).decode()
    with pytest.raises(HTTPException) as e: read_sheet(data)
    assert e.value.status_code==422

@pytest.mark.parametrize('text',[
 'sku,sku\nA,A',
 'sku,name,category,unit_cost,unit_price\nA,C,C,1,2,extra',
 'sku,name,category,unit_cost,unit_price\n'+('A,C,C,1,2\n'*1001)])
def test_invalid_shape_and_limit(text):
    with pytest.raises(HTTPException): read_sheet(payload(text))

def test_confirm_revalidates_and_blocks_existing_identifier():
    class DB:
        writes=0
        def company(self,cid): pass
        def rows(self,*args): return [{'sku':'A'}]
        def request(self,*args,**kwargs): self.writes+=1
        def insert(self,table,payload):
            assert table=='import_jobs' and payload['status']=='rejected'
    db=DB();data=payload('sku,name,category,unit_cost,unit_price\nA,Caneca,Casa,1.00,2.00')
    result=import_sheet(uuid4(),'preview',data,db)
    assert not result['can_import'] and result['duplicates']==['A']
    with pytest.raises(HTTPException): import_sheet(uuid4(),'confirm',data,db)
    assert db.writes==0


def test_import_rejects_extreme_exponent_before_integer_conversion():
    rows,errors=parse_sheet(payload('sku,name,category,unit_cost,unit_price\nA,C,C,1.00,1e1000000'))
    assert rows==[] and len(errors)==1
