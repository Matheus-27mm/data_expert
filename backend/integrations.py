"""Company-scoped integration catalog and reusable import profiles."""
from typing import Literal
from uuid import UUID
from fastapi import Depends, HTTPException
from pydantic import Field
from .workspace import router, Input, Session, session

class Source(Input):
    name: str = Field(min_length=2,max_length=100)
    provider: str = Field(default='spreadsheet',min_length=2,max_length=80)
    mode: Literal['file','api'] = 'file'

from .spreadsheets import ImportOptions

class Mapping(Input):
    source_id: UUID
    kind: Literal['products','sales','expenses']
    name: str = Field(min_length=2,max_length=100)
    mapping: dict[str,str] = Field(default_factory=dict,max_length=40)
    options: ImportOptions = Field(default_factory=ImportOptions)

@router.get('/{company_id}/integrations')
def overview(company_id:UUID,db:Session=Depends(session)):
    cid=str(company_id);db.company(cid)
    return {'sources':db.rows('integration_sources',cid),
            'mappings':db.rows('import_mappings',cid),
            'jobs':db.request('GET','import_jobs',params={'company_id':'eq.'+cid,'order':'created_at.desc','limit':100}),
            'capabilities':{'files':True,'automatic_erp':False}}

@router.post('/{company_id}/integrations',status_code=201)
def create_source(company_id:UUID,body:Source,db:Session=Depends(session)):
    db.company(str(company_id))
    return db.insert('integration_sources',{'company_id':str(company_id),**body.model_dump()})

@router.post('/{company_id}/integrations/mappings',status_code=201)
def save_mapping(company_id:UUID,body:Mapping,db:Session=Depends(session)):
    from .spreadsheets import MODELS
    cid=str(company_id);db.company(cid)
    if not db.rows('integration_sources',cid,id='eq.'+str(body.source_id)):
        raise HTTPException(404,'Origem não encontrada nesta empresa.')
    model=MODELS[body.kind]
    required={k for k,v in model.model_fields.items() if v.is_required()}
    provided=set(body.mapping)|set(body.options.defaults)
    if body.options.generate_ids: provided.add('sku' if body.kind=='products' else 'external_id')
    if not required<=provided or any(k not in model.model_fields for k in body.options.defaults) or any(k not in model.model_fields or not v.strip() or len(v)>180 for k,v in body.mapping.items()):
        raise HTTPException(422,'Relacione todos os campos obrigatórios a colunas válidas.')
    return db.insert('import_mappings',{'company_id':cid,**body.model_dump(mode='json')})
