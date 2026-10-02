"""Built-in natural-language analysis: no external service, no model.

`analyze(dossier, question)` detects the topics of a question by keywords,
computes the relevant figures from the company dossier (built under RLS in
assistant.py) and writes the answer in Portuguese from templates. The output
follows the same Answer contract the page and the PDF render.
"""
import unicodedata

ENGINE = 'sobrevo-analise-v1'

TOPICS = {
    'produtos': ['prejuizo', 'margem', 'produto', 'preco', 'lucr', 'vende mais', 'mais vendido', 'ganho'],
    'caixa': ['caixa', 'receb', 'pagar', 'vencimento', 'vence', 'vencida', 'atras', 'fluxo', 'dinheiro', 'proximos', 'contas', 'conta a pagar'],
    'comparacao': ['compar', 'anterior', 'mudou', 'cresc', 'caiu', 'queda', 'aument', 'diminu', 'evolu', 'passado'],
    'despesas': ['despesa', 'gasto', 'gastando', 'custo fixo', 'custos fixos', 'alto'],
    'estoque': ['estoque', 'repor', 'reposicao', 'saldo', 'mercadoria', 'falta'],
    'clientes': ['cliente', 'retorno', 'atendimento', 'contat'],
    'prioridades': ['prioriz', 'o que fazer', 'devo fazer', 'acao', 'acoes', 'melhorar', 'foco', 'focar', 'proximo passo', 'plano'],
    'resumo': ['resumo', 'geral', 'como foi', 'como esta', 'como vai', 'panorama', 'visao', 'executivo', 'situacao'],
}
TITLES = {'resumo': 'Resumo executivo', 'produtos': 'Produtos e margens', 'caixa': 'Caixa dos próximos 30 dias',
          'comparacao': 'Comparação com o período anterior', 'despesas': 'Despesas do período', 'estoque': 'Situação do estoque',
          'clientes': 'Clientes e retornos', 'prioridades': 'Prioridades para melhorar o resultado'}
PERIOD = {'monthly': 'no mês', 'weekly': 'na semana', 'daily': 'no dia'}

def normalized(text):
    return unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode()

def topics_of(question):
    """Topics in order of keyword hits; a question without hits gets the general summary."""
    q = normalized(question)
    scored = [(sum(q.count(k) for k in words), topic) for topic, words in TOPICS.items()]
    found = [t for score, t in sorted(scored, key=lambda s: -s[0]) if score]
    return found[:3] or ['resumo']

def brl(value):
    sign = '-' if value < 0 else ''
    return sign + 'R$ ' + f'{abs(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def pct(value):
    return f'{value:.1f}%'.replace('.', ',')

def date_br(iso):
    y, m, d = iso.split('-'); return f'{d}/{m}/{y}'

def share(part, total):
    return part / total * 100 if total else 0

def change(current, previous):
    """(trend, sentence fragment) comparing two values; no trend when there is no base."""
    if not previous:
        return 'none', ''
    delta = (current - previous) / abs(previous) * 100
    if abs(delta) < 2:
        return 'flat', 'estável em relação ao período anterior'
    return ('up' if delta > 0 else 'down'), f"{'alta' if delta > 0 else 'queda'} de {pct(abs(delta))} sobre o período anterior"

def analyze(dossier, question):
    now, before = dossier['periodo_atual'], dossier['periodo_anterior']
    company, period = dossier['empresa'], PERIOD.get(dossier['periodo_tipo'], 'no período')
    span = f"{date_br(now['inicio'])} a {date_br(now['fim'])}"
    revenue, net, operating = now['revenue'], now['net'], now['operating']
    has_sales, had_sales = revenue > 0, before['revenue'] > 0
    topics = topics_of(question)
    products = dossier['produtos_no_periodo']
    losers = sorted([p for p in products if p['resultado'] < 0], key=lambda p: p['resultado'])
    bills, stock, receivable = dossier['contas_a_pagar'], dossier['estoque'], dossier['a_receber']
    due_out = sum(b['saldo'] for b in bills['proximos_30_dias']) + bills['vencidas']['total']
    expenses = dossier['despesas_por_categoria']
    plans, customers = dossier['planos_de_acao'], dossier['clientes']
    sections, highlights, actions, caveats = [], [], [], []

    def highlight(label, value, trend, note):
        if label not in {h['label'] for h in highlights}:
            highlights.append({'label': label, 'value': value, 'trend': trend, 'note': note})

    def action(title, description, priority):
        if title not in {a['title'] for a in actions}:
            actions.append({'title': title, 'description': description, 'priority': priority})

    # Core figures always lead.
    trend, text = change(revenue, before['revenue'])
    highlight('Receita do período', brl(revenue), trend, text.capitalize() + '.' if text else 'Total das vendas registradas.')
    trend, text = change(net, before['net'])
    highlight('Resultado das vendas', brl(net), trend, f"Margem de {pct(now['margem_vendas_pct'])} após custo, impostos, cartão e comissão.")
    trend, text = change(operating, before['operating'])
    highlight('Resultado operacional', brl(operating), trend, 'Depois das despesas e devoluções; não é saldo bancário.')

    if not has_sales:
        summary = (f"Não há vendas registradas para {company} {period} ({span}). Sem vendas, não é possível calcular margens nem resultado. "
                   'Registre as vendas ou importe a planilha do período para ter a análise completa.')
        caveats.append('Nenhuma venda registrada no período selecionado.')
        action('Registrar as vendas do período', 'Lance as vendas em Vendas ou importe a planilha em Importações para que o Sobrevo calcule margens e resultado.', 'high')
    else:
        trend_text = change(revenue, before['revenue'])[1]
        summary = (f"{company} vendeu {brl(revenue)} {period} ({span}){', ' + trend_text if trend_text else ''}. "
                   f"Depois de custo das mercadorias, impostos, cartão e comissão sobraram {brl(net)} ({pct(now['margem_vendas_pct'])} da receita); "
                   + (f"descontadas as despesas, o resultado operacional foi {brl(operating)}." if operating >= 0 else
                      f"MAS_DESPESAS as despesas consumiram mais do que isso e o resultado operacional ficou negativo em {brl(-operating)}."))
        summary = summary.replace('; MAS_DESPESAS', ', mas')
        if had_sales and now['margem_vendas_pct'] < before['margem_vendas_pct'] - 2 and revenue >= before['revenue']:
            summary += f" Atenção: a receita subiu, mas a margem das vendas caiu de {pct(before['margem_vendas_pct'])} para {pct(now['margem_vendas_pct'])}."
        if losers:
            summary += f" {len(losers)} {'produto vendeu' if len(losers) == 1 else 'produtos venderam'} no prejuízo."

    if 'resumo' in topics or 'prioridades' in topics:
        if has_sales:
            lost = now['cmv'] + now['tax'] + now['card'] + now['commission']
            parts = [('custo das mercadorias', now['cmv']), ('impostos', now['tax']), ('taxas de cartão e antecipação', now['card']), ('comissões', now['commission'])]
            biggest = max(parts, key=lambda p: p[1])
            sections.append({'heading': 'Para onde foi o dinheiro das vendas', 'paragraphs': [
                f"De cada R$ 100 vendidos, R$ {share(lost, revenue):.0f} foram para custos e deduções e R$ {share(net, revenue):.0f} ficaram como resultado das vendas.",
                f"O maior peso é {biggest[0]}: {brl(biggest[1])} ({pct(share(biggest[1], revenue))} da receita)."],
                'bullets': [f'{name.capitalize()}: {brl(value)} ({pct(share(value, revenue))})' for name, value in parts]})
        if not expenses and has_sales:
            caveats.append('Nenhuma despesa operacional lançada no período: o resultado operacional pode estar otimista.')

    if 'produtos' in topics or 'prioridades' in topics or ('resumo' in topics and losers):
        if not products:
            sections.append({'heading': 'Produtos', 'paragraphs': ['Não há vendas por produto no período para analisar.'], 'bullets': []})
        else:
            best = sorted([p for p in products if p['resultado'] > 0], key=lambda p: -p['resultado'])[:3]
            paragraphs = []
            if losers:
                paragraphs.append(f"{len(losers)} {'combinação de produto e parcelamento ficou' if len(losers) == 1 else 'combinações de produto e parcelamento ficaram'} no prejuízo. "
                                  'Quando um item vende bem mas deixa resultado negativo, normalmente o preço não cobre o custo somado às taxas do parcelamento.')
            else:
                paragraphs.append('Nenhum produto vendeu no prejuízo no período.')
            if best: paragraphs.append('Os que mais deixaram resultado: ' + '; '.join(f"{p['produto']} ({brl(p['resultado'])})" for p in best) + '.')
            bullets = [f"{p['produto']} em {p['parcelas']}x: {p['unidades']} un., receita {brl(p['receita'])}, resultado {brl(p['resultado'])} (margem {pct(p['margem_pct'])})" for p in losers[:6]]
            sections.append({'heading': 'Produtos e margens', 'paragraphs': paragraphs, 'bullets': bullets})
            highlight('Produtos no prejuízo', str(dossier['produtos_com_prejuizo']), 'none', 'Combinações de produto e parcelamento com resultado negativo.')
            if losers:
                worst = losers[0]
                high_installments = [p for p in losers if p['parcelas'] >= 6]
                action(f"Revisar o preço de {worst['produto']}", f"Vendido em {worst['parcelas']}x, deixou {brl(worst['resultado'])} no período. Use o Simulador de preço para encontrar o preço mínimo que cobre custo e taxas.", 'high')
                if high_installments:
                    action('Rever as condições de parcelamento longo', ('1 item no prejuízo foi vendido' if len(high_installments) == 1 else f"{len(high_installments)} itens no prejuízo foram vendidos") + " em 6x ou mais. Avalie limitar parcelas ou repassar a taxa de antecipação.", 'medium')

    if 'caixa' in topics or 'prioridades' in topics:
        incoming = receivable['proximos_30_dias']
        balance = incoming - due_out
        paragraphs = [f"Nos próximos 30 dias estão previstos {brl(incoming)} a receber das vendas parceladas e {brl(due_out)} em contas a pagar, incluindo as já vencidas. "
                      f"O saldo previsto do período é {brl(balance)}{' — atenção, as saídas superam as entradas' if balance < 0 else ''}."]
        bullets = [f"{b['descricao']} ({b['fornecedor']}): {brl(b['saldo'])} em {date_br(b['vencimento'])}" for b in bills['proximos_30_dias'][:6]]
        if bills['vencidas']['quantidade']:
            paragraphs.append(f"Há {bills['vencidas']['quantidade']} {'conta vencida' if bills['vencidas']['quantidade'] == 1 else 'contas vencidas'} somando {brl(bills['vencidas']['total'])}.")
            action('Organizar as contas vencidas', f"{brl(bills['vencidas']['total'])} em contas vencidas. Priorize as que geram juros e registre os pagamentos em Contas a pagar.", 'high')
        if receivable['vencido']:
            paragraphs.append(f"Também há {brl(receivable['vencido'])} em parcelas de clientes já vencidas e não registradas como recebidas.")
            action('Conferir recebimentos atrasados', f"{brl(receivable['vencido'])} em parcelas vencidas. Confirme no extrato e registre os recebimentos ou cobre os clientes.", 'medium')
        sections.append({'heading': 'Caixa dos próximos 30 dias', 'paragraphs': paragraphs, 'bullets': bullets})
        highlight('Saldo previsto em 30 dias', brl(balance), 'none', 'A receber menos contas a pagar nos próximos 30 dias.')
        caveats.append('A previsão de caixa considera só vendas integradas e contas lançadas; não inclui o saldo bancário atual.')

    if 'comparacao' in topics:
        if not had_sales:
            sections.append({'heading': 'Comparação com o período anterior', 'paragraphs': ['O período anterior não tem vendas registradas, então não há base para comparar.'], 'bullets': []})
            caveats.append('Período anterior sem vendas: variações não podem ser calculadas.')
        else:
            def line(label, a, b):
                return f"{label}: {brl(a)} contra {brl(b)} ({change(a, b)[1] or 'sem variação'})"
            margin_delta = now['margem_vendas_pct'] - before['margem_vendas_pct']
            sections.append({'heading': 'Comparação com o período anterior', 'paragraphs': [
                f"A margem das vendas foi de {pct(now['margem_vendas_pct'])}, {'subindo' if margin_delta >= 0 else 'caindo'} {pct(abs(margin_delta)).replace('%', ' ponto(s) percentual(is)')} em relação ao período anterior."],
                'bullets': [line('Receita', revenue, before['revenue']), line('Resultado das vendas', net, before['net']),
                            line('Despesas', now['expenses'], before['expenses']), line('Resultado operacional', operating, before['operating'])]})
            if net < before['net']:
                action('Investigar a queda do resultado', 'Compare em Produtos e margens quais itens perderam resultado e verifique mudanças de custo, preço ou parcelamento.', 'high')

    if 'despesas' in topics or 'prioridades' in topics:
        total = now['expenses']
        ratio = share(total, revenue)
        if not expenses:
            sections.append({'heading': 'Despesas do período', 'paragraphs': ['Nenhuma despesa operacional foi lançada no período.'], 'bullets': []})
            action('Lançar as despesas do mês', 'Registre aluguel, salários, energia e demais gastos em Contas a pagar para que o resultado operacional seja real.', 'medium')
        else:
            judgement = ('acima de 30% da receita, um nível alto para o comércio' if ratio > 30 else 'entre 15% e 30% da receita, um nível de atenção' if ratio > 15 else 'abaixo de 15% da receita, um nível controlado') if has_sales else 'sem vendas no período para comparar'
            sections.append({'heading': 'Despesas do período', 'paragraphs': [f"As despesas operacionais somaram {brl(total)}, {judgement}."],
                             'bullets': [f"{e['categoria']}: {brl(e['total'])} ({pct(share(e['total'], total))} das despesas)" for e in expenses[:6]]})
            highlight('Despesas operacionais', brl(total), change(total, before['expenses'])[0], f"{pct(ratio)} da receita do período." if has_sales else 'Total lançado no período.')
            if has_sales and ratio > 30:
                action(f"Revisar a categoria {expenses[0]['categoria']}", f"É a maior despesa ({brl(expenses[0]['total'])}). Veja o que pode ser renegociado ou cortado.", 'high')

    if 'estoque' in topics or 'prioridades' in topics:
        if not stock['produtos']:
            sections.append({'heading': 'Estoque', 'paragraphs': ['Nenhum produto cadastrado para acompanhar o estoque.'], 'bullets': []})
        else:
            paragraphs = [f"{stock['produtos']} produtos cadastrados, {stock['unidades']} unidades em estoque, valendo {brl(stock['valor_ao_custo'])} ao custo."]
            bullets = [f"Sem saldo: {name}" for name in stock['sem_saldo'][:6]] + [f"Abaixo do mínimo: {s['produto']} ({s['saldo']} de {s['minimo']})" for s in stock['abaixo_do_minimo'][:6]]
            if stock['sem_saldo'] or stock['abaixo_do_minimo']:
                action('Planejar a reposição do estoque', ' e '.join(x for x in [f"{len(stock['sem_saldo'])} {'produto' if len(stock['sem_saldo']) == 1 else 'produtos'} sem saldo" if stock['sem_saldo'] else '', f"{len(stock['abaixo_do_minimo'])} {'produto' if len(stock['abaixo_do_minimo']) == 1 else 'produtos'} abaixo do mínimo" if stock['abaixo_do_minimo'] else ''] if x).capitalize() + ". Confira o físico e registre as entradas.", 'medium')
            if stock['unidades'] == 0:
                caveats.append('Estoque sem movimentações registradas: os saldos podem não refletir o físico.')
            sections.append({'heading': 'Estoque', 'paragraphs': paragraphs, 'bullets': bullets})

    if 'clientes' in topics:
        due = customers['retornos_nos_proximos_7_dias']
        sections.append({'heading': 'Clientes', 'paragraphs': [f"{customers['cadastrados']} clientes cadastrados e {due} {'retorno previsto' if due == 1 else 'retornos previstos'} nos próximos 7 dias."], 'bullets': []})
        if due:
            action('Fazer os retornos de clientes da semana', f"{due} contatos com retorno marcado nos próximos 7 dias. Veja em Clientes.", 'low')

    if 'prioridades' in topics and (plans['atrasados'] or plans['em_aberto']):
        sections.append({'heading': 'Planos de ação em andamento', 'paragraphs': [f"{plans['pending']} a fazer, {plans['progress']} em andamento e {plans['done']} concluídos."],
                         'bullets': [f"Atrasado: {t}" for t in plans['atrasados'][:5]]})

    order = {'high': 0, 'medium': 1, 'low': 2}
    actions.sort(key=lambda a: order[a['priority']])
    title = TITLES[topics[0]] + ' — ' + span
    caveats.append('Impostos, taxas e comissões são os valores informados pela empresa; não substituem a apuração contábil.')
    return {'title': title, 'summary': summary, 'highlights': highlights[:6], 'sections': sections[:5], 'actions': actions[:5], 'caveats': caveats}
