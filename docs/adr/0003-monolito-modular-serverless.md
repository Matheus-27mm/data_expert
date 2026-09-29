# 0003 — Monólito modular FastAPI na Vercel

**Contexto.** Equipe de duas pessoas, poucos clientes, demanda de lançamento rápido.

**Decisão.** Um único backend FastAPI, organizado por módulo (workspace, trading, spreadsheets, integrations, company_backup), publicado como Vercel Function. O mesmo código roda em Docker (`Dockerfile`, `compose.yaml`) para uma eventual VPS.

**Alternativas.** Microserviços (rejeitado: o gargalo medido era I/O, não acoplamento); VPS agora (adiada em 21/09: mais operação sem ganho imediato).

**Consequências.**
- `maxDuration` de 60 s: importações grandes, backups e relatórios pesados precisarão de fila e worker quando crescerem.
- Sem estado entre invocações: caches em processo (`lru_cache`) valem por instância.
- Rever quando houver jobs longos ou processos contínuos; o Docker já existe para essa mudança.
