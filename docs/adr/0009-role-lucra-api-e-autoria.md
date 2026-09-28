# 0009 — Role de login dedicada à API e autoria dos lançamentos

**Contexto.** A API conecta ao Neon com a credencial de owner do banco e só rebaixa o privilégio com `SET LOCAL ROLE lucra_app` (ADR 0002). Um caminho de código que pulasse esse passo leria todas as empresas. Os lançamentos também não registravam quem os criou, o que bloqueia a entrada de equipes.

**Decisão.**
- A migration `009` cria `lucra_api` com `NOINHERIT`: a role não tem privilégio próprio em tabela nenhuma. Ela só acessa dados depois de `SET ROLE lucra_app`, onde o RLS se aplica. A única exceção é `select` em `lucra_migrations`, usado por `/api/ready`.
- A credencial de owner fica restrita ao GitHub Actions (migrations, backup, restore drill, relatórios).
- `created_at` e `created_by` entram em produtos e nos ledgers, com default `lucra_private.user_id()`: o banco atribui a autoria pela identidade da transação, sem mudar código.

**Alternativas.** Manter o owner na API, com a proteção dependendo só de disciplina de código. `FORCE ROW LEVEL SECURITY` para o owner, que quebraria backup e migrations.

**Consequências.** A migration cria a role sem login. A ativação é manual e fica fora do repositório, porque envolve uma senha:

1. Aplicar a `009`, que roda pelo CI após o merge.
2. No SQL Editor do Neon (branch production), como owner: `ALTER ROLE lucra_api LOGIN PASSWORD '<senha longa gerada>';`
3. Montar a connection string com o mesmo host pooler e o usuário `lucra_api`, e gravá-la como `DATABASE_URL` só em **Production** na Vercel. O secret `DATABASE_URL` do GitHub continua com o owner.
4. Redeploy e conferência: `/api/ready` deve responder `ok`, e o login com cadastro de um registro deve funcionar.
5. Rollback: voltar a `DATABASE_URL` da Vercel para a string do owner.

Registros anteriores à `009` ficam com autoria nula.
