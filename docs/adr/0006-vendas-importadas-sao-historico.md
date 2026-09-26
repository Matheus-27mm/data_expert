# 0006 — Venda importada é histórico e não movimenta estoque

**Contexto.** Clientes trazem histórico de vendas de ERPs ou planilhas cujo estoque já foi baixado na origem.

**Decisão.** Só o checkout integrado (`/sales/checkout`, com `product_id`) baixa estoque e gera recebíveis (`stock_managed=true`). Vendas importadas ou manuais ficam com `product_id` nulo e `stock_managed=false`. A devolução com reposição só vale para vendas integradas.

**Consequências.** Evita a baixa em dobro. Os dois tipos convivem em `sales`, e as telas os distinguem ("Integrada" × "Histórico / importação"). Uma venda com vários itens vira N linhas ligadas por `batch_reference`; um cabeçalho de pedido fica como evolução.
