# 0005 — Invariantes de domínio em triggers com advisory lock

**Contexto.** Requisições concorrentes (duplo clique, duas abas) não podem, por exemplo, deixar o estoque negativo.

**Decisão.** Triggers `BEFORE INSERT` validam: estoque ≥ 0 (`validate_stock`), pagamento ≤ saldo da conta, devolução ≤ receita/CMV da venda, recebimento ≤ esperado (vendas integradas). Cada um serializa por entidade com `pg_advisory_xact_lock(hashtextextended(id, seed))`. O checkout usa as mesmas chaves, e o lock é reentrante na transação.

**Alternativas.** Validar só na aplicação (sofre race condition); `SELECT ... FOR UPDATE` numa linha de saldo (exigiria tabela de saldos).

**Consequências.** Correto sob concorrência, independente do cliente. O custo é recalcular a soma do ledger a cada inserção (O(n) por produto ou conta); com volume, manter um saldo materializado.
