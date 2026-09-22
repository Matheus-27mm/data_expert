"""One encrypted snapshot per company, using the same external key as global backup."""
import os
from pathlib import Path
from datetime import datetime,timezone
from cryptography.fernet import Fernet
from backend.neon_repository import Session
from backend.company_backup import snapshot, encode_snapshot, record_backup


def main():
    cipher=Fernet(os.environ['BACKUP_KEY'].encode())
    directory=Path('output/backups/companies');directory.mkdir(parents=True,exist_ok=True)
    admin=Session('',{},worker=True)
    companies=admin.rows('companies')
    for company in companies:
        # Even the scheduler exports with the company's owner's RLS identity.
        db=Session('',{'id':company['owner_id']})
        data=snapshot(db,company['id']);content,checksum=encode_snapshot(data)
        name=f'{company["id"]}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json.gz.enc'
        (directory/name).write_bytes(cipher.encrypt(content))
        record_backup(db,data,checksum,name,'scheduled')
    print(f'Encrypted company snapshots generated: {len(companies)}')

if __name__=='__main__':main()
