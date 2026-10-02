"""Create a fictitious demo store with ~3 months of coherent activity.

Usage (production runs through .github/workflows/demo.yml):
  python -m scripts.seed_demo --owner-company Perceptron
  python -m scripts.seed_demo --owner-email dono@empresa.com.br --name "Aurora Moda & Casa"

The owner is looked up with the worker credential; every write after that uses
the owner's RLS identity and the same code paths as the app (checkout, returns,
bills), so stock, receivables and expenses stay consistent. Refuses to run if
the owner already has a company with the same name. Deterministic (seeded RNG).
"""
import argparse
import random
from datetime import date, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from datetime import datetime

from backend import settings  # noqa: F401
from backend.neon_repository import Session

TERMS = [  # name, installments, card base %, anticipation % per month, share of sales
    ('Pix / dinheiro', 1, 0, 0, .30), ('Débito', 1, 1.6, 0, .18), ('Crédito à vista', 1, 3.1, 0, .14),
    ('Crédito 3x', 3, 3.6, 1.6, .16), ('Crédito 6x', 6, 3.9, 1.7, .10), ('Crédito 10x', 10, 4.2, 1.8, .08), ('Crédito 12x', 12, 4.4, 1.9, .04),
]
PRODUCTS = [  # sku, name, category, cost, price, weight, min stock
    ('CAM-BAS', 'Camiseta Básica Algodão', 'Roupas', 22.0, 59.90, 14, 15), ('CAM-EST', 'Camiseta Estampada', 'Roupas', 28.0, 79.90, 9, 10),
    ('POL-PIQ', 'Polo Piquet', 'Roupas', 45.0, 129.90, 5, 6), ('CAL-JEA', 'Calça Jeans Slim', 'Roupas', 78.0, 199.90, 7, 8),
    ('BER-SAR', 'Bermuda Sarja', 'Roupas', 42.0, 119.90, 5, 6), ('VES-MID', 'Vestido Midi Viscose', 'Roupas', 65.0, 189.90, 6, 6),
    ('JAQ-COU', 'Jaqueta Couro Eco', 'Roupas', 260.0, 329.00, 2, 3), ('MOL-BAS', 'Moletom Básico', 'Roupas', 55.0, 149.90, 4, 5),
    ('TEN-RUN', 'Tênis Runner Pro', 'Calçados', 210.0, 249.90, 4, 5), ('TEN-CAS', 'Tênis Casual Branco', 'Calçados', 95.0, 239.90, 5, 5),
    ('SAN-RAS', 'Sandália Rasteira', 'Calçados', 28.0, 89.90, 6, 8), ('CHI-SLI', 'Chinelo Slide', 'Calçados', 18.0, 49.90, 7, 10),
    ('BOL-TIR', 'Bolsa Tiracolo', 'Acessórios', 70.0, 179.90, 4, 4), ('CIN-COU', 'Cinto de Couro', 'Acessórios', 32.0, 89.90, 3, 4),
    ('BON-ABA', 'Boné Aba Curva', 'Acessórios', 19.0, 59.90, 5, 6), ('OCU-SOL', 'Óculos de Sol', 'Acessórios', 48.0, 149.90, 3, 4),
    ('MEI-KIT', 'Kit 3 Meias', 'Acessórios', 12.0, 39.90, 8, 12), ('REL-DIG', 'Relógio Digital', 'Acessórios', 115.0, 139.90, 2, 3),
    ('ALM-DEC', 'Almofada Decorativa', 'Casa', 24.0, 69.90, 4, 6), ('VEL-AROM', 'Vela Aromática', 'Casa', 14.0, 44.90, 5, 8),
    ('MAN-SOF', 'Manta para Sofá', 'Casa', 58.0, 159.90, 3, 4), ('JOG-TOA', 'Jogo de Toalhas', 'Casa', 49.0, 129.90, 3, 4),
]
SOLD_OUT = {'OCU-SOL', 'MAN-SOF'}  # not restocked in the last 7 weeks: they run out
LOW = {'CHI-SLI', 'VEL-AROM', 'BON-ABA'}  # not restocked in the last 4 weeks: below the minimum
FIRST = ['Ana', 'Bruno', 'Carla', 'Diego', 'Elaine', 'Fábio', 'Gabriela', 'Henrique', 'Isabela', 'João', 'Karina', 'Lucas', 'Mariana', 'Nelson',
         'Olívia', 'Paulo', 'Renata', 'Sérgio', 'Tatiane', 'Vinícius', 'Patrícia', 'Rafael', 'Juliana', 'Marcos', 'Camila']
LAST = ['Souza', 'Lima', 'Ferreira', 'Almeida', 'Costa', 'Ribeiro', 'Gomes', 'Martins', 'Rocha', 'Barbosa', 'Pereira', 'Carvalho']
CITIES = ['Manaus/AM', 'Manaus/AM', 'Manaus/AM', 'Iranduba/AM', 'Manacapuru/AM']

cents = lambda reais: int(round(reais * 100))

def owner_id(email, company):
    worker = Session('', {}, worker=True)
    if email:
        with worker.transaction() as tx:
            row = tx.connection.execute('select id from neon_auth."user" where lower(email)=lower(%s)', (email,)).fetchone()
        if not row: raise SystemExit(f'Nenhuma conta com o e-mail {email}.')
        return str(row['id'])
    rows = worker.rows('companies', name=f'eq.{company}')
    if len(rows) != 1: raise SystemExit(f'Esperava exatamente uma empresa chamada "{company}", encontrei {len(rows)}.')
    return rows[0]['owner_id']

def seed(owner, name, today, days=95):
    from backend.trading import Checkout, Line, checkout, receivables, Return, return_sale
    from backend.assistant import Ask, ask
    rng = random.Random(2026)
    db = Session('', {'id': owner})
    if db.rows('companies', name=f'eq.{name}'): raise SystemExit(f'A conta já tem uma empresa chamada "{name}". Nada foi alterado.')
    cid = db.insert('companies', {'name': name, 'owner_id': owner})['id']
    start = today - timedelta(days=days)
    terms = []
    for label, n, base, antecip, share in TERMS:
        terms.append((db.insert('payment_terms', {'company_id': cid, 'name': label, 'installments': n, 'tax_rate': 6, 'commission_rate': 3, 'card_base': base, 'anticipation_rate': antecip}), share))
    products = {}
    with db.transaction() as tx:
        for sku, pname, category, cost, price, weight, minimum in PRODUCTS:
            p = tx.insert('products', {'company_id': cid, 'sku': sku, 'name': pname, 'category': category, 'unit_cost': cents(cost), 'unit_price': cents(price),
                                       'min_stock': minimum, 'max_stock': minimum * 4, 'notes': 'Produto fictício para demonstração.'})
            products[sku] = {**p, 'weight': weight, 'stock': 0}
    def purchase(day, items, reference):
        """Restock as a supplier purchase: stock entries plus a bill due in 30 days."""
        total = 0
        with db.transaction() as tx:
            for sku, qty in items:
                p = products[sku]; p['stock'] += qty; total += qty * p['unit_cost']
                tx.insert('stock_movements', {'company_id': cid, 'product_id': p['id'], 'occurred_on': str(day), 'direction': 'in', 'quantity': qty,
                                              'reference': f'{reference}:{sku}', 'description': 'Compra de mercadoria'})
        return db.insert('bills', {'company_id': cid, 'reference': reference, 'supplier': rng.choice(['Têxtil Amazonas', 'Distribuidora Norte Calçados', 'Atacado Rio Negro', 'Casa & Decor Distribuidora']),
                                   'description': f'Compra de mercadoria ({len(items)} itens)', 'category': 'Compras de mercadoria', 'incurred_on': str(day), 'due_on': str(day + timedelta(days=30)), 'amount': total})
    bills = [purchase(start, [(s, p['weight'] * 4 + p['min_stock'] ) for s, p in products.items()], 'COMPRA-INICIAL')]
    customers = []
    with db.transaction() as tx:
        for i in range(28):
            first, last = FIRST[i % len(FIRST)], rng.choice(LAST)
            customers.append(tx.insert('customers', {'company_id': cid, 'name': f'{first} {last}', 'phone': f'(92) 9{rng.randint(8000, 9999)}-{rng.randint(1000, 9999)}',
                                                     'email': f'{first.lower()}.{last.lower()}@exemplo.com.br'.replace('á', 'a').replace('í', 'i').replace('é', 'e').replace('ó', 'o').replace('ú', 'u').replace('ê', 'e'),
                                                     'city': rng.choice(CITIES), 'notes': 'Cliente fictício para demonstração.'}))
    weights = [p['weight'] for p in products.values()]; skus = list(products)
    sales, number = [], 1000
    for offset in range(days + 1):
        day = start + timedelta(days=offset)
        if day.weekday() == 6: continue  # closed on Sundays
        growth = 1 + offset / days * .35
        count = max(1, int(rng.gauss(7 if day.weekday() < 4 else 11, 2) * growth))
        for _ in range(count):
            picks = {}
            for sku in rng.choices(skus, weights, k=rng.choice([1, 1, 1, 2, 2, 3])):
                picks[sku] = picks.get(sku, 0) + 1
            hold = (SOLD_OUT if day > today - timedelta(days=50) else set()) | (LOW if day > today - timedelta(days=28) else set())
            low = [s for s, q in picks.items() if products[s]['stock'] < q + products[s]['min_stock'] and s not in hold]
            if low: bills.append(purchase(day, [(s, products[s]['weight'] * 5 + products[s]['min_stock']) for s in low], f'COMPRA-{day:%Y%m%d}-{number}'))
            picks = {s: q for s, q in picks.items() if products[s]['stock'] >= q}
            if not picks: continue
            term, = rng.choices([t for t, _ in terms], [w for _, w in terms])
            heavy = any(s in ('TEN-RUN', 'JAQ-COU', 'REL-DIG') for s in picks)
            if heavy and rng.random() < .7: term = next(t for t, _ in terms if t['installments'] >= 10)
            number += 1
            body = Checkout(reference=uuid4(), sold_on=day, first_due_on=day if term['installments'] == 1 and term['card_base'] < 2 else day + timedelta(days=30),
                            lines=[Line(product_id=UUID(products[s]['id']), quantity=q) for s, q in picks.items()], terms_id=UUID(term['id']),
                            manage_stock=True, received=term['card_base'] < 2)
            for line in checkout(UUID(cid), body, db)['sales']: sales.append(line)
            for s, q in picks.items(): products[s]['stock'] -= q
    # Card receipts already due: most paid, a few left overdue to show in cash and alerts.
    payments = []
    for sale in receivables(UUID(cid), db):
        for part in sale['parts']:
            if part['balance'] and part['due_on'] and part['due_on'] < str(today) and rng.random() < .93:
                payments.append({'company_id': cid, 'sale_id': sale['id'], 'reference': f"REC-{sale['id'][:8]}-{part['number']}", 'received_on': part['due_on'], 'amount': part['balance']})
    with db.transaction() as tx:
        if payments: tx.request('POST', 'settlements', payload=payments)
    for sale in rng.sample([s for s in sales if s['sold_on'] < str(today - timedelta(days=10))], 4):
        return_sale(UUID(cid), UUID(sale['id']), Return(reference=uuid4(), quantity=1, occurred_on=date.fromisoformat(sale['sold_on']) + timedelta(days=3), restock=True,
                                                        description='Troca: tamanho errado'), db)
    # Fixed monthly costs; past ones paid, the current month open, some overdue.
    month = date(start.year, start.month, 1)
    while month <= today:
        for label, supplier, category, value, due_day in [('Aluguel da loja', 'Imobiliária Centro', 'Ocupação', 4200, 10), ('Salários e encargos', 'Folha de pagamento', 'Pessoal', 7600, 5),
                                                          ('Energia elétrica', 'Amazonas Energia', 'Ocupação', 780, 25), ('Internet e telefone', 'Operadora Fibra', 'Administrativo', 189.9, 15),
                                                          ('Contabilidade', 'Escritório Contábil Silva', 'Administrativo', 650, 20), ('Marketing digital', 'Agência Impulso', 'Marketing', 900, 12)]:
            due = month.replace(day=due_day)
            if due > today + timedelta(days=30): continue
            amount = cents(value * (1 + rng.uniform(-.08, .08)) if category != 'Ocupação' or 'Energia' in label else value)
            bills.append(db.insert('bills', {'company_id': cid, 'reference': f'{label[:12].upper()}-{due:%Y%m}', 'supplier': supplier, 'description': label, 'category': category,
                                             'incurred_on': str(due), 'due_on': str(due), 'amount': amount}))
        month = (month + timedelta(days=32)).replace(day=1)
    past_due = sorted((b for b in bills if b['due_on'] < str(today)), key=lambda b: b['due_on'])
    # Leave the latest energy bill and the latest supplier purchase unpaid, so the demo shows overdue bills.
    unpaid = {next((b['id'] for b in reversed(past_due) if b['description'] == label), None) for label in ('Energia elétrica',)}
    unpaid.add(next((b['id'] for b in reversed(past_due) if b['category'] == 'Compras de mercadoria'), None))
    with db.transaction() as tx:
        for bill in past_due:
            if bill['id'] in unpaid: continue
            partial = bill['category'] == 'Compras de mercadoria' and bill['due_on'] > str(today - timedelta(days=15)) and rng.random() < .5
            tx.insert('bill_payments', {'company_id': cid, 'bill_id': bill['id'], 'reference': f"PAG-{bill['reference']}", 'paid_on': bill['due_on'],
                                        'amount': bill['amount'] // 2 if partial else bill['amount']})
    plans = [('Revisar o preço do Tênis Runner Pro', 'Vendido em 10x, o tênis fecha no prejuízo depois das taxas. Simular novo preço ou limitar parcelas.', 'high', 'progress', 7),
             ('Negociar taxa da maquininha', 'Pedir proposta a duas adquirentes com taxa menor no crédito parcelado.', 'high', 'pending', 14),
             ('Repor óculos e mantas', 'Itens esgotados com boa saída. Fazer pedido ao fornecedor.', 'medium', 'pending', -3),
             ('Campanha de clientes inativos', 'Mensagem no WhatsApp para quem não compra há 60 dias.', 'medium', 'done', -10),
             ('Organizar vitrine da coleção casa', 'Destacar mantas, almofadas e velas na entrada.', 'low', 'pending', 21)]
    for title, description, priority, status, due in plans:
        plan = db.insert('action_plans', {'company_id': cid, 'title': title, 'description': description, 'priority': priority, 'status': status, 'due_on': str(today + timedelta(days=due))})
        if status != 'pending': db.insert('plan_updates', {'company_id': cid, 'plan_id': plan['id'], 'message': 'Iniciado na reunião de acompanhamento da semana.'})
    with db.transaction() as tx:
        for i, customer in enumerate(customers[:14]):
            tx.insert('customer_contacts', {'company_id': cid, 'customer_id': customer['id'], 'channel': rng.choice(['whatsapp', 'whatsapp', 'phone', 'store']),
                                            'message': rng.choice(['Avisou sobre a chegada da nova coleção.', 'Ofereceu troca de tamanho.', 'Enviou cupom de aniversário.', 'Confirmou reserva de produto.']),
                                            'response': rng.choice(['Vai passar na loja no sábado.', 'Pediu fotos pelo WhatsApp.', '', 'Gostou e quer ser avisada da próxima coleção.']),
                                            'next_on': str(today + timedelta(days=i % 9)) if i < 9 else None})
    ask(UUID(cid), Ask(question='Faça um resumo executivo da empresa neste período.', period='monthly', anchor=(today.replace(day=1) - timedelta(days=1))), db)
    return cid, len(sales), len(payments)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-email'); parser.add_argument('--owner-company', default='Perceptron')
    parser.add_argument('--name', default='Aurora Moda & Casa'); parser.add_argument('--today')
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else datetime.now(ZoneInfo('America/Manaus')).date()
    cid, sales, payments = seed(owner_id(args.owner_email, args.owner_company), args.name, today)
    print(f'Empresa de demonstração criada: {args.name} ({cid}) com {sales} itens de venda e {payments} recebimentos.')

if __name__ == '__main__':
    main()
