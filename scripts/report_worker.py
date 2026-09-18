"""Generate closed-period reports and deliver to account owners via SMTP.

One daily execution, e.g. 10:00 UTC (06:00 Manaus). Unique delivery records
prevent overlapping runs from sending twice. Uncertain SMTP failures require
operator review before retry, rather than risking duplicate mail.
"""
import os
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo
from backend.workspace import Session, company_summary
from backend.report import report_pdf

def due_anchor(period, today):
    if period == 'weekly' and today.weekday() != 0:
        return None
    if period == 'monthly' and today.day != 1:
        return None
    return today-timedelta(days=1)

def main():
    db = Session('',{},worker=True)
    today = datetime.now(ZoneInfo('America/Manaus')).date()
    schedules = db.rows('report_schedules',enabled='eq.true')
    failures = 0
    for schedule in schedules:
        anchor = due_anchor(schedule['period'],today)
        if not anchor:
            continue
        if db.rows('report_deliveries',schedule_id=f"eq.{schedule['id']}",anchor=f'eq.{anchor}'):
            continue
        from fastapi import HTTPException
        try:
            delivery = db.insert('report_deliveries',{'schedule_id':schedule['id'],'anchor':str(anchor),'status':'processing'})
        except HTTPException as exc:
            if exc.status_code == 409:
                continue
            raise
        try:
            snapshot = company_summary(db,schedule['company_id'],schedule['period'],anchor)
            db.insert('report_history',{'company_id':schedule['company_id'],'period':schedule['period'],
                'anchor':str(anchor),'snapshot':snapshot,'created_by':schedule['created_by']})
            message=EmailMessage()
            message['Subject']=f"Lucra | Relatório {schedule['period']} | {anchor}"
            message['From']=os.environ['SMTP_FROM']
            message['To']=schedule['recipient']
            message.set_content('Seu relatório do período encerrado está anexado. Acesse o Lucra para consultar o histórico.')
            message.add_attachment(report_pdf(snapshot),maintype='application',subtype='pdf',filename=f'lucra-{anchor}.pdf')
            with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=30) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
                smtp.send_message(message)
            db.request('PATCH','report_deliveries',params={'id':f"eq.{delivery['id']}"},payload={'status':'sent'})
        except Exception:
            failures += 1
            db.request('PATCH','report_deliveries',params={'id':f"eq.{delivery['id']}"},payload={'status':'failed'})
            print(f"Delivery {delivery['id']} failed; inspect provider delivery status before retry.")
    if failures:
        raise SystemExit(f'{failures} delivery failures')

if __name__ == '__main__':
    main()
