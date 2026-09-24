import asyncio
import re
from uuid import uuid4
import psycopg
from fastapi.testclient import TestClient
from backend.main import app
from backend.security import MAX_BODY, SecurityMiddleware
from backend.neon_repository import Session, TABLES
from backend.test_neon_database import database

def test_every_private_route_requires_auth(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql://unused')
    monkeypatch.setenv('NEON_AUTH_URL','https://auth.example.test/auth')
    client = TestClient(app)
    checked = 0
    for template, operations in app.openapi()['paths'].items():
        if not template.startswith('/api/workspace'): continue
        path = re.sub(r'\{[^}]+\}',str(uuid4()),template)
        for method in operations:
            if method not in {'get','post','patch','put','delete'}: continue
            response = client.request(method,path,json={})
            assert response.status_code == 401, (method,template,response.status_code)
            assert response.headers['cache-control'] == 'no-store'
            checked += 1
    assert checked >= 25

def test_headers_docs_and_body_bounds():
    client = TestClient(app)
    response = client.get('/api/config')
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert "object-src 'none'" in response.headers['content-security-policy']
    for path in ('/api/docs','/api/redoc','/api/openapi.json'):
        assert client.get(path).status_code == 404
    assert client.post('/api/simulate',content=b'x'*(MAX_BODY+1)).status_code == 413
    assert client.get('/api/workspace/companies',headers={'Authorization':'Bearer '+'x'*17000}).status_code == 401

def test_stream_without_content_length_is_bounded():
    async def run():
        messages = iter([{'type':'http.request','body':b'x'*(MAX_BODY//2),'more_body':True}]*3)
        sent=[]
        async def receive(): return next(messages)
        async def send(message): sent.append(message)
        async def application(*args): raise AssertionError('Oversized request reached application')
        await SecurityMiddleware(application)({'type':'http','path':'/api/simulate','headers':[]},receive,send)
        assert sent[0]['status']==413
    asyncio.run(run())

def test_rls_covers_every_application_table(database):
    with psycopg.connect(database) as conn:
        role=conn.execute("select rolsuper,rolbypassrls,rolcanlogin from pg_roles where rolname='lucra_app'").fetchone()
        assert role == (False,False,False)
        rows=dict(conn.execute("select c.relname,c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r'").fetchall())
        assert all(rows.get(table) for table in TABLES)
    # Even with no company filter, a fresh unrelated identity sees no tenant data.
    stranger=Session('',{'id':str(uuid4())})
    for table in TABLES-{'report_deliveries'}:
        assert stranger.rows(table)==[], table
