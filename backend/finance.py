"""All stored money is integer cents. Rates are illustrative, not tax advice."""
import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

PRODUCTS = [
    ('Fone Bluetooth Pulse', 'Eletrônicos', 120, 20000, 18000, 12, 1200, 400),
    ('Smartwatch Connect', 'Eletrônicos', 90, 20000, 18400, 12, 1100, 400),
    ('Caixa de Som Mini', 'Áudio', 80, 20000, 18000, 10, 1000, 400),
    ('Cadeira Office Pro', 'Escritório', 40, 80000, 48000, 6, 600, 400),
    ('Monitor Essential', 'Informática', 70, 40000, 24000, 6, 600, 400),
    ('Teclado Mecânico Flow', 'Informática', 80, 40000, 20550, 6, 606.25, 337.5),
]

def cents(value):
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def demo_sales():
    rows = []
    for month in (7, 8):
        for index, (name, category, qty, price, cost, installments, card, commission) in enumerate(PRODUCTS):
            for unit in range(qty):
                # Distribute actual unit records across the month, reproducibly.
                day = 1 + ((unit * 7 + index * 3) % 31)
                rows.append(dict(sold_on=f'2026-{month:02}-{day:02}', product=name, category=category,
                    quantity=1, revenue=price, cmv=cost, tax=cents(price * 0.06),
                    card=cents(Decimal(price) * Decimal(str(card)) / 10000),
                    commission=cents(Decimal(price) * Decimal(str(commission)) / 10000), installments=installments))
    return pd.DataFrame(rows)

def period_bounds(period, anchor):
    if period == 'daily':
        return anchor, anchor
    if period == 'weekly':
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    return anchor.replace(day=1), anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])

def summarize(frame, period, anchor):
    start, end = period_bounds(period, anchor)
    df = frame[(frame.sold_on >= start.isoformat()) & (frame.sold_on <= end.isoformat())].copy()
    totals = {key: int(df[key].sum()) for key in ['revenue', 'cmv', 'tax', 'card', 'commission', 'quantity']}
    totals['estimated'] = totals['revenue'] - totals['cmv']
    totals['hidden'] = totals['tax'] + totals['card'] + totals['commission']
    totals['net'] = totals['estimated'] - totals['hidden']
    totals['margin'] = round(totals['net'] / totals['revenue'] * 100, 2) if totals['revenue'] else 0
    df['net'] = df.revenue - df.cmv - df.tax - df.card - df.commission
    products = []
    for (name, category, installments), group in df.groupby(['product', 'category', 'installments']):
        revenue = int(group.revenue.sum())
        net = int(group.net.sum())
        products.append(dict(name=name, category=category, installments=int(installments),
            quantity=int(group.quantity.sum()), revenue=revenue, net=net,
            margin=round(net / revenue * 100, 2) if revenue else 0))
    products.sort(key=lambda p: (-p['quantity'], p['net']))
    daily = []
    current = start
    for_day = df.groupby('sold_on')[['revenue', 'cmv', 'net']].sum()
    while current <= end:
        key = current.isoformat()
        r = for_day.loc[key] if key in for_day.index else None
        daily.append(dict(date=key, estimated=int(r.revenue-r.cmv) if r is not None else 0,
                          net=int(r.net) if r is not None else 0))
        current += timedelta(days=1)
    return dict(start=start.isoformat(), end=end.isoformat(), period=period, totals=totals,
                products=products, daily=daily, source='demo')

def simulate(price, cost, installments, tax_rate, commission_rate, card_base, anticipation_rate):
    price_cents, cost_cents = cents(price * 100), cents(cost * 100)
    # Simple illustrative model: MDR + anticipation * average receivable term.
    card_rate = card_base + anticipation_rate * Decimal(installments + 1) / 2
    rates = {'tax': tax_rate, 'commission': commission_rate, 'card': card_rate}
    deductions = {k: cents(Decimal(price_cents) * rate / 100) for k, rate in rates.items()}
    net = price_cents - cost_cents - sum(deductions.values())
    retained = 1 - sum(rates.values()) / 100
    breakeven = int((Decimal(cost_cents) / retained).to_integral_value(rounding='ROUND_CEILING')) if retained > 0 else None
    return dict(price=price_cents, cost=cost_cents, **deductions, net=net,
                margin=round(net/price_cents*100, 2), card_rate=float(card_rate), breakeven=breakeven)
