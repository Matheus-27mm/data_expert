# 0007 — Integração com ERP por conector explícito

**Contexto.** Nenhum cliente definido ainda; ERPs variam (Bling e Omie têm API).

**Decisão.** A porta de entrada universal é a importação guiada de CSV/XLSX (mapeamento por empresa, rastreio em `import_jobs`/`source_records`). APIs de ERP entram por um contrato (`backend/connectors.py`: `Connector.fetch` com cursor retomável e `SourceEvent` com revisão), com um adaptador registrado por fornecedor. Atualizações e cancelamentos exigem regra explícita por conector.

**Consequências.** Não se promete integração antes da avaliação técnica. O primeiro conector será escolhido pelo primeiro cliente (plano Pro).
