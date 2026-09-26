# Architecture Decision Records

Decisões já tomadas no projeto, registradas em 26/09/2026 a partir do histórico
de desenvolvimento (16–24/09/2026). Formato: contexto, decisão, alternativas,
consequências. Uma decisão só muda com um novo ADR que substitui o anterior.

| # | Decisão | Status |
|---|---|---|
| [0001](0001-neon-em-vez-de-supabase.md) | Neon (Postgres + Auth) em vez de Supabase | Aceita |
| [0002](0002-isolamento-multiempresa.md) | Isolamento multiempresa por RLS + FKs compostas | Aceita |
| [0003](0003-monolito-modular-serverless.md) | Monólito modular FastAPI na Vercel | Aceita |
| [0004](0004-ledger-append-only-centavos.md) | Ledgers append-only em centavos inteiros | Aceita |
| [0005](0005-invariantes-no-banco.md) | Invariantes de domínio em triggers com advisory lock | Aceita |
| [0006](0006-vendas-importadas-sao-historico.md) | Venda importada é histórico e não movimenta estoque | Aceita |
| [0007](0007-integracao-erp-por-conector.md) | Integração com ERP por conector explícito | Aceita |
| [0008](0008-cache-de-token-no-cliente.md) | JWT reutilizado em memória até perto da expiração | Aceita |
