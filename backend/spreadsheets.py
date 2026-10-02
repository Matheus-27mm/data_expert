"""Bounded, preview-first spreadsheet imports; all writes use the tenant RLS session."""
import hashlib
import base64
import binascii
import csv
import io
import zipfile
import json
import re
import unicodedata
from typing import Literal
from pydantic import ValidationError
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Depends, HTTPException
from pydantic import Field
from .workspace import router, Input, Product, Sale, Expense, Session, session, MONEY_MAX

class ExpenseImport(Expense):
    external_id: str = Field(min_length=1,max_length=120)

class SaleImport(Sale):
    """Store exports rarely carry costs and fees: missing ones default to zero,
    category and CMV come from the catalog (see fill_from_catalog)."""
    category: str = Field(default='',max_length=80)
    cmv: int | None = Field(default=None,ge=0,le=MONEY_MAX)
    tax: int = Field(default=0,ge=0,le=MONEY_MAX)
    card: int = Field(default=0,ge=0,le=MONEY_MAX)
    commission: int = Field(default=0,ge=0,le=MONEY_MAX)
    installments: int = Field(default=1,ge=1,le=12)

MODELS = {'products':Product,'sales':SaleImport,'expenses':ExpenseImport}
IDENTITY = {'products':'sku','sales':'external_id','expenses':'external_id'}

def required_fields(kind):
    """Fields the user must map or fill; the identity is generated when absent."""
    return {k for k,v in MODELS[kind].model_fields.items() if v.is_required()}-{IDENTITY[kind]}
MONEY = {'unit_cost','unit_price','revenue','cmv','tax','card','commission','amount'}

def normalized(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower())

ALIASES = {
 'sku':['código','cód','referência','código produto','sku'],
 'name':['produto','nome','descrição','nome do produto'],
 'category':['categoria','grupo','departamento'],
 'unit_cost':['custo','custo aquisição','preço de custo','custo unitário'],
 'unit_price':['preço','preço venda','preço de venda','valor unitário','valor de venda','preço unitário','venda'],
 'notes':['observações','obs'], 'active':['ativo'],
 'external_id':['id','referência','identificador','número da venda','código venda','id venda','pedido','nº pedido','número do pedido','nº venda','n venda','nº','cupom','nota','nf','documento','código'],
 'sold_on':['data','data venda','data da venda'],
 'product':['produto','nome do produto','produto auto'],
 'quantity':['quantidade','qtd','qtde','quant','unidades'],
 'revenue':['receita','receita total','total da venda','valor total','total','valor da venda','valor','faturamento'],
 'cmv':['cmv','custo mercadoria','custo mercadoria total'],
 'tax':['imposto','impostos','valor imposto'],
 'card':['taxa cartão','valor taxa cartão','taxa de cartão','tarifa cartão','taxa maquininha'],
 'commission':['comissão','valor comissão'],
 'installments':['parcelas','número de parcelas'],
 'description':['descrição','histórico','despesa','descrição da despesa'],
 'incurred_on':['data','competência','data competência','data vencimento','data da despesa','data pagamento'],
 'amount':['valor','total','valor despesa','valor pago'],
}

def header_key(header):
    return normalized(re.sub(r'\([^)]*\)|r\$|em reais','',str(header),flags=re.I))

def suggest_mapping(kind,headers):
    result={}
    for field in MODELS[kind].model_fields:
        matches=[h for h in headers if not (field in MONEY and '%' in h) and header_key(h) in {normalized(v) for v in [field,*ALIASES.get(field,[])]}]
        if len(matches)==1: result[field]=matches[0]
    return result

class ImportOptions(Input):
    header_row: int | None = Field(default=None,ge=1,le=50)
    number_format: Literal['auto','br','us'] = 'auto'
    date_format: Literal['dmy','mdy'] = 'dmy'
    encoding: Literal['utf-8-sig','cp1252'] = 'utf-8-sig'
    delimiter: Literal['auto',',',';','\t'] = 'auto'
    defaults: dict[str,str] = Field(default_factory=dict,max_length=40)
    generate_ids: bool = False

class Spreadsheet(ImportOptions):
    kind: str
    source_id: UUID | None = None
    filename: str = Field(max_length=180)
    content: str = Field(max_length=2800000)
    sheet: str | None = None
    mapping: dict[str,str] = Field(default_factory=dict,max_length=40)
    corrections: dict[int,dict[str,str]] = Field(default_factory=dict,max_length=1000)
    excluded_rows: list[int] = Field(default_factory=list,max_length=1000)

class SourceRow(dict):
    def __init__(self,values,line):
        super().__init__(values)
        self.line=line

def money_value(value,locale):
    text=str(value).strip().replace('R$','').replace('$','').replace(' ','').replace('\xa0','')
    if isinstance(value,str):
        if locale=='auto':
            if re.fullmatch(r'[+-]?\d+[.,]\d{3}',text):
                raise ValueError('Número ambíguo: escolha o formato brasileiro ou internacional.')
            locale='br' if ',' in text and ('.' not in text or text.rfind(',')>text.rfind('.')) else 'us'
        pattern=r'\d+(?:,\d{1,2})?|\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?' if locale=='br' else r'\d+(?:\.\d{1,2})?|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?'
        if not re.fullmatch(pattern,text): raise ValueError('Valor monetário inválido para o formato escolhido.')
        text=text.replace('.','').replace(',','.') if locale=='br' else text.replace(',','')
    amount=Decimal(text)
    if not amount.is_finite() or amount<0 or amount>MONEY_MAX/100 or amount.as_tuple().exponent < -2:
        raise ValueError('Valor monetário inválido.')
    return int(amount*100)


def decode_text(raw,encoding):
    """UTF-8 first; files saved by Excel on Windows are usually cp1252."""
    try: return raw.decode(encoding)
    except UnicodeDecodeError:
        if encoding!='utf-8-sig': raise
        return raw.decode('cp1252')

def read_xls(raw,selected):
    """Legacy Excel 97-2003 (.xls), common in ERP exports. Dates become date objects."""
    import xlrd
    book=xlrd.open_workbook(file_contents=raw,on_demand=True)
    try:
        sheets=book.sheet_names()
        sheet=book.sheet_by_name(selected or sheets[0])
        if sheet.nrows>1051: raise ValueError('Limite de 1.000 linhas após o cabeçalho.')
        data=[]
        for r in range(sheet.nrows):
            row=[]
            for c in range(min(sheet.ncols,41)):
                cell=sheet.cell(r,c)
                if cell.ctype==xlrd.XL_CELL_DATE: row.append(xlrd.xldate.xldate_as_datetime(cell.value,book.datemode))
                elif cell.ctype==xlrd.XL_CELL_EMPTY: row.append(None)
                elif cell.ctype==xlrd.XL_CELL_NUMBER and cell.value==int(cell.value): row.append(int(cell.value))
                else: row.append(cell.value)
            while row and row[-1] in (None,''): row.pop()
            data.append(row)
        return data,sheets
    finally: book.release_resources()

def read_sheet(body, discover=False):
    if body.kind not in MODELS:
        raise HTTPException(422,'Escolha produtos, vendas ou despesas.')
    try:
        raw=base64.b64decode(body.content,validate=True)
        if len(raw)>2000000: raise ValueError('Arquivo maior que 2 MB.')
        sheets=[]
        if body.filename.lower().endswith('.xls'):
            data,sheets=read_xls(raw,body.sheet)
            if discover: return [],[],sheets
        elif body.filename.lower().endswith('.xlsx'):
            from openpyxl import load_workbook
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if sum(f.file_size for f in archive.infolist())>20000000 or len(archive.infolist())>200:
                    raise ValueError('Planilha muito grande quando descompactada.')
            book=load_workbook(io.BytesIO(raw),read_only=True,data_only=False,keep_links=False)
            cached=None
            try:
                sheets=book.sheetnames
                if discover: return [],[],sheets
                sheet=book[body.sheet or sheets[0]]
                sheet.reset_dimensions()
                cached=load_workbook(io.BytesIO(raw),read_only=True,data_only=True,keep_links=False)
                cached_sheet=cached[sheet.title]
                cached_sheet.reset_dimensions()
                data=[]
                for index,(row,values_row) in enumerate(zip(sheet.iter_rows(max_col=41),cached_sheet.iter_rows(max_col=41))):
                    if index>1050: raise ValueError("Limite de 1.000 linhas após o cabeçalho.")
                    values=[(v.value if v.value is not None and v.data_type!='e' else f'Fórmula sem resultado: {c.coordinate}') if c.data_type=='f' else c.value for c,v in zip(row,values_row)]
                    while values and values[-1] is None: values.pop()
                    data.append(values)
            finally:
                book.close()
                if cached: cached.close()
        elif body.filename.lower().endswith(('.csv','.tsv','.txt')):
            text=decode_text(raw,body.encoding)
            try: dialect=csv.Sniffer().sniff(text[:4096],delimiters=',;\t')
            except csv.Error:
                candidates={d:list(csv.reader(io.StringIO(text[:8192]),delimiter=d))[:50] for d in [',',';','\t']}
                chosen=max(candidates,key=lambda d:max((len(suggest_mapping(body.kind,r)) for r in candidates[d]),default=0))
                dialect=type('DetectedDialect',(csv.excel,),{'delimiter':chosen})
            data=[]
            reader=csv.reader(io.StringIO(text),dialect) if body.delimiter=='auto' else csv.reader(io.StringIO(text),delimiter=body.delimiter)
            for row in reader:
                data.append(row)
                if len(data)>1051: raise ValueError('Limite de linhas excedido.')
        else: raise ValueError('Use CSV, TSV ou Excel (.xlsx ou .xls).')
        if len(data)<2: raise ValueError('Arquivo sem registros.')
        candidates=[i for i,r in enumerate(data[:50]) if any(v is not None and str(v).strip() for v in r)]
        start=body.header_row-1 if body.header_row else max(candidates,key=lambda i:len(suggest_mapping(body.kind,[str(v or '') for v in data[i]])),default=0)
        headers=[str(v or '').strip() for v in data[start]]
        body.header_row=start+1
        numbered=[(i+1,r) for i,r in enumerate(data) if i>start and any(v is not None and str(v).strip() for v in r)]
        if len(numbered)>1000: raise ValueError('Limite de 1.000 registros por arquivo.')
        if len(headers)>40 or not all(headers) or len(set(headers))!=len(headers):
            raise ValueError('Use até 40 colunas, com cabeçalhos únicos e preenchidos.')
        if any(len(r)>len(headers) for _,r in numbered): raise ValueError('Há linhas com mais colunas que o cabeçalho.')
        rows=[SourceRow(dict(zip(headers,r)),line) for line,r in numbered]
        return headers,rows,sheets
    except (ValueError,KeyError,IndexError,UnicodeError,zipfile.BadZipFile,binascii.Error,csv.Error) as e:
        raise HTTPException(422,str(e))
    except Exception:
        raise HTTPException(422,'Não foi possível ler o arquivo. Confira se é um CSV UTF-8 ou XLSX válido.') from None


def prepare_rows(body):
    headers,rows,_=read_sheet(body)
    model=MODELS[body.kind]
    mapping=body.mapping or suggest_mapping(body.kind,headers)
    fields=set(model.model_fields)
    if any(k not in fields or v not in headers for k,v in mapping.items()) or any(k not in fields for k in body.defaults):
        raise HTTPException(422,'Mapeamento ou valores fixos inválidos.')
    if any(k not in fields for edit in body.corrections.values() for k in edit):
        raise HTTPException(422,'Campo de correção inválido.')
    identity=IDENTITY[body.kind]
    occurrences={};prepared=[]
    for row in rows:
        signature=json.dumps(dict(row),sort_keys=True,default=str,ensure_ascii=False)
        digest=hashlib.sha256((body.kind+'|'+str(body.source_id or '')+'|'+signature).encode()).hexdigest()[:32]
        occurrences[digest]=occurrences.get(digest,0)+1
        if row.line in body.excluded_rows: continue
        values={k:row.get(v) for k,v in mapping.items()}
        for k,v in body.defaults.items():
            if values.get(k) is None or values.get(k)=='': values[k]=v
        if values.get(identity) is None or not str(values.get(identity)).strip():
            # Products get a readable code from the name; ledgers a stable hash, so re-sending the same file is detected as duplicate.
            values[identity]=(re.sub(r'[^A-Z0-9]+','-',normalized_upper(values.get('name')))[:60].strip('-') if body.kind=='products' and values.get('name') else '') or 'AUTO-'+digest+'-'+str(occurrences[digest])
        values.update(body.corrections.get(row.line,{}))
        prepared.append((row.line,values))
    return prepared

def normalized_upper(value):
    return unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode().upper()

def parse_date(value,order):
    """dd/mm/aaaa, dd-mm-aaaa, dd.mm.aa or ISO; order 'mdy' for US files."""
    text=str(value).strip().split(' ')[0]
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',text): return text
    parts=re.split(r'[/.-]',text)
    if len(parts)!=3 or not all(p.isdigit() for p in parts): raise ValueError(f'Data inválida: {value}. Use DD/MM/AAAA.')
    day,month,year=(parts if order=='dmy' else [parts[1],parts[0],parts[2]])
    year=int(year)+(2000 if len(year)==2 else 0)
    return date(year,int(month),int(day)).isoformat()

def catalog_index(products):
    index={}
    for p in products:
        index[normalized(p['name'])]=p; index[normalized(p['sku'])]=p
    return index

def parse_sheet(body,prepared=None,catalog=None):
    """catalog (sales only): normalized name/SKU -> product, used for missing CMV and category."""
    model=MODELS[body.kind];parsed,errors,seen=[],[],set()
    identity=IDENTITY[body.kind]
    for number,original in (prepare_rows(body) if prepared is None else prepared):
        values={k:v for k,v in original.items() if not (v is None or (isinstance(v,str) and not v.strip()))};field=''
        try:
            for field,v in list(values.items()):
                if isinstance(v,str) and v.startswith('Fórmula sem resultado:'):
                    raise ValueError(v+'. Recalcule no Excel ou informe o valor na revisão.')
                if model.model_fields[field].annotation is str and isinstance(v,(int,float)):
                    values[field]=str(int(v)) if int(v)==v else str(v)
                if field in MONEY: values[field]=money_value(v,body.number_format)
                if field.endswith('_on'):
                    if isinstance(v,datetime): values[field]=v.date().isoformat()
                    elif isinstance(v,date): values[field]=v.isoformat()
                    else: values[field]=parse_date(v,body.date_format)
                if field=='active' and isinstance(v,str) and normalized(v) in ('sim','nao','ativo','inativo'):
                    values[field]=normalized(v) in ('sim','ativo')
            if body.kind=='sales':
                match=(catalog or {}).get(normalized(values.get('product',''))) if catalog is not None else None
                if match and values.get('cmv') is None: values['cmv']=match['unit_cost']*int(Decimal(str(values.get('quantity',0))))
                if match and not values.get('category'): values['category']=match['category']
            record=model.model_validate(values).model_dump(mode='json')
            if body.kind=='sales':
                if record['cmv'] is None:
                    field='cmv';raise ValueError(f"Produto \"{record['product']}\" não está no catálogo: cadastre o produto ou informe o custo (CMV) da venda.")
                record['category']=record['category'] or 'Sem categoria'
            if record[identity] in seen:
                field=identity;raise ValueError('Identificador repetido neste arquivo.')
            seen.add(record[identity]);parsed.append(record)
        except ValidationError as e:
            errors.extend({'line':number,'field':str(item['loc'][0]),'message':'Campo obrigatório ausente ou valor inválido.'} for item in e.errors())
        except (ValueError,TypeError,ArithmeticError) as e:
            errors.append({'line':number,'field':field,'message':str(e) or 'Valor inválido.'})
    return parsed,errors

@router.post('/{company_id}/spreadsheets/read')
def inspect(company_id:UUID,body:Spreadsheet,db:Session=Depends(session)):
    db.company(str(company_id))
    headers,rows,sheets=read_sheet(body,discover=body.filename.lower().endswith(('.xlsx','.xls')) and not body.sheet)
    return {'headers':headers,'sample':rows[:5],'sheets':sheets,'count':len(rows),
            'header_row':body.header_row,'suggested_mapping':suggest_mapping(body.kind,headers),
            'fields':[{'key':k,'required':k in required_fields(body.kind)} for k in MODELS[body.kind].model_fields]}

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
        # Decode and map the workbook once; parsing and the review table share it.
        prepared=prepare_rows(body)
        parsed,errors=parse_sheet(body,prepared,catalog_index(db.rows('products',cid)) if body.kind=='sales' else None)
        identity=IDENTITY[body.kind]
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
        return {'rows':parsed,'errors':errors,'duplicates':duplicates,'can_import':valid,
                'review':[{'line':line,'values':values} for line,values in prepared]}
    except HTTPException as error:
        if error.status_code in (409,413,422):
            db.insert('import_jobs',{**audit,'status':'rejected','rejected':1,
                                     'detail':str(error.detail)[:500]})
        raise
