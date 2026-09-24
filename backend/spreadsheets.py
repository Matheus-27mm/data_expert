"""Bounded, preview-first spreadsheet imports; all writes use the tenant RLS session."""
import hashlib
import base64
import binascii
import csv
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Depends, HTTPException
from pydantic import Field
from .workspace import router, Input, Product, Sale, Expense, Session, session, MONEY_MAX

class ExpenseImport(Expense):
    external_id: str = Field(min_length=1,max_length=120)

MODELS = {'products':Product,'sales':Sale,'expenses':ExpenseImport}
MONEY = {'unit_cost','unit_price','revenue','cmv','tax','card','commission','amount'}

class Spreadsheet(Input):
    kind: str
    source_id: UUID | None = None
    filename: str = Field(max_length=180)
    content: str = Field(max_length=2800000)
    sheet: str | None = None
    mapping: dict[str,str] = Field(default_factory=dict)


def read_sheet(body):
    if body.kind not in MODELS:
        raise HTTPException(422,'Escolha produtos, vendas ou despesas.')
    try:
        raw=base64.b64decode(body.content,validate=True)
        if len(raw)>2000000: raise ValueError('Arquivo maior que 2 MB.')
        sheets=[]
        if body.filename.lower().endswith('.xlsx'):
            from openpyxl import load_workbook
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if sum(f.file_size for f in archive.infolist())>20000000 or len(archive.infolist())>200:
                    raise ValueError('Planilha muito grande quando descompactada.')
            book=load_workbook(io.BytesIO(raw),read_only=True,data_only=False,keep_links=False)
            try:
                sheets=book.sheetnames
                sheet=book[body.sheet or sheets[0]]
                sheet.reset_dimensions()
                data=[]
                for index,row in enumerate(sheet.iter_rows(max_col=41)):
                    if index>1000: raise ValueError("Limite de 1.000 linhas após o cabeçalho.")
                    if any(c.data_type=='f' for c in row):
                        raise ValueError('Exporte as fórmulas como valores antes de importar.')
                    values=[c.value for c in row]
                    while values and values[-1] is None: values.pop()
                    if any(v is not None for v in values): data.append(values)
            finally: book.close()
        elif body.filename.lower().endswith('.csv'):
            text=raw.decode('utf-8-sig')
            try: dialect=csv.Sniffer().sniff(text[:4096],delimiters=',;\t')
            except csv.Error: dialect=csv.excel
            data=[]
            for row in csv.reader(io.StringIO(text),dialect):
                if any(v.strip() for v in row): data.append(row)
                if len(data)>1001: break
        else: raise ValueError('Use CSV UTF-8 ou Excel .xlsx.')
        if len(data)<2: raise ValueError('Arquivo sem registros.')
        if len(data)>1001: raise ValueError('Limite de 1.000 registros por arquivo.')
        headers=[str(v or '').strip() for v in data[0]]
        if len(headers)>40 or not all(headers) or len(set(headers))!=len(headers):
            raise ValueError('Use até 40 colunas, com cabeçalhos únicos e preenchidos.')
        if any(len(r)>len(headers) for r in data[1:]): raise ValueError('Há linhas com mais colunas que o cabeçalho.')
        rows=[dict(zip(headers,r)) for r in data[1:]]
        return headers,rows,sheets
    except (ValueError,KeyError,IndexError,UnicodeError,zipfile.BadZipFile,binascii.Error,csv.Error) as e:
        raise HTTPException(422,str(e))
    except Exception:
        raise HTTPException(422,'Não foi possível ler o arquivo. Confira se é um CSV UTF-8 ou XLSX válido.') from None


def parse_sheet(body):
    headers,rows,sheets=read_sheet(body)
    model=MODELS[body.kind]
    mapping=body.mapping or {k:k for k in model.model_fields if k in headers}
    if any(k not in model.model_fields or v not in headers for k,v in mapping.items()):
        raise HTTPException(422,'Mapeamento de colunas inválido.')
    parsed,errors,seen=[],[],set()
    identity='sku' if body.kind=='products' else 'external_id'
    for number,row in enumerate(rows,2):
        try:
            values={k:row.get(v) for k,v in mapping.items()}
            for k,v in list(values.items()):
                if k in MONEY:
                    text=str(v).strip().replace('R$','').replace(' ','')
                    if ',' in text: text=text.replace('.','').replace(',','.')
                    amount=Decimal(text)
                    if not amount.is_finite() or amount<0 or amount>MONEY_MAX/100 or amount.as_tuple().exponent < -2: raise ValueError('Valor monetário inválido.')
                    values[k]=int(amount*100)
                if k.endswith('_on'):
                    if isinstance(v,datetime): values[k]=v.date().isoformat()
                    elif isinstance(v,date): values[k]=v.isoformat()
                    elif '/' in str(v): values[k]=datetime.strptime(str(v),'%d/%m/%Y').date().isoformat()
            record=model.model_validate(values).model_dump(mode='json')
            if record[identity] in seen: raise ValueError('Identificador repetido neste arquivo.')
            seen.add(record[identity]);parsed.append(record)
        except (ValueError,TypeError,ArithmeticError):
            errors.append({'line':number,'message':'Confira os campos obrigatórios, datas, valores e identificador único.'})
    return parsed,errors

@router.post('/{company_id}/spreadsheets/read')
def inspect(company_id:UUID,body:Spreadsheet,db:Session=Depends(session)):
    db.company(str(company_id))
    headers,rows,sheets=read_sheet(body)
    return {'headers':headers,'sample':rows[:5],'sheets':sheets,'count':len(rows),
            'fields':[{'key':k,'required':v.is_required()} for k,v in MODELS[body.kind].model_fields.items()]}

@router.post('/{company_id}/spreadsheets/{operation}')
def import_sheet(company_id:UUID,operation:str,body:Spreadsheet,db:Session=Depends(session)):
    if operation not in ('preview','confirm'): raise HTTPException(404)
    db.company(str(company_id))
    cid=str(company_id)
    source_id=str(body.source_id) if body.source_id else None
    if source_id and not db.rows('integration_sources',cid,id='eq.'+source_id):
        raise HTTPException(404,'Origem não encontrada nesta empresa.')
    audit={'company_id':cid,'source_id':source_id,'kind':body.kind,
           'filename':body.filename.replace('\\','/').split('/')[-1],
           'fingerprint':hashlib.sha256(body.content.encode()).hexdigest()}
    try:
        parsed,errors=parse_sheet(body)
        identity='sku' if body.kind=='products' else 'external_id'
        existing={r.get(identity) for r in db.rows(body.kind,cid)}
        duplicates=[r[identity] for r in parsed if r[identity] in existing]
        valid=bool(parsed) and not errors and not duplicates
        if operation=='confirm':
            if not valid:
                raise HTTPException(422,'Corrija os erros ou identificadores duplicados antes de importar.')
            with db.transaction() as tx:
                job=tx.insert('import_jobs',{**audit,'status':'imported','imported':len(parsed)})
                saved=tx.request('POST',body.kind,payload=[{**r,'company_id':cid} for r in parsed])
                if source_id:
                    tx.request('POST','source_records',payload=[{'company_id':cid,'source_id':source_id,
                        'job_id':job['id'],'kind':body.kind,'external_id':r[identity],'record_id':r['id']} for r in saved])
            return {'imported':len(parsed),'job_id':job['id']}
        if not valid:
            db.insert('import_jobs',{**audit,'status':'rejected','rejected':len(errors)+len(duplicates),
                                     'detail':'Validação: corrija campos inválidos ou identificadores repetidos.'})
        return {'rows':parsed,'errors':errors,'duplicates':duplicates,'can_import':valid}
    except HTTPException as error:
        if error.status_code in (409,413,422):
            db.insert('import_jobs',{**audit,'status':'rejected','rejected':1,
                                     'detail':str(error.detail)[:500]})
        raise
