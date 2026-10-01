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

# Test-only: the assistant answers deterministically from the dossier, without calling the AI provider.
from backend import assistant
os.environ.setdefault('ANTHROPIC_API_KEY','e2e-test-only')
def fake_ask_model(dossier,question):
    revenue=dossier['periodo_atual']['revenue']
    return ({'title':'Resumo executivo de teste','summary':f"A empresa {dossier['empresa']} faturou R$ {revenue:.2f} no período.",
             'highlights':[{'label':'Receita do período','value':f'R$ {revenue:.2f}','trend':'none','note':'Sem comparação com o período anterior.'}],
             'sections':[{'heading':'Vendas e margens','paragraphs':['Pergunta recebida: '+question],'bullets':['Registre as despesas do mês.']}],
             'actions':[{'title':'Revisar preços com margem baixa','description':'Compare custo, taxas e preço de venda.','priority':'high'}],
             'caveats':['Dados de teste.']},'claude-opus-5-5',100,50)
assistant.ask_model=fake_ask_model
