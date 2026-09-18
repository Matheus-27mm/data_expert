from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def brl(cents):
    return ('R$ ' + f'{cents/100:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')

def report_pdf(data):
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=(210*mm, 297*mm), rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    styles['Heading2'].keepWithNext = True
    styles.add(ParagraphStyle(name='Brand', fontName='Helvetica-Bold', fontSize=28, textColor=colors.HexColor('#174b3b'), spaceAfter=18))
    styles.add(ParagraphStyle(name='Muted', fontSize=9, leading=14, textColor=colors.HexColor('#64736b'), spaceAfter=10))
    styles.add(ParagraphStyle(name='Cell', fontSize=9, leading=13))
    period = {'daily':'Diário', 'weekly':'Semanal', 'monthly':'Mensal'}[data['period']]
    t = data['totals']
    story = [Paragraph('lucra.', styles['Brand']), Paragraph(f'Relatório {period} de Resultados', styles['Title']),
        Paragraph(f"{escape(data.get('company','Casa Nova Store'))} | {data['start']} a {data['end']} | {'Dados demonstrativos' if data.get('source')=='demo' else 'Dados registrados pela empresa'}", styles['Muted']), Spacer(1, 6*mm)]
    summary = [['INDICADOR', 'VALOR'], ['Receita de vendas', brl(t['revenue'])], ['Custo das mercadorias (CMV)', brl(t['cmv'])],
        ['Lucro estimado (receita - CMV)', brl(t['estimated'])], ['Impostos informados', brl(t['tax'])],
        ['Cartão e antecipação', brl(t['card'])], ['Comissões', brl(t['commission'])], ['Resultado líquido das vendas', brl(t['net'])],
        ['Margem de contribuição', f"{t['margin']:.2f}%".replace('.', ',')]]
    if 'operating' in t:
        summary += [['Despesas operacionais',brl(t['expenses'])],['Devoluções e estornos',brl(t['refunds'])],
                    ['CMV recuperado',brl(t['cost_recovered'])],['Resultado operacional',brl(t['operating'])]]
    table = Table(summary, colWidths=[115*mm, 59*mm])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#174b3b')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),10),('ALIGN',(1,1),(-1,-1),'RIGHT'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f2f6f3'),colors.white]),
        ('FONTNAME',(0,7),(-1,7),'Helvetica-Bold')]))
    story += [table, Spacer(1, 5*mm), Paragraph('Itens no prejuízo', styles['Heading2']),
        Paragraph('Produtos com margem negativa, ordenados por unidades vendidas.', styles['Muted'])]
    negative = [p for p in data['products'] if p['net'] < 0]
    if negative:
        rows = [['PRODUTO', 'QTD.', 'PARCELAS', 'PREJUÍZO']]
        rows += [[Paragraph(escape(p['name']), styles['Cell']), str(p['quantity']), f"{p['installments']}x", brl(p['net'])] for p in negative]
        table = Table(rows, colWidths=[80*mm,24*mm,28*mm,42*mm], repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#fcebe7')),('TEXTCOLOR',(-1,1),(-1,-1),colors.HexColor('#b74230')),
            ('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('ALIGN',(1,0),(-1,-1),'RIGHT')]))
        story.append(table)
    else:
        story.append(Paragraph('Nenhum item com margem negativa neste período.' if t['quantity'] else 'Nenhuma venda neste período.', styles['Normal']))
    story += [Spacer(1,5*mm), Paragraph('Leitura do resultado',styles['Heading2']),
        Paragraph(f"As deduções somam {brl(t['hidden'])}. Revise preço, custo e condições de parcelamento dos itens com prejuízo.",styles['Normal']),
        Spacer(1,4*mm), Paragraph('Metodologia: resultado das vendas = receita - CMV - impostos - cartão/antecipação - comissões. Resultado operacional = resultado das vendas - despesas - devoluções + CMV recuperado, quando esses lançamentos estão disponíveis. Não representa saldo bancário nem apuração fiscal. '+('Taxas fictícias para demonstração.' if data.get('source')=='demo' else 'Valores conforme registros da empresa; relatório preservado na data de geração.'),styles['Muted'])]
    def footer(canvas, document):
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#64736b'))
        canvas.drawString(18*mm,12*mm,'L U C R A  /  Clareza para decidir melhor')
        canvas.drawRightString(192*mm,12*mm,f'Página {document.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()
