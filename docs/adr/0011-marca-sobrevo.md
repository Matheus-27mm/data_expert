# 0011 — Marca Sobrevo, identificadores técnicos inalterados

**Contexto.** Já existe outro sistema chamado "Lucra" no mesmo segmento. Em 01/10/2026 foram verificados cerca de 120 nomes (RDAP do registro.br e da Verisign, além de busca de mercado). Escolhido: **Sobrevo**, de "sobra" + "sobrevoo" (ver o negócio de cima), com sobrevo.com.br e sobrevo.com livres naquela data. A busca no INPI (classes 9, 35, 36 e 42) é responsabilidade dos sócios antes do registro da marca.

**Decisão.**
- Tudo que o cliente vê passa a Sobrevo: telas, logo (`public/brand/sobrevo-*.svg`, wordmark em Manrope 760 convertida em contornos + símbolo "S" geométrico), favicon, título da aba, PDFs, nomes dos arquivos baixados, e-mails, README e documentação.
- Identificadores técnicos mantêm `lucra`: roles e schema do PostgreSQL, claims RLS, a tabela de migrations, migrations já aplicadas (imutáveis por checksum), o formato `lucra-company` dos backups e as chaves de `localStorage`.

**Por quê.** Renomear roles e schemas em produção exige migrations destrutivas coordenadas com as credenciais, e o formato do backup é um contrato com arquivos já gerados. Nenhum desses nomes aparece para o cliente.

**Pendências fora do código.** Registrar os domínios; ajustar o nome da aplicação nos e-mails do Neon Auth (console do Neon); renomear o repositório e o projeto na Vercel, se desejado, e ligar o domínio próprio.
