"""Test-only app, never included in a production image or deployment.

Neon identity is simulated; business APIs use a disposable PostgreSQL database.
"""
import os
from uuid import uuid4
if not os.getenv('NEON_TEST_DATABASE_URL'):
    raise RuntimeError('Browser tests require NEON_TEST_DATABASE_URL for a disposable database')
os.environ['DATABASE_URL']=os.environ['NEON_TEST_DATABASE_URL']
os.environ['NEON_AUTH_URL']='https://auth.example.test/auth'
from scripts.migrate import main
main()
from backend.main import app
from backend.neon_auth import session
from backend.neon_repository import Session
from fastapi import Header,HTTPException

USER={'id':str(uuid4()),'email':'browser@example.test','email_confirmed_at':True}
def test_session(authorization:str=Header(default='')):
    # Test-only server: also accept unsigned JWT-shaped tokens so the browser
    # suite can exercise client-side expiry handling. Production verifies JWKS.
    token=authorization.removeprefix('Bearer ')
    if token!='browser-test-token' and not (token.count('.')==2 and token.startswith('e2e.')):
        raise HTTPException(401,'Test login required')
    return Session('',USER)
app.dependency_overrides[session]=test_session
