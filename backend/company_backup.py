"""Consistent tenant snapshots; no authentication tokens or other companies."""
import gzip
import hashlib
import json
from datetime import datetime,timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Response
from .workspace import router, Session, session

BACKUP_TABLES=['products','sales','payment_terms','bills','expenses','adjustments','settlements',
 'stock_movements','bill_payments','report_history','report_schedules','action_plans','plan_updates',
 'customers','customer_contacts','integration_sources','import_mappings','import_jobs','source_records']


def snapshot(db,cid):
    with db.transaction(snapshot=True) as tx:
        company=tx.company(cid)
        records={table:tx.rows(table,cid) for table in BACKUP_TABLES}
    return {'format':'lucra-company','version':1,'schema_migration':'005_integrations_backups.sql',
            'created_at':datetime.now(timezone.utc).isoformat(),'company':company,'records':records}


def encode_snapshot(data):
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    return gzip.compress(raw),hashlib.sha256(raw).hexdigest()


def record_backup(db,data,checksum,filename,destination):
    return db.insert('company_backups',{'company_id':data['company']['id'],
        'record_count':sum(map(len,data['records'].values())),
        'checksum':checksum,'filename':filename,'destination':destination})

@router.get('/{company_id}/backups')
def history(company_id:UUID,db:Session=Depends(session)):
    cid=str(company_id);db.company(cid)
    return db.request('GET','company_backups',params={'company_id':'eq.'+cid,'order':'created_at.desc','limit':100})

@router.post('/{company_id}/backups')
def download(company_id:UUID,db:Session=Depends(session)):
    data=snapshot(db,str(company_id));content,checksum=encode_snapshot(data)
    if len(content)>4000000:
        raise HTTPException(413,'Cópia maior que o limite de download. Use o backup agendado pelo administrador.')
    filename=f'lucra-{company_id}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json.gz'
    record_backup(db,data,checksum,filename,'download')
    return Response(content,media_type='application/gzip',headers={
        'Content-Disposition':f'attachment; filename="{filename}"','Cache-Control':'no-store'})
