from fastapi.testclient import TestClient
from backend.main import app

def test_request_id_and_no_secret_in_logs(caplog):
    with caplog.at_level('INFO',logger='uvicorn.error'):
        response=TestClient(app).get('/api/health?secret=must-not-appear',headers={'Authorization':'Bearer private-token'})
    assert response.status_code==200 and response.headers.get('x-request-id')
    assert 'must-not-appear' not in caplog.text
    assert 'private-token' not in caplog.text

def test_readiness_without_credentials(monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    assert TestClient(app).get('/api/ready').json()=={'status':'ok','mode':'demo'}
