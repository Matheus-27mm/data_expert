from copy import deepcopy
from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from backend import assistant, insights
from backend.assistant import Answer, Ask

def period(revenue=0.0, net=0.0, operating=None, expenses=0.0, margin=0.0):
    return {'inicio': '2026-09-01', 'fim': '2026-09-30', 'unidades_vendidas': 3, 'revenue': revenue, 'cmv': revenue * .5, 'tax': revenue * .06,
            'card': revenue * .04, 'commission': revenue * .02, 'estimated': revenue * .5, 'hidden': revenue * .12, 'net': net, 'expenses': expenses,
            'refunds': 0, 'cost_recovered': 0, 'operating': net - expenses if operating is None else operating, 'margem_vendas_pct': margin, 'margem_operacional_pct': 0}

DOSSIER = {
    'empresa': 'Loja Exemplo', 'data_de_hoje': '2026-10-01', 'periodo_tipo': 'monthly',
    'periodo_atual': period(12000, 4200, expenses=5000, margin=35), 'periodo_anterior': period(10000, 4000, expenses=3000, margin=40),
    'resultado_diario_atual': [],
    'produtos_no_periodo': [{'produto': 'Tênis', 'categoria': 'C', 'parcelas': 12, 'unidades': 10, 'receita': 3000, 'resultado': -250.5, 'margem_pct': -8.4},
                            {'produto': 'Meia', 'categoria': 'C', 'parcelas': 1, 'unidades': 40, 'receita': 9000, 'resultado': 4450.5, 'margem_pct': 49.4}],
    'produtos_com_prejuizo': 1,
    'despesas_por_categoria': [{'categoria': 'Aluguel', 'total': 3500}, {'categoria': 'Energia', 'total': 1500}],
    'contas_a_pagar': {'saldo_em_aberto': 2000, 'vencidas': {'quantidade': 1, 'total': 800}, 'proximos_30_dias': [{'fornecedor': 'Imobiliária', 'descricao': 'Aluguel', 'vencimento': '2026-10-05', 'saldo': 1200}]},
    'estoque': {'produtos': 2, 'unidades': 30, 'valor_ao_custo': 1500, 'sem_saldo': ['Boné'], 'abaixo_do_minimo': []},
    'a_receber': {'saldo_em_aberto': 3000, 'vencido': 0, 'proximos_30_dias': 1000},
    'planos_de_acao': {'pending': 1, 'progress': 0, 'done': 0, 'atrasados': [], 'em_aberto': ['Rever preços']},
    'clientes': {'cadastrados': 5, 'retornos_nos_proximos_7_dias': 2},
}

def test_topics_follow_the_question():
    assert insights.topics_of('Quais produtos estão me dando prejuízo?')[0] == 'produtos'
    assert insights.topics_of('Como fica meu caixa nos próximos 30 dias?')[0] == 'caixa'
    assert insights.topics_of('Compare com o mês passado')[0] == 'comparacao'
    assert insights.topics_of('xyz') == ['resumo']

def test_money_and_percent_in_brazilian_format():
    assert insights.brl(1234.5) == 'R$ 1.234,50' and insights.brl(-80) == '-R$ 80,00' and insights.pct(8.25) == '8,2%'

def test_loss_question_names_the_product_and_recommends_price_review():
    answer = Answer.model_validate(insights.analyze(DOSSIER, 'Quais produtos estão me dando prejuízo e por quê?')).model_dump()
    assert answer['title'].startswith('Produtos e margens')
    assert 'R$ 12.000,00' in answer['summary'] and 'alta de 20,0%' in answer['summary']
    text = str(answer['sections'])
    assert 'Tênis em 12x' in text and '-R$ 250,50' in text
    assert answer['actions'][0] == {'title': 'Revisar o preço de Tênis', 'description': answer['actions'][0]['description'], 'priority': 'high'}

def test_cash_question_projects_inflows_against_outflows():
    answer = insights.analyze(DOSSIER, 'Como fica meu caixa nos próximos 30 dias?')
    cash = next(s for s in answer['sections'] if s['heading'].startswith('Caixa'))
    assert 'R$ 1.000,00 a receber' in cash['paragraphs'][0] and 'R$ 2.000,00 em contas a pagar' in cash['paragraphs'][0]
    assert any(a['title'] == 'Organizar as contas vencidas' for a in answer['actions'])

def test_company_without_sales_gets_guidance_instead_of_invented_numbers():
    empty = deepcopy(DOSSIER)
    empty['periodo_atual'] = period(); empty['produtos_no_periodo'] = []; empty['produtos_com_prejuizo'] = 0
    answer = Answer.model_validate(insights.analyze(empty, 'Faça um resumo executivo')).model_dump()
    assert 'Não há vendas registradas' in answer['summary']
    assert answer['actions'][0]['title'] == 'Registrar as vendas do período'
    assert 'Nenhuma venda registrada no período selecionado.' in answer['caveats']

def test_comparison_without_previous_sales_says_so():
    first = deepcopy(DOSSIER); first['periodo_anterior'] = period()
    answer = insights.analyze(first, 'O que mudou em relação ao período anterior?')
    assert any('não há base para comparar' in p for s in answer['sections'] for p in s['paragraphs'])

def test_question_bounds():
    with pytest.raises(Exception): Ask(question='oi', anchor=date(2026, 9, 1))
    with pytest.raises(Exception): Ask(question='x' * 1001, anchor=date(2026, 9, 1))

@pytest.fixture
def database(monkeypatch):
    import os
    url = os.getenv('NEON_TEST_DATABASE_URL')
    if not url: pytest.skip('Disposable PostgreSQL required')
    monkeypatch.setenv('DATABASE_URL', url)
    from scripts.migrate import main
    main()

def test_analysis_is_stored_exported_and_isolated(database):
    from backend.neon_repository import Session
    owner = Session('', {'id': str(uuid4())}); intruder = Session('', {'id': str(uuid4())})
    cid = owner.insert('companies', {'name': 'Loja Assistente', 'owner_id': owner.user['id']})['id']
    owner.insert('sales', {'company_id': cid, 'external_id': 'v1', 'sold_on': '2026-09-18', 'product': 'Produto', 'category': 'C', 'quantity': 1,
                           'revenue': 20000, 'cmv': 10000, 'tax': 1200, 'card': 600, 'commission': 200, 'installments': 1})
    body = Ask(question='Faça um resumo executivo da empresa neste período.', period='monthly', anchor=date(2026, 9, 30))
    saved = assistant.ask(UUID(cid), body, owner)
    assert saved['model'] == insights.ENGINE and saved['created_by'] == owner.user['id']
    assert 'Loja Assistente vendeu R$ 200,00' in saved['answer']['summary']
    overview = assistant.assistant_overview(UUID(cid), owner)
    assert overview['history'][0]['title'].startswith('Resumo executivo')
    pdf = assistant.assistant_report_pdf(UUID(cid), UUID(saved['id']), owner).body
    assert pdf.startswith(b'%PDF') and len(pdf) > 1500
    for call in (lambda: assistant.assistant_report(UUID(cid), UUID(saved['id']), intruder), lambda: assistant.ask(UUID(cid), body, intruder)):
        with pytest.raises(HTTPException) as denied: call()
        assert denied.value.status_code == 404
