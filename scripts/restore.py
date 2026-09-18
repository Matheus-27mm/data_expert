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
        conn.execute('grant select,insert on public.companies,public.sales,public.products,public.expenses,public.adjustments,public.settlements,public.payment_terms,public.report_history,public.report_schedules,public.stock_movements,public.bills,public.bill_payments to lucra_app')
        conn.execute('grant update on public.companies,public.products,public.payment_terms,public.report_schedules to lucra_app')
    print('Business data restored. Authentication accounts remain managed by Neon Auth.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path)
    restore(parser.parse_args().backup)
