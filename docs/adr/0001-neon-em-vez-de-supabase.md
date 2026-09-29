# 0001 — Neon (Postgres + Auth) em vez de Supabase

**Contexto.** O projeto começou prevendo Supabase. Em 18/09/2026 a conta já tinha os dois projetos permitidos no plano gratuito.

**Decisão.** Usar Neon: PostgreSQL gerenciado (endpoint com pooler) e Neon Auth (Better Auth) para cadastro e sessão. A API valida o JWT via JWKS (`backend/neon_auth.py`) e acessa o banco com psycopg.

**Alternativas.** Pausar um projeto Supabase; Postgres próprio numa VPS.

**Consequências.**
- Sem PostgREST/Data API: o acesso a dados é código próprio (`neon_repository.Session`). A interface dele ainda imita o PostgREST (filtros como `eq.`/`gte.` em string), herança do desenho inicial.
- O emissor do token de usuário difere do anônimo, e o relógio do provedor pode divergir: validação com `issuer` explícito e `leeway=30` s (corrigido em 22/09).
- Domínios públicos precisam estar em *trusted domains* do Neon Auth, ou o cadastro falha com `INVALID_ORIGIN`.
