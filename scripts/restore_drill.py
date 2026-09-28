"""Take the encrypted backup and prove it restores: schema, RLS and row counts.

Counts rows before and after pg_dump, restores the dump into
RESTORE_DATABASE_URL (a disposable, empty database) and requires every table
to land inside that window. Read-only on the source. Exits non-zero on any
gap, so the scheduled job fails loudly instead of keeping unusable backups.
"""
import os
from pathlib import Path
import psycopg
from psycopg import sql
from backend import settings  # noqa: F401
from backend.neon_repository import TABLES
from backend.schema import MIGRATIONS
from scripts.restore import restore
from scripts.backup import main as backup

def counts(url):
    with psycopg.connect(url,connect_timeout=15) as conn:
        return {t:conn.execute(sql.SQL('select count(*) from public.{}').format(sql.Identifier(t))).fetchone()[0] for t in sorted(TABLES)}

def main():
    before=counts(os.environ['DATABASE_URL'])
    path=backup()
    after=counts(os.environ['DATABASE_URL'])
    restore(path)
    target_url=os.environ['RESTORE_DATABASE_URL']
    restored=counts(target_url)
    problems=[]
    with psycopg.connect(target_url,connect_timeout=15) as conn:
        applied={r[0] for r in conn.execute('select name from public.lucra_migrations')}
        problems+=[f'migration missing: {m}' for m in MIGRATIONS if m not in applied]
        secured={r[0] for r in conn.execute("select relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relrowsecurity")}
        problems+=[f'RLS disabled: {t}' for t in sorted(TABLES-secured)]
    # Business tables are append-only through the API, so the dump's snapshot
    # must fall between the counts taken immediately before and after it.
    problems+=[f'{t}: restored {restored[t]} outside [{before[t]}, {after[t]}]' for t in sorted(TABLES) if not before[t]<=restored[t]<=after[t]]
    for t in sorted(TABLES): print(f'{t:22} source={after[t]:>7} restored={restored[t]:>7}')
    if problems: raise SystemExit('Restore drill failed:\n'+'\n'.join(problems))
    print(f'Restore drill passed: {path.name}, {sum(restored.values())} rows, {len(MIGRATIONS)} migrations.')

if __name__=='__main__': main()
