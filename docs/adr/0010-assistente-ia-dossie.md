# 0010 — [Substituída por 0012] Assistente de IA: dossiê no servidor e uma chamada com saída estruturada

**Contexto.** O dono da empresa quer perguntar em linguagem natural ("por que meu lucro caiu?") e receber uma análise que possa exportar em PDF e transformar em ações. Restrições: isolamento entre empresas (ADR 0002), função da Vercel com limite de 60 s (ADR 0003) e custo previsível.

**Decisão.**
- `backend/assistant.py` monta um **dossiê** limitado da empresa sob a identidade RLS de quem pergunta: período atual e anterior, produtos e margens, despesas por categoria, contas a pagar, estoque, recebíveis, planos e clientes.
- **Uma chamada** a `claude-opus-5-5` (esforço `low`, `fallbacks: "default"`), com o dossiê na mensagem e a saída restrita por JSON Schema (`title`, `summary`, `highlights`, `sections`, `actions`, `caveats`), validada de novo com Pydantic. O prompt de sistema é estável e fica em cache.
- O modelo **não acessa o banco**: o isolamento continua todo no código e no RLS. Os textos digitados pela empresa vão como dados delimitados (`<dados_empresa>`), nunca como instrução.
- As respostas ficam em `assistant_reports` (append-only, com RLS). O PDF é gerado pelo servidor a partir do registro salvo, com todo texto do modelo escapado. As ações viram planos com um clique.
- Custo: limite diário por empresa (`ASSISTANT_DAILY_LIMIT`, padrão 20). Sem `ANTHROPIC_API_KEY`, a página informa que não está ativada e nada é chamado.

**Alternativas.** Agente com ferramentas consultando os dados: mais flexível, mas são várias idas e voltas, que estouram os 60 s, e a superfície de dados fica difícil de auditar. Resposta em Markdown renderizada no navegador: exigiria sanitizar HTML e deixaria o PDF frágil.

**Consequências.** Perguntas que precisam de dados fora do dossiê recebem um "falta registrar X", não uma resposta inventada. Ampliar o que a IA sabe significa ampliar `build_dossier`, que é testado. Se as análises passarem de ~50 s, o caminho é streaming até o navegador ou um job em segundo plano.
