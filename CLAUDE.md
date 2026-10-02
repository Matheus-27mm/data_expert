# Sobrevo — guia para agentes e desenvolvedores

SaaS multiempresa que mostra o resultado real das vendas de pequenos varejos
(CMV, Simples, MDR/antecipação, comissão). Produção: https://dataexpert-eight.vercel.app

## Stack e topologia
- **Frontend**: React 19 + Vite, SPA com roteamento por hash (`#/workspace/<area>`, `#/demo/<page>`). Sem biblioteca de server-state.
- **API**: FastAPI, monólito modular em `backend/`. Vercel Function via `api/index.py`; Docker serve SPA + API na mesma origem (`STATIC_DIR`).
- **Banco**: Neon PostgreSQL (endpoint pooler). **Auth**: Neon Auth (Better Auth), JWT validado por JWKS em `backend/neon_auth.py`.
- **CI**: `.github/workflows/ci.yml`. **Cron** (backup, relatórios, health): `operations.yml`.

## Comandos
```
npm run dev                      # SPA em 127.0.0.1:5173 (proxy /api)
python -m uvicorn backend.main:app --reload --port 8000
python -m pytest backend -q      # sem NEON_TEST_DATABASE_URL, 12 testes de RLS são pulados
npm run build                    # tsc + vite
npx playwright test              # exige NEON_TEST_DATABASE_URL (Postgres descartável)
python -m scripts.migrate        # aplica neon/migrations no DATABASE_URL do ambiente (produção: só via CI)
python -m scripts.seed_demo --owner-company Perceptron   # loja fictícia (produção: workflow demo.yml)
python -m scripts.restore_drill  # backup + restore em banco vazio (RESTORE_DATABASE_URL) + verificação
```
Postgres descartável para testes: `docker run -d --name sobrevo-e2e-pg -e POSTGRES_PASSWORD=local-test-only -p 127.0.0.1:55499:5432 postgres:18-alpine`
e `NEON_TEST_DATABASE_URL=postgresql://postgres:local-test-only@127.0.0.1:55499/postgres`.

## Nome do produto
- A marca é **Sobrevo** (antes Lucra; ADR 0011). Logos em `public/brand/sobrevo-*.svg`; textos gerados usam `backend/brand.py`.
- Identificadores técnicos continuam com `lucra` de propósito e **não devem ser renomeados**: roles e schema do banco (`lucra_app`, `lucra_api`, `lucra_private`, `lucra.claims`, `lucra_migrations`), migrations aplicadas, o formato `lucra-company` dos backups e as chaves `lucra-company:` do navegador.

## Invariantes que não podem ser quebradas
- **Isolamento entre empresas** em três camadas: RLS (`SET LOCAL ROLE lucra_app` + `lucra.claims` por transação, em `neon_repository.Session`), FKs compostas `(company_id, id)` e `db.company(cid)` em toda rota. Toda tabela nova com `company_id` precisa de RLS, policies `owner_*`, FK composta e índice em `company_id`.
- **Dinheiro em centavos inteiros** (`bigint`/`int`). Nunca float em cálculo ou persistência.
- **Lançamentos financeiros são append-only**: `sales`, `adjustments`, `settlements`, `stock_movements`, `bill_payments` não têm UPDATE. Correção = novo lançamento.
- **Invariantes de domínio vivem no banco** (triggers com `pg_advisory_xact_lock`): estoque ≥ 0, pagamento ≤ saldo, devolução ≤ receita/CMV, recebimento ≤ esperado.
- Venda importada é histórico (`stock_managed=false`): não baixa estoque.
- Conta a pagar de **compra de mercadoria para revenda** (categoria com "mercadoria" ou "revenda") não vira despesa: o custo entra no resultado como CMV na venda (migration 011).
- Importação aceita CSV/TSV/TXT (UTF-8 ou cp1252), `.xlsx` e `.xls`; identificador ausente é gerado; venda sem CMV usa o custo do catálogo.

## Convenções
- Migrations: novo arquivo `neon/migrations/NNN_*.sql` **e** entrada em `backend/schema.py` no mesmo commit (`test_schema.py` falha se divergirem). Migration aplicada nunca é editada (checksum em `lucra_migrations`).
- Acesso a dados só via `Session`: `rows`/`insert`/`request` para operações por tabela; `query(sql, params)` para agregações (SQL literal no código, valores só em `params`, mesma identidade RLS). Somas de ledger ficam no banco, não em Python. Leituras com várias consultas usam `db.transaction(snapshot=True)`.
- Toda rota nova sob `/api/workspace/{company_id}` depende de `session`; `test_security.py` enumera as rotas privadas pela OpenAPI.
- Estilo existente é denso (várias instruções por linha). Siga o arquivo ao editar; não reformate arquivos inteiros junto com mudanças de comportamento.

## Assistente de análise
- Sem serviço externo (ADR 0012). `backend/assistant.py` monta o dossiê sob RLS (`build_dossier`); `backend/insights.py` identifica os temas da pergunta e escreve a resposta por regras e modelos de frase. Para o assistente entender algo novo: tema em `TOPICS`, seção e regras em `analyze`, teste em `test_assistant.py`.
- A resposta segue o contrato `Answer` (resumo, destaques, seções, ações, ressalvas), usado pela página e pelo PDF.
- O nome do produto em textos gerados vem de `backend/brand.py`.

## Deploy e ambientes — atenção
- Fluxo: branch → PR (CI + preview da Vercel em modo demo) → revisão → merge. `push` em `main` publica em produção pela Vercel imediatamente.
- **Migrations de produção** rodam em `.github/workflows/database.yml`, só depois do CI verde num push em `main`. Como o deploy da Vercel é paralelo, toda migration precisa ser **compatível com o código em produção** (expand/contract): primeiro um PR só com o schema aditivo, depois o PR do código; remoções numa release posterior.
- Não há staging. `.env` local aponta para o **Neon de produção** com a credencial de owner: não rode `scripts.migrate` nem scripts ad hoc com ele.
- Backup diário (`operations.yml`) faz restore drill a cada execução; o job falha se o dump não restaurar completo.
- O tenant "Perceptron" em produção contém dados fictícios de demonstração (24/09/2026).

## Documentação
- Decisões de arquitetura: `docs/adr/`. Prioridades de produto: `docs/PRIORIDADES_PRODUTO.md`.
- Segurança: `docs/SEGURANCA.md`. Desempenho: `docs/DESEMPENHO.md`. README: guia de uso e API.
