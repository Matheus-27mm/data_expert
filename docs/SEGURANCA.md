# Revisão de segurança — 23/09/2026

## Escopo e conclusão

Revisão do código frontend/backend, rotas, validação JWT, políticas PostgreSQL RLS, dependências, empacotamento e objetos alcançáveis no histórico Git local. Os testes usam banco descartável e identidades independentes. A verificação do site publicado é somente de leitura, sem ataques de carga ou criação de contas reais.

Não foi encontrado um caminho de acesso aos dados de outra empresa nos testes realizados. Isso não é garantia de inexistência de falhas nem substitui uma auditoria independente da infraestrutura e dos provedores.

## Correções entregues

| Achado | Correção |
| --- | --- |
| Respostas privadas sem regra geral explícita contra cache | `Cache-Control: no-store` em todas as respostas da API, inclusive erros, PDF e downloads |
| Sem política de carregamento de conteúdo e proteção contra enquadramento | CSP, `frame-ancestors 'none'`, X-Frame-Options DENY, nosniff, política de referenciador e restrição de câmera/microfone/localização; HTTPS com HSTS |
| Limites de importação só depois da leitura/validação do corpo | Limite global de 4 MB antes do parsing, também contado em requisições transmitidas por partes; cabeçalho Authorization limitado a 16 KiB |
| Documentação técnica da API habilitada publicamente | Swagger, ReDoc e OpenAPI desativados por padrão; opção local `ENABLE_API_DOCS=1` |
| Ausência de verificações recorrentes de dependências/segredos no CI | Job de segurança com npm audit, pip-audit e varredura do histórico Git; exclusão adicional de arquivos de chave dos pacotes |

Documentação pública não era um bypass de autenticação; sua desativação reduz exposição de detalhes. A biblioteca de validação tenta detectar suporte a compilação dinâmica e recua para interpretação quando CSP bloqueia `eval`. A política mantém esse bloqueio; o formulário foi testado compilado, incluindo envio e tratamento de erro.

## Quem pode acessar

- Sem login: tela de acesso, arquivos públicos da interface, configuração pública do provedor de autenticação, saúde da API e demonstração com dados fictícios.
- Com conta: somente as empresas cujo proprietário corresponde ao identificador do token verificado. Criar conta não concede acesso às empresas de outros usuários.
- O cadastro permanece aberto. Não foi implementada aprovação comercial por convite ou bloqueio por plano nesta revisão.
- URLs, IDs de empresa, localStorage ou menus do React não concedem autorização. As rotas privadas verificam o JWT e o banco aplica RLS.
- JWT exige assinatura confiável, emissor, audiência, expiração e identificador; tokens anônimos ou adulterados são rejeitados. Um JWT já emitido pode continuar válido até expirar, mesmo após logout no provedor: não há revogação imediata por requisição implementada.

## Verificações e evidências

- 60 testes Python passaram, incluindo cada rota privada sem autenticação, assinatura adulterada, token expirado, emissor/audiência incorretos, filtros SQL parametrizados, isolamento de registros e vínculos entre empresas.
- Todas as 22 tabelas de aplicação foram verificadas com RLS habilitado, inclusive por consulta somente de metadados em produção. `lucra_app` não é superusuário, não ignora RLS e não aceita login direto. No banco de teste, uma identidade nova não lê registros em nenhuma tabela de empresa, mesmo sem filtro de empresa.
- 344 objetos do histórico Git foram examinados na revisão inicial; nenhum achado nos padrões pesquisados ou comparação com credenciais locais. O scanner não imprime valores encontrados. Arquivos públicos e build também são verificados.
- `npm audit`: nenhum aviso conhecido no lockfile examinado. `pip-audit -r requirements.txt`: nenhum aviso conhecido nas versões resolvidas na data. Dependências Python não estão travadas por hash; resoluções futuras são verificadas pelo CI, e isso não é inventário das versões de um deploy antigo.
- PDFs escapam texto de usuário; exportações Excel gravam identificadores e nomes como texto, sem executar fórmulas. O importador não executa fórmulas e limita arquivo descompactado.
- React renderiza os campos como texto; não foi encontrado uso de `dangerouslySetInnerHTML`. Tokens não são gravados explicitamente em localStorage pelo código do aplicativo.
- `.env`, arquivos temporários e artefatos de testes estão excluídos do Git e dos pacotes de deploy. O repositório GitHub é **público**: código fonte visível é esperado, credenciais e dados de clientes não.

## Limites operacionais que exigem acompanhamento

- WAF, limitação distribuída de requisições, proteção contra abuso de cadastro e MFA são configurações de Vercel/Neon/GitHub. Não foram auditadas nem alteradas nas contas dos provedores. O limite de corpo não substitui rate limiting.
- O servidor usa a conexão administrativa configurada e reduz privilégios para `lucra_app` nas operações de usuário. Separar a credencial de migrações da credencial de runtime é uma melhoria de defesa em profundidade pendente; nunca distribuir DATABASE_URL ao navegador.
- Não foram auditados colaboradores, tokens pessoais, sessões existentes, integrações externas, retenção ou permissões dos provedores. Mantenha MFA e revisão de acessos nessas contas.
- A CSP de Vercel permite conexão HTTPS com subdomínios Neon para autenticação; ao trocar o provedor/domínio, ajuste a política e repita o teste do frontend.
- Não se deve tornar o repositório privado ou revogar credenciais sem combinar os efeitos sobre colaboradores e deploy. Nenhuma credencial foi rotacionada nesta revisão, pois não houve evidência de vazamento no escopo examinado.

## Reproduzir

```powershell
python -m scripts.security_scan
npm audit
pip-audit -r requirements.txt
# NEON_TEST_DATABASE_URL deve apontar apenas para um banco descartável.
python -m pytest backend -q
npm run build
node scripts/browser_security.mjs
```
