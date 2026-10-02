# 0012 — Assistente com motor próprio de linguagem natural (substitui 0010)

**Contexto.** O ADR 0010 previa um modelo de linguagem externo. Os sócios decidiram não usar API externa: nenhum dado da empresa sai do sistema, não há custo por pergunta e nenhuma chave precisa ser gerida.

**Decisão.**
- `backend/insights.py` responde com um motor determinístico. Ele identifica os temas da pergunta por palavras-chave (resumo, produtos, caixa, comparação, despesas, estoque, clientes, prioridades), calcula os indicadores a partir do dossiê e escreve o texto em português com modelos de frase. Valores saem em formato brasileiro e a concordância de singular e plural é tratada.
- O dossiê (`build_dossier`, sob RLS), o contrato da resposta (`Answer`), o histórico (`assistant_reports`), o PDF e o "criar plano" continuam como no 0010. Só a geração do texto mudou.
- Recomendações saem de regras explícitas e testáveis: produto no prejuízo leva a revisar o preço; parcelamento longo leva a rever as condições; contas vencidas, parcelas atrasadas, despesas acima de 30% da receita, estoque sem saldo e período sem vendas geram cada um a sua ação.
- Sem limite diário e sem `ANTHROPIC_API_KEY`: a análise roda em milissegundos, dentro da própria API.

**Consequências.** As respostas são previsíveis e auditáveis, e uma mesma pergunta com os mesmos dados dá sempre a mesma resposta. Em troca, o motor só entende os temas que reconhece: uma pergunta fora deles recebe o resumo geral. Ampliar o assistente significa acrescentar temas e regras em `insights.py`, com testes em `test_assistant.py`.
