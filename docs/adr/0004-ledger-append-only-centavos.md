# 0004 — Ledgers append-only em centavos inteiros

**Contexto.** Os números do sistema embasam decisões financeiras e relatórios preservados.

**Decisão.**
- Todo valor monetário é inteiro em centavos (`bigint` no banco, `int` na API; a conversão acontece só na borda da interface).
- `sales`, `adjustments`, `settlements`, `stock_movements` e `bill_payments` não têm policy de UPDATE: correção é um novo lançamento (devolução, estorno ou movimento inverso).
- Contas a pagar são reconhecidas na competência: um trigger cria a despesa ao lançar a conta, e o pagamento só abate o saldo.
- Relatórios guardam um *snapshot* dos números na geração (`report_history.snapshot`).

**Consequências.** Auditável e sem erro de arredondamento. Saldos são derivados na leitura (hoje em Python); com volume, vão precisar de agregação em SQL ou snapshots. Faltam `created_at`/`created_by` em vendas, produtos e despesas: resolver junto com a entrada de equipes.
