"""PostgreSQL access with parameterized values and transaction-local RLS identity."""
from contextlib import nullcontext, contextmanager
import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from fastapi import HTTPException
from . import settings  # noqa: F401

TABLES = {'companies','sales','products','expenses','adjustments','settlements',
          'payment_terms','report_history','report_schedules','report_deliveries',
          'stock_movements','bills','bill_payments','action_plans','plan_updates','customers','customer_contacts','integration_sources','import_mappings','import_jobs','source_records','company_backups'}

def identifier(value):
    if not re.fullmatch(r'[a-z_][a-z_0-9]*', value):
        raise HTTPException(422, 'Campo inválido.')
    return sql.Identifier(value)

def serializable(value):
    if isinstance(value, dict): return {k:serializable(v) for k,v in value.items()}
    if isinstance(value, list): return [serializable(v) for v in value]
    if isinstance(value, (date,datetime,UUID)): return str(value)
    if isinstance(value, Decimal): return float(value)
    return value

def conditions(params):
    clauses, values = [], []
    for name, expression in params.items():
        if name in ('select','order','limit','offset'): continue
        if name == 'and':
            for term in expression.strip('()').split(','):
                column, operator, value = term.split('.',2)
                clause, args = conditions({column:operator+'.'+value})
                clauses.extend(clause); values.extend(args)
            continue
        operator, value = expression.split('.',1)
        if operator not in ('eq','gte','lte'): raise HTTPException(422,'Filtro inválido.')
        clauses.append(sql.SQL('{} {} %s').format(identifier(name),sql.SQL({'eq':'=','gte':'>=','lte':'<='}[operator])))
        values.append(value)
    return clauses, values

class Session:
    def __init__(self, token, user, *, worker=False, connection=None):
        self.user, self.worker = user, worker
        self.connection = connection

    def request(self, method, path, *, params=None, payload=None, prefer=None):
        if path not in TABLES or (path=='report_deliveries' and not self.worker):
            raise HTTPException(404,'Cadastro não encontrado.')
        params = params or {}
        table = sql.Identifier('public',path)
        clauses, values = conditions(params)
        where = sql.SQL(' WHERE ')+sql.SQL(' AND ').join(clauses) if clauses else sql.SQL('')
        try:
            with (nullcontext(self.connection) if self.connection else psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=15,row_factory=dict_row)) as conn:
                if not self.worker:
                    conn.execute('SET LOCAL ROLE lucra_app')
                    conn.execute("SELECT set_config('lucra.claims',%s,true)", (json.dumps(self.user),))
                if method == 'GET':
                    projection = params.get('select','*')
                    columns = sql.SQL('*') if projection=='*' else sql.SQL(',').join(identifier(c) for c in projection.split(','))
                    order, direction = params.get('order','id.asc').split('.')
                    if direction not in ('asc','desc'): raise HTTPException(422,'Ordenação inválida.')
                    query = sql.SQL('SELECT {} FROM {}').format(columns,table)+where
                    query += sql.SQL(' ORDER BY {} {} LIMIT %s OFFSET %s').format(identifier(order),sql.SQL(direction))
                    result = conn.execute(query,values+[int(params.get('limit',1000)),int(params.get('offset',0))]).fetchall()
                elif method == 'POST':
                    result = []
                    for row in payload if isinstance(payload,list) else [payload]:
                        keys = list(row)
                        query = sql.SQL('INSERT INTO {} ({}) VALUES ({}) RETURNING *').format(table,sql.SQL(',').join(map(identifier,keys)),sql.SQL(',').join(sql.Placeholder() for _ in keys))
                        result.append(conn.execute(query,[Jsonb(row[k]) if isinstance(row[k],dict) else row[k] for k in keys]).fetchone())
                elif method == 'PATCH':
                    if not clauses: raise HTTPException(422,'Atualização exige filtro.')
                    assignments = sql.SQL(',').join(sql.SQL('{}=%s').format(identifier(k)) for k in payload)
                    query = sql.SQL('UPDATE {} SET {}').format(table,assignments)+where+sql.SQL(' RETURNING *')
                    result = conn.execute(query,list(payload.values())+values).fetchall()
                else: raise HTTPException(405,'Operação não permitida.')
            return serializable(result)
        except psycopg.errors.UniqueViolation:
            raise HTTPException(409,'Registro duplicado. Confira o identificador.') from None
        except psycopg.errors.InsufficientPrivilege:
            raise HTTPException(403,'Acesso não autorizado.') from None
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException):
            raise HTTPException(422,'Confira valores, vínculos e limites do lançamento.') from None
        except psycopg.Error:
            raise HTTPException(503,'Banco indisponível. Confira a conexão e as migrações Neon.') from None

    @contextmanager
    def transaction(self, *, snapshot=False):
        with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=15,row_factory=dict_row) as conn:
            if snapshot:
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            yield Session('',self.user,worker=self.worker,connection=conn)

    def rows(self, table, company_id=None, **filters):
        params = {'select':'*','order':'id.asc','limit':1000,**filters}
        if company_id: params['company_id'] = f'eq.{company_id}'
        result, offset = [], 0
        while True:
            batch = self.request('GET',table,params={**params,'offset':offset})
            result.extend(batch)
            if len(batch)<1000: return result
            offset += len(batch)

    def company(self, company_id):
        rows = self.rows('companies',id=f'eq.{company_id}')
        if not rows: raise HTTPException(404,'Empresa não encontrada ou sem acesso.')
        return rows[0]

    def insert(self, table, payload):
        return self.request('POST',table,payload=payload)[0]
