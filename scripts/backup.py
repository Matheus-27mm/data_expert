"""Encrypted PostgreSQL backup; restore uses the same private Fernet key.

Run with DATABASE_URL and BACKUP_KEY from a secret store. The key must be kept
outside the repository and backup artifact. Does not back up Storage objects.
"""
import os
from pathlib import Path
import subprocess
from datetime import datetime,timezone
from cryptography.fernet import Fernet
from backend import settings
from scripts.pg_tools import run_pg

def main():
    cipher = Fernet(os.environ['BACKUP_KEY'].encode())
    content = run_pg('pg_dump',['--format=custom','--no-owner','--no-acl','--schema=public','--schema=lucra_private'],os.environ['DATABASE_URL'])
    directory = Path('output/backups');directory.mkdir(parents=True,exist_ok=True)
    path=directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.dump.enc')
    path.write_bytes(cipher.encrypt(content))
    print(f'Encrypted backup: {path}')
    return path

if __name__ == '__main__':
    main()
