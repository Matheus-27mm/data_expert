from pathlib import Path
from backend.schema import MIGRATIONS, LATEST
from backend.company_backup import snapshot

def test_declared_migrations_match_directory():
    files = sorted(p.name for p in (Path(__file__).resolve().parents[1]/'neon'/'migrations').glob('*.sql'))
    assert list(MIGRATIONS) == files

def test_backup_records_current_schema():
    class DB:
        def transaction(self, snapshot=False):
            from contextlib import nullcontext
            return nullcontext(self)
        def company(self, cid): return {'id': cid, 'name': 'X'}
        def rows(self, table, cid): return []
    assert snapshot(DB(), 'c')['schema_migration'] == LATEST
