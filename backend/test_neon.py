import time
from types import SimpleNamespace
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from backend.main import app
from backend import neon_auth
from backend.neon_repository import conditions, identifier

@pytest.fixture
def signing(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    monkeypatch.setenv('DATABASE_URL','postgresql://test')
    monkeypatch.setenv('NEON_AUTH_URL','https://auth.example.test/auth')
    for name in ('NEON_AUTH_AUDIENCE','NEON_AUTH_ISSUER','NEON_AUTH_JWKS_URL'):
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setattr(neon_auth,'jwks_client',lambda url:SimpleNamespace(get_signing_key_from_jwt=lambda token:SimpleNamespace(key=private.public_key())))
    return private

def token(key, **updates):
    payload={'sub':'user-A','iss':'https://auth.example.test/auth','aud':'https://auth.example.test',
             'exp':int(time.time())+300,'email':'a@example.test','emailVerified':True}
    payload.update(updates)
    return jwt.encode(payload,key,algorithm='RS256')

def test_neon_verified_identity(signing):
    db=neon_auth.session('Bearer '+token(signing))
    assert db.user=={'id':'user-A','email':'a@example.test','email_confirmed_at':True}

@pytest.mark.parametrize('updates',[{'exp':1},{'iss':'https://attacker.test'},{'aud':'other-project'},{'sub':''},{'role':'anonymous'},{'is_anonymous':True}])
def test_neon_rejects_untrusted_tokens(signing,updates):
    response=TestClient(app).get('/api/workspace/companies',headers={'Authorization':'Bearer '+token(signing,**updates)})
    assert response.status_code==401

def test_neon_rejects_wrong_signature(signing):
    other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    response=TestClient(app).get('/api/workspace/companies',headers={'Authorization':'Bearer '+token(other)})
    assert response.status_code==401

def test_config_never_exposes_database_password(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql://owner:private-value@localhost/db')
    monkeypatch.setenv('NEON_AUTH_URL','https://auth.example.test/auth')
    response=TestClient(app).get('/api/config')
    assert response.json()=={'configured':True,'neon_auth_url':'https://auth.example.test/auth'}
    assert 'private-value' not in response.text

def test_sql_values_are_bound_not_interpolated():
    malicious="x' OR true --"
    clauses,values=conditions({'id':'eq.'+malicious})
    assert values==[malicious]
    assert malicious not in str(clauses)
    with pytest.raises(Exception): identifier('id; DROP TABLE sales')
