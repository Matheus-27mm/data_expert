"""Restore one company as a NEW copy. Existing records are never overwritten.

Usage: python -m scripts.restore_company backup.json.gz[.enc] --company-id ORIGINAL_UUID
Uses RESTORE_DATABASE_URL (explicit target) and BACKUP_KEY for encrypted files.
"""
import argparse,gzip,json,os
from pathlib import Path
from uuid import UUID,uuid4
from cryptography.fernet import Fernet
from backend.company_backup import BACKUP_TABLES
from backend.neon_repository import Session


def restore_data(data,expected_company):
    if data.get('format')!='lucra-company' or data.get('version')!=1:
        raise ValueError('Unsupported backup format')
    company=data['company'];records=data['records']
    if company['id']!=str(expected_company) or set(records)!=set(BACKUP_TABLES):
        raise ValueError('Company or schema does not match backup')
    mapping={company['id']:str(uuid4())}
    for table,rows in records.items():
        for row in rows:
            if row.get('company_id')!=company['id'] or row['id'] in mapping:
                raise ValueError('Invalid company scope or duplicate record')
            mapping[row['id']]=str(uuid4())
    db=Session('',{'id':company['owner_id']})
    with db.transaction() as tx:
        tx.insert('companies',{'id':mapping[company['id']],'owner_id':company['owner_id'],
                               'name':company['name']+' (restaurada)'})
        for table in BACKUP_TABLES:
            rows=records[table]
            if table=='stock_movements': rows=sorted(rows,key=lambda r:r['direction']!='in')
            for original in rows:
                # Bill insertion already books its expense through the database trigger.
                if table=='expenses' and original.get('bill_id'): continue
                row=dict(original)
                for key in ('id','company_id','sale_id','product_id','bill_id','plan_id','customer_id','source_id','job_id','record_id'):
                    if row.get(key):
                        if row[key] not in mapping: raise ValueError('Reference outside company backup')
                        row[key]=mapping[row[key]]
                if table=='report_schedules':row['enabled']=False
                tx.insert(table,row)
    return mapping[company['id']]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path);parser.add_argument('--company-id',type=UUID,required=True)
    args=parser.parse_args()
    target=os.getenv('RESTORE_DATABASE_URL')
    if not target:raise SystemExit('Set RESTORE_DATABASE_URL explicitly before restoring.')
    os.environ['DATABASE_URL']=target
    raw=args.backup.read_bytes()
    if args.backup.suffix=='.enc':raw=Fernet(os.environ['BACKUP_KEY'].encode()).decrypt(raw)
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as archive:
        content=archive.read(100000001)
    if len(content)>100000000:raise SystemExit('Backup exceeds restore size limit.')
    result=restore_data(json.loads(content),args.company_id)
    print('Company restored as a new copy: '+result)

if __name__=='__main__':main()
