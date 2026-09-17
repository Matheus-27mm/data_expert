"""Optional adapter for the authenticated integration phase; demo never calls it.

Uses the end user's JWT and public key, preserving RLS. Never use service_role
for requests from users. Caller must validate JWT through Supabase Auth first.
"""
import os
import httpx
import pandas as pd

def load_company_sales(company_id: str, user_access_token: str) -> pd.DataFrame:
    url = os.environ['SUPABASE_URL'].rstrip('/')
    key = os.environ['SUPABASE_PUBLISHABLE_KEY']
    headers = {'apikey':key, 'Authorization':f'Bearer {user_access_token}'}
    with httpx.Client(timeout=20, headers=headers) as client:
        auth = client.get(f'{url}/auth/v1/user')
        auth.raise_for_status()
        rows = []
        offset = 0
        while True:
            response = client.get(f'{url}/rest/v1/sales',params={
                'company_id':f'eq.{company_id}',
                'select':'sold_on,product,category,quantity,revenue,cmv,tax,card,commission,installments',
                'order':'id.asc','limit':1000,'offset':offset})
            response.raise_for_status()
            batch = response.json()
            rows.extend(batch)
            if not batch:
                break
            offset += len(batch)
    return pd.DataFrame(rows,columns=['sold_on','product','category','quantity','revenue','cmv','tax','card','commission','installments'])
