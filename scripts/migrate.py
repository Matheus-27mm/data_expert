"""Apply versioned Neon PostgreSQL migrations atomically. Run: python -m scripts.migrate"""
import hashlib
import os
from pathlib import Path
import psycopg
from backend import settings  # noqa: F401

def main():
    if not os.getenv('DATABASE_URL'):
        raise SystemExit('Preencha DATABASE_URL no .env antes de aplicar as migrações.')
    try:
        with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=15) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('lucra_migrations'))")
            conn.execute('CREATE TABLE IF NOT EXISTS public.lucra_migrations(name text primary key, checksum text not null, applied_at timestamptz default now())')
            for path in sorted((Path(__file__).resolve().parents[1]/'neon'/'migrations').glob('*.sql')):
                content = path.read_text(encoding='utf-8')
                digest = hashlib.sha256(content.encode()).hexdigest()
                previous = conn.execute('SELECT checksum FROM public.lucra_migrations WHERE name=%s',(path.name,)).fetchone()
                if previous:
                    if previous[0]!=digest: raise SystemExit('Migração aplicada foi alterada: '+path.name)
                    continue
                conn.execute(content)
                conn.execute('INSERT INTO public.lucra_migrations(name,checksum) VALUES(%s,%s)',(path.name,digest))
                print('Aplicada: '+path.name)
        print('Migrações concluídas.')
    except psycopg.Error as error:
        raise SystemExit('Falha na migração; transação revertida. Código SQL: '+str(error.sqlstate or 'conexão')) from None

if __name__=='__main__': main()
