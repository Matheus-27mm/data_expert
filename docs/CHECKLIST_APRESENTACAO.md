# Checklist de apresentação — Lucra

Revisão realizada em **23/09/2026**, para a apresentação de **24/09/2026**.

**Resultado:** os fluxos verificados estão aptos à demonstração do controle financeiro e operacional. Use o roteiro abaixo e apresente integrações automáticas de ERP e envio de e-mails como recursos dependentes de implementação/configuração, não como serviços já ativos.

## 1. Acesso e ambiente publicado

- [x] Site abre em `https://dataexpert-eight.vercel.app`.
- [x] `/api/health` e `/api/ready` respondem HTTP 200; conexão Neon e cinco migrações verificadas.
- [x] Cadastro, saída, novo login, emissão do JWT e consulta autenticada testados **no Neon real**, com uma conta temporária de diagnóstico removida ao final.
- [x] Conta recém-criada não enxerga empresas de outros usuários.
- [x] Consulta sem autenticação a empresas retorna HTTP 401.
- [x] Login, mostrar/ocultar senha, pausa do vídeo, movimento reduzido, configurações e saída testados no navegador.
- [x] A empresa ativa é lembrada por usuário; criação adicional e troca ficam em Configurações.
- [ ] Antes da reunião: entrar com a conta que vocês usarão e confirmar o acesso no notebook da apresentação.

## 2. Revisão das telas

As **23 rotas** abaixo foram percorridas em Chromium nas larguras **1.440 e 360 px**, com dados de teste, sem erro de JavaScript nem rolagem horizontal da página. Tabelas largas e gráficos possuem rolagem interna. Os testes anteriores também cobrem 768 e 2.560 px nos fluxos principais.

| Área | Verificação |
| --- | --- |
| Visão geral e Análises | Indicadores, filtros, gráfico, radar e estados vazios |
| Produtos e Condições | Listagem, pesquisa, cadastro/edição e organização visual |
| Vendas, Devoluções e Recebimentos | Rotas, formulários e vínculos aos registros da empresa |
| Conciliação | Comparação entre valores esperados e recebidos |
| Despesas e Contas a pagar | Valores, vencimentos e registros de pagamento |
| Cadastrar conta e Pagar conta | Formulários e navegação contextual |
| Estoque e Movimentar estoque | Saldo, entrada e saída |
| Importações | Arquivo, colunas, prévia, validação e confirmação |
| Integrações | Origens, mapeamentos e histórico |
| Backups | Download e histórico de cópias |
| Relatórios e Agendamentos | PDF, histórico e indicação da necessidade de configurar envio |
| Importar recebimentos | Modelo CSV e validação |
| Planos de ação e Clientes | Cadastro e histórico de respostas/atendimentos |
| Configurações | Conta, empresa, taxas, backup e saída |

- [x] Axe: nenhuma ocorrência nas regras WCAG A/AA executadas nas 23 telas, após os ajustes desta revisão.
- [x] Inspeção visual de capturas de análise, produtos, importações, backups, planos e configurações; exemplos em `output/review/` (arquivos locais, não versionados).
- [x] Contraste de estados vazios corrigido.
- [x] Gráfico de cascata e exemplo de CSV passam a aceitar foco para rolagem por teclado.

Essa cobertura usa emulação de tamanhos em Chromium; não substitui testes em aparelhos físicos, Safari ou Firefox.

## 3. Cálculos e operações

- [x] Demonstração de agosto/2026 fecha em R$ 150.000,00 de receita, R$ 45.000,00 de estimativa, R$ 26.800,00 de deduções e R$ 18.200,00 de resultado das vendas.
- [x] Soma dos dias e dos produtos confere com o total mensal.
- [x] Períodos diário, semanal e mensal, mês sem vendas e fevereiro bissexto cobertos.
- [x] Simulador cobre margem negativa, arredondamentos e situações sem preço de equilíbrio possível.
- [x] Despesas, devoluções e recuperação de CMV entram no resultado operacional.
- [x] Criar conta a pagar gera a despesa uma única vez; pagamentos reduzem o saldo sem duplicar o gasto.
- [x] Pagamentos acima do saldo, devoluções acima dos limites e estoque negativo são bloqueados pelo banco.
- [x] Lançamentos financeiros permanecem imutáveis; correções usam os mecanismos de ajuste disponíveis.

**Explicação para o público:** resultado operacional não é saldo bancário nem apuração fiscal. Vendas e estoque são lançamentos separados; registrar uma venda não movimenta automaticamente o estoque. Condições cadastradas não recalculam vendas já informadas. O simulador de preço está na demonstração pública.

## 4. Importações e integrações

- [x] CSV e Excel (.xlsx) testados, incluindo valores em reais e datas.
- [x] Escolha de abas e rejeição de fórmulas cobertas nos testes do leitor.
- [x] Produtos, vendas e despesas têm modelos e validação próprios.
- [x] Origem de dados e mapeamento de colunas podem ser cadastrados e reutilizados.
- [x] Duplicidades são rejeitadas; conflito durante a gravação reverte o lote inteiro.
- [x] Histórico e vínculos da origem são persistidos junto com os registros.
- [x] Valores monetários excessivos são rejeitados **antes** da conversão para inteiros; regressão adicionada nesta revisão.

**Limites a informar:** CSV UTF-8 ou XLSX, até 2 MB, 1.000 registros e 40 colunas. A importação adiciona registros; não substitui automaticamente registros existentes. Conectores de ERP específicos ainda não estão implementados. Selecionar “API” cadastra uma intenção de integração, não inicia sincronização.

## 5. Relatórios e backups

- [x] PDFs diário, semanal e mensal cobertos por testes.
- [x] Relatório mensal baixado da produção, com valores conferidos e página renderizada para inspeção visual: sem cortes ou sobreposições observados.
- [x] Histórico de relatórios preserva os dados da geração.
- [x] Backup individual baixado e descompactado no teste de navegador, contendo produtos, clientes, atendimentos e histórico de importações.
- [x] Restauração testada em uma **nova empresa**, com vínculos refeitos e sem duplicação de despesas de contas.
- [x] Backup diário mais recente concluído e artifact criptografado existente, não expirado.
- [x] Rotina diária inclui dump geral e arquivo separado por empresa; retenção de 14 dias.

O download manual `.json.gz` não é criptografado e tem limite de 4 MB compactados. O backup agendado é criptografado. A recuperação é administrativa por CLI. Cópias de negócio não incluem contas/sessões do Neon Auth. O envio automático de relatórios por e-mail está desativado enquanto o SMTP não for configurado.

## 6. Isolamento e qualidade técnica

- [x] **47 testes de backend**, incluindo PostgreSQL real descartável, aprovados após os ajustes.
- [x] RLS testado entre proprietários: leitura, gravação, atualização e vínculos de registros de outra empresa são bloqueados nos cenários cobertos.
- [x] Históricos de clientes, planos, integrações, mapeamentos e backups cobertos pelo isolamento.
- [x] `.env` não é versionado; somente `.env.example` consta no Git.
- [x] `npm audit --omit=dev`: nenhum alerta conhecido nas dependências JavaScript de produção na data da revisão.
- [x] Build TypeScript/Vite concluído.
- [x] Quatro testes de navegador: autenticação, revisão das 23 telas, demonstração e fluxo completo de operação/importação/PDF/backup.

**Escopo da verificação:** testes funcionais, isolamento e revisão visual. Não houve teste de carga, pentest independente ou análise automatizada das vulnerabilidades de todos os pacotes Python. O build informa bundle JavaScript acima de 500 kB; funciona nos testes, mas ainda há oportunidade de otimização para conexões lentas.

## 7. O que mostrar como disponível — e o que não prometer

| Pode demonstrar | Apresentar com a ressalva correta |
| --- | --- |
| Indicadores, margem e resultado operacional | Não substitui contabilidade ou apuração tributária |
| Produtos, vendas, despesas, contas e estoque | Movimentação de estoque ainda é manual |
| Leitura e importação de CSV/Excel | Requer campos disponíveis e mapeamento correto |
| Planos de ação e respostas de clientes | Contatos são registrados manualmente; não envia WhatsApp |
| Histórico, PDF e backups por empresa | SMTP e recuperação administrativa têm configuração própria |
| Cadastro de origens e estrutura de integração | Conexão automática depende de desenvolver o conector do ERP |
| Acesso separado por proprietário | Não há convites para equipe, perfis de permissão ou redefinição de senha na interface atual |

## 8. Roteiro recomendado — 10 a 15 minutos

1. **Problema do cliente (1 min):** “Vender mais não significa lucrar mais. O Lucra organiza vendas, custos e despesas para mostrar o que sobra.”
2. **Demonstração pronta (2 min):** abrir `/#/demo/overview`, selecionar **Mensal / 31/08/2026** e mostrar R$ 45 mil estimados versus R$ 18,2 mil após deduções.
3. **Produtos no prejuízo e simulador (2 min):** mostrar o impacto do parcelamento e simular uma venda antes de conceder desconto.
4. **Empresa autenticada (2 min):** mostrar Produtos, Vendas, Contas a pagar e Estoque. Usar uma empresa explicitamente criada para demonstração, evitando dados reais de clientes na projeção.
5. **Importação (2 min):** usar um arquivo já conferido; mostrar leitura, colunas e prévia. O arquivo de teste `tests/fixtures/products.xlsx` foi validado. Confirmar apenas numa empresa de demonstração; repetir o mesmo SKU será bloqueado como duplicado.
6. **Análises e acompanhamento (2 min):** mostrar um plano de ação e um atendimento com a resposta do cliente.
7. **Entrega de valor (1 min):** gerar um PDF e mostrar Backups.
8. **Serviço de vocês (1 min):** explicar implantação, organização inicial dos dados e acompanhamento mensal. Para ERP, explicar que a integração depende de avaliação técnica.

## 9. Conferência final no local da apresentação

- [ ] Notebook com carregador, internet e navegador atualizados.
- [ ] Login feito e acesso confirmado na conta que será usada.
- [ ] Zoom do navegador em 100%; conferir projeção e legibilidade.
- [ ] Demonstração aberta em outra aba com agosto/2026 selecionado.
- [ ] Planilha de exemplo e PDF já baixados no notebook.
- [ ] Confirmar o nome da empresa ativa antes de gravar dados de demonstração.
- [ ] Não abrir `.env`, credenciais, logs sensíveis ou dados de clientes no projetor.
- [ ] Ter o PDF e capturas disponíveis como alternativa caso a internet falhe; o aplicativo depende da API online.

## Evidências

- Suíte: `python -m pytest backend -q` com `NEON_TEST_DATABASE_URL` apontando para PostgreSQL descartável.
- Navegador: `tests/browser/auth.spec.ts`, `review.spec.ts` e `workspace.spec.ts`.
- Backup verificado: [Scheduled operations — 35876130305](https://github.com/Matheus-27mm/data_expert/actions/runs/35876130305).
- PDF inspecionado e capturas: pasta local `output/review/`.
- Verificação real do login: conta temporária de diagnóstico criada e removida, sem alteração de dados das empresas existentes.
