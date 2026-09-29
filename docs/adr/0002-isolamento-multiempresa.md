# 0002 — Isolamento multiempresa por RLS + FKs compostas

**Contexto.** Várias lojas no mesmo banco; nenhuma pode ler ou referenciar dados de outra.

**Decisão.** Três camadas independentes:
1. **RLS**: em cada transação, `SET LOCAL ROLE lucra_app` e `set_config('lucra.claims', ..., true)`. As policies comparam `companies.owner_id` com `lucra_private.user_id()`. `lucra_app` é `nologin nobypassrls`.
2. **FKs compostas** `(company_id, id)`: um registro não consegue apontar para uma venda, produto ou conta de outra empresa, mesmo com um UUID válido.
3. **Aplicação**: `db.company(cid)` em cada rota e JWT obrigatório.

**Alternativas.** Um banco ou schema por loja (custo operacional); filtrar só na aplicação (uma falha expõe tudo).

**Consequências.**
- A identidade é *transaction-local*, compatível com o pooler em modo transação.
- **Limitação:** uma empresa tem um único dono (`owner_id`). Equipe, contador e convites exigem uma tabela de membership e a reescrita das policies (backlog).
- **Risco aberto:** a API conecta com a credencial de owner do banco e só rebaixa o privilégio via `SET ROLE`. O próximo passo é um role de login dedicado para a API, deixando o owner só para migrations.
