import json
import os
from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from backend import assistant
from backend.assistant import SCHEMA, Answer, Ask

ANSWER = {'title': 'Resumo de setembro', 'summary': 'As vendas renderam R$ 200,00 <script>.', 'highlights': [{'label': 'Receita', 'value': 'R$ 200,00', 'trend': 'none', 'note': 'Primeiro mês.'}],
          'sections': [{'heading': 'Margens', 'paragraphs': ['Produto & cia teve margem de 34%.'], 'bullets': ['Revise o preço']}],
          'actions': [{'title': 'Revisar preço', 'description': 'Compare custo e taxas.', 'priority': 'high'}], 'caveats': ['Sem despesas lançadas.']}

def test_schema_matches_answer_model():
    assert set(SCHEMA['properties']) == set(Answer.model_fields) and SCHEMA['additionalProperties'] is False
    Answer.model_validate(ANSWER)

class FakeStream:
    def __init__(self, message, calls, kwargs): self.message, self.calls, self.kwargs = message, calls, kwargs
    def __enter__(self): self.calls.append(self.kwargs); return self
    def __exit__(self, *exc): return False
    def get_final_message(self): return self.message

def fake_client(monkeypatch, stop_reason='end_turn', text=json.dumps(ANSWER)):
    import anthropic
    calls = []
    message = SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type='text', text=text)], model='claude-opus-5-5',
                              usage=SimpleNamespace(input_tokens=1200, output_tokens=640))
    class Client:
        def __init__(self, **options): calls.append(options); self.beta = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: FakeStream(message, calls, kw)))
    monkeypatch.setattr(anthropic, 'Anthropic', Client)
    return calls

def test_model_call_contract(monkeypatch):
    calls = fake_client(monkeypatch)
    answer, model, used_in, used_out = assistant.ask_model({'empresa': 'X'}, 'Como foi o mês?')
    options, request = calls
    assert options == {'timeout': 55.0, 'max_retries': 0}
    assert request['model'] == 'claude-opus-5-5' and request['fallbacks'] == 'default' and request['betas'] == ['server-side-fallback-2026-07-01']
    assert request['output_config']['format'] == {'type': 'json_schema', 'schema': SCHEMA}
    assert request['system'][0]['cache_control'] == {'type': 'ephemeral'}
    assert '<dados_empresa>' in request['messages'][0]['content'] and 'Como foi o mês?' in request['messages'][0]['content']
    assert answer['title'] == 'Resumo de setembro' and (used_in, used_out) == (1200, 640)

@pytest.mark.parametrize('stop_reason,text,status', [('refusal', '', 422), ('max_tokens', '{"title":', 502), ('end_turn', '{"title":"x"}', 502)])
def test_model_failures_become_clear_errors(monkeypatch, stop_reason, text, status):
    fake_client(monkeypatch, stop_reason, text)
    with pytest.raises(HTTPException) as error:
        assistant.ask_model({}, 'pergunta')
    assert error.value.status_code == status

def test_question_bounds():
    with pytest.raises(Exception): Ask(question='oi', anchor=date(2026, 9, 1))
    with pytest.raises(Exception): Ask(question='x' * 1001, anchor=date(2026, 9, 1))

@pytest.fixture
def database(monkeypatch):
    url = os.getenv('NEON_TEST_DATABASE_URL')
    if not url: pytest.skip('Disposable PostgreSQL required')
    monkeypatch.setenv('DATABASE_URL', url)
    from scripts.migrate import main
    main()

def test_analysis_is_stored_exported_and_isolated(database, monkeypatch):
    from backend.neon_repository import Session
    owner = Session('', {'id': str(uuid4())}); intruder = Session('', {'id': str(uuid4())})
    cid = owner.insert('companies', {'name': 'Loja Assistente', 'owner_id': owner.user['id']})['id']
    owner.insert('sales', {'company_id': cid, 'external_id': 'v1', 'sold_on': '2026-09-18', 'product': 'Produto', 'category': 'C', 'quantity': 1,
                           'revenue': 20000, 'cmv': 10000, 'tax': 1200, 'card': 600, 'commission': 200, 'installments': 1})
    seen = []
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    monkeypatch.setattr(assistant, 'ask_model', lambda dossier, question: (seen.append(dossier), (ANSWER, 'claude-opus-5-5', 10, 20))[1])
    body = Ask(question='Como foi setembro?', period='monthly', anchor=date(2026, 9, 30))
    saved = assistant.ask(UUID(cid), body, owner)
    dossier = seen[0]
    assert dossier['empresa'] == 'Loja Assistente' and dossier['periodo_atual']['revenue'] == 200.0 and dossier['periodo_anterior']['revenue'] == 0
    assert saved['created_by'] == owner.user['id'] and saved['answer']['title'] == 'Resumo de setembro'
    overview = assistant.assistant_overview(UUID(cid), owner)
    assert overview['configured'] and overview['used_today'] == 1 and overview['history'][0]['title'] == 'Resumo de setembro'
    pdf = assistant.assistant_report_pdf(UUID(cid), UUID(saved['id']), owner).body
    assert pdf.startswith(b'%PDF') and len(pdf) > 1500
    for call in (lambda: assistant.assistant_report(UUID(cid), UUID(saved['id']), intruder), lambda: assistant.ask(UUID(cid), body, intruder)):
        with pytest.raises(HTTPException) as denied: call()
        assert denied.value.status_code == 404
    monkeypatch.setattr(assistant, 'DAILY_LIMIT', 1)
    with pytest.raises(HTTPException) as limited: assistant.ask(UUID(cid), body, owner)
    assert limited.value.status_code == 429 and len(seen) == 1

def test_unconfigured_assistant_refuses_before_any_work(database, monkeypatch):
    from backend.neon_repository import Session
    owner = Session('', {'id': str(uuid4())})
    cid = owner.insert('companies', {'name': 'Sem IA', 'owner_id': owner.user['id']})['id']
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.setattr(assistant, 'ask_model', lambda *a: pytest.fail('model must not be called'))
    with pytest.raises(HTTPException) as error:
        assistant.ask(UUID(cid), Ask(question='Como foi?', anchor=date(2026, 9, 30)), owner)
    assert error.value.status_code == 503
