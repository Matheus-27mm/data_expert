"""Restore business data only into an empty database; never overwrite an existing one."""
import argparse
import os
from pathlib import Path
import psycopg
from cryptography.fernet import Fernet
from backend import settings
from scripts.pg_tools import run_pg

def restore(path):
    target=os.environ['RESTORE_DATABASE_URL']
    content=Fernet(os.environ['BACKUP_KEY'].encode()).decrypt(Path(path).read_bytes())
    with psycopg.connect(target,connect_timeout=15) as conn:
        if conn.execute("select 1 from pg_tables where schemaname not in ('pg_catalog','information_schema') limit 1").fetchone():
            raise RuntimeError('Restore requires an empty database. Existing data will not be overwritten.')
        if not conn.execute("select 1 from pg_roles where rolname='lucra_app'").fetchone():
            conn.execute('create role lucra_app nologin nosuperuser nobypassrls')
        conn.execute("do $$ begin execute format('grant lucra_app to %I',current_user); end $$")
        # No CASCADE: even a single existing object prevents removing the schema.
        conn.execute('drop schema if exists public')
    run_pg('pg_restore',['--dbname='+target.split('/')[-1].split('?')[0],'--no-owner','--no-acl','--single-transaction','--exit-on-error'],target,content=content)
    with psycopg.connect(target,connect_timeout=15) as conn:
        conn.execute('grant usage on schema public,lucra_private to lucra_app')
        from backend.neon_repository import TABLES
        # Older backups may predate a table: restore available privileges, then migrate.
        existing={r[0] for r in conn.execute("select tablename from pg_tables where schemaname='public'")}
        for table in sorted((TABLES-{'report_deliveries'}) & existing):
            conn.execute(psycopg.sql.SQL('grant select,insert on public.{} to lucra_app').format(psycopg.sql.Identifier(table)))
        for table in {'companies','products','payment_terms','report_schedules','action_plans'} & existing:
            conn.execute(psycopg.sql.SQL('grant update on public.{} to lucra_app').format(psycopg.sql.Identifier(table)))
    print('Business data restored. Authentication accounts remain managed by Neon Auth.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path)
    restore(parser.parse_args().backup)
