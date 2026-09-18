# Lucra — clareza para decidir melhor

**Dashboard de análise de margem que mostra quanto realmente sobra de cada venda.**

O Lucra organiza vendas, custos e taxas para ajudar o empresário a identificar produtos que vendem muito, mas geram prejuízo, entender as deduções que reduzem o resultado e simular condições de pagamento antes de fechar uma venda.

[![Validação do projeto](https://github.com/Matheus-27mm/data_expert/actions/workflows/ci.yml/badge.svg)](https://github.com/Matheus-27mm/data_expert/actions/workflows/ci.yml)

**[Acessar demonstração](https://dataexpert-eight.vercel.app)** · **[Repositório](https://github.com/Matheus-27mm/data_expert)** · **[Documentação da API](https://dataexpert-eight.vercel.app/api/docs)**

> **Demonstração e área autenticada.** O modo demonstrativo funciona sem credenciais. A área da empresa usa Neon PostgreSQL e Neon Auth e exige configurar o ambiente e aplicar as migrações. A conexão com o projeto remoto deve ser validada antes de cadastrar dados reais.

## Sumário

- [1. Visão do produto](#1-visão-do-produto)
- [2. Funcionalidades](#2-funcionalidades)
- [3. Tecnologias e arquitetura](#3-tecnologias-e-arquitetura)
- [4. Estrutura do repositório](#4-estrutura-do-repositório)
- [5. Início rápido com Docker](#5-início-rápido-com-docker)
- [6. Ambiente de desenvolvimento](#6-ambiente-de-desenvolvimento)
- [7. Configuração](#7-configuração)
- [8. Dados demonstrativos](#8-dados-demonstrativos)
- [9. Regras de cálculo](#9-regras-de-cálculo)
- [10. Referência da API](#10-referência-da-api)
- [11. Relatórios em PDF](#11-relatórios-em-pdf)
- [12. Neon e modelo de dados](#12-neon-e-modelo-de-dados)
- [13. Publicação na Vercel](#13-publicação-na-vercel)
- [14. Testes e integração contínua](#14-testes-e-integração-contínua)
- [15. Fluxo de colaboração](#15-fluxo-de-colaboração)
- [16. Solução de problemas](#16-solução-de-problemas)
- [17. Operação e configuração dos serviços](#17-operação-e-configuração-dos-serviços)

## 1. Visão do produto

Uma empresa pode apresentar bom faturamento e perder dinheiro em determinadas vendas. Considerar somente preço e custo do produto esconde o impacto de impostos, comissões e taxas do cartão, especialmente quando há antecipação de recebíveis.

O Lucra responde a quatro perguntas:

1. **Quanto vendemos?** Receita e quantidade de unidades no período.
2. **Quanto parece que lucramos?** Receita menos o custo das mercadorias.
3. **Quanto sobra após as deduções?** Resultado após impostos, cartão e comissões.
4. **Essa próxima venda vale a pena?** Simulação de preço, custo e parcelamento.

Na demonstração mensal, uma estimativa de **R$ 45.000,00** se transforma em **R$ 18.200,00** após as deduções consideradas.

> O indicador representa o resultado das vendas antes de despesas fixas. Não é saldo bancário, lucro contábil ou apuração fiscal.

## 2. Funcionalidades

| Recurso | Comportamento | Estado |
| --- | --- | --- |
| Visão geral | Cards de receita, lucro estimado, resultado e deduções | Implementado |
| Lucro ilusório vs. real | Comparação dos resultados e evolução acumulada | Implementado |
| Deduções | Impostos, cartão/antecipação e comissões | Implementado |
| Produtos e margens | Busca por nome ou categoria; ordenação por unidades vendidas | Implementado |
| Itens no prejuízo | Destaque para grupos de produtos com resultado negativo | Implementado |
| Cascata | Receita e deduções calculadas com os dados do período | Implementado |
| Simulador | Preço, CMV, parcelas e taxas editáveis, com cálculo pela API | Implementado |
| Filtros | Dia, semana ou mês, definidos por uma data de referência | Implementado |
| Relatórios | Download de PDF com o período selecionado | Implementado |
| Responsividade | Colunas adaptáveis e navegação inferior no celular | Implementado |
| Estados da interface | Carregamento, erro, ausência de vendas e busca sem resultado | Implementado |
| Docker | Imagem com frontend e backend, healthcheck e Compose | Implementado |
| Vercel | Frontend estático e API Python no mesmo domínio | Configurado |
| GitHub Actions | Build frontend, testes backend e verificação Docker | Configurado |
| Neon | PostgreSQL, login e isolamento por empresa | Exige configuração do projeto |
| Login e dados reais | Neon Auth, seleção de empresa e persistência | Implementado; contas e domínios configurados no Neon |
| Importação e cadastro | CSV com prévia, duplicidades e confirmação atômica; cadastros financeiros | Implementado |
| Estoque | Entradas, saídas, saldo por produto e bloqueio de saldo negativo | Implementado |
| Contas a pagar | Vencimentos, pagamentos parciais e saldo pendente | Implementado |
| Extrato CSV | Recebimentos vinculados por identificador de venda | Implementado |
| Operação | Logs com request ID e endpoint de prontidão | Implementado |

As telas compartilham o período selecionado. O simulador é independente: alterar suas taxas não modifica as vendas fictícias, os indicadores ou o PDF.

## 3. Tecnologias e arquitetura

| Camada | Tecnologia | Responsabilidade |
| --- | --- | --- |
| Interface | React 19 + TypeScript 5 | Componentes, estados e interação |
| Build frontend | Vite 6 | Servidor local, proxy e bundle de produção |
| Estilos e ícones | CSS responsivo + Lucide React | Layout e identidade visual |
| API | Python + FastAPI + Pydantic | Rotas HTTP e validação de entrada |
| Análise | pandas | Filtros, agrupamentos e agregações |
| PDF | ReportLab | Geração do relatório no backend |
| Acesso ao banco | psycopg 3 | SQL parametrizado e transações PostgreSQL |
| Autenticação | Neon Auth + PyJWT | Login e validação de assinatura, emissor, destinatário e expiração |
| Testes | pytest | Verificação de cálculos e endpoints |
| Banco | Neon/PostgreSQL | Dados persistidos com Row Level Security |
| Containers | Docker + Docker Compose | Execução do sistema completo |
| Entrega | GitHub Actions + Vercel | Validação automatizada e publicação |

Node.js **22** e Python **3.12** são as referências do CI e do Docker. O JavaScript utiliza `package-lock.json`; os requisitos Python utilizam intervalos de versão.

```mermaid
flowchart LR
    U[Empresário] --> R[React / TypeScript]
    R -->|HTTP /api| A[FastAPI]
    A --> F[Regras financeiras + pandas]
    F --> D[Dados fictícios em memória]
    A --> P[ReportLab]
    P -->|Download| PDF[Relatório PDF]
    R --> N[Neon Auth]
    A --> S[Neon PostgreSQL / RLS]
```

### Fluxo dos dados

1. O backend gera uma base determinística com `demo_sales()` ao carregar a aplicação.
2. O React envia período e data para `/api/dashboard`.
3. `summarize()` filtra vendas e produz totais, grupos de produtos e valores diários.
4. O React formata a moeda e acumula a série diária no gráfico.
5. A exportação chama `/api/reports/pdf`, reutilizando a mesma função de resumo.
6. O simulador envia suas premissas a `/api/simulate` e recebe deduções e resultado por unidade.

### Ambientes

| Ambiente | Frontend | Backend | Endereço principal |
| --- | --- | --- | --- |
| Desenvolvimento | Vite na porta 5173 | Uvicorn na porta 8000 | `http://127.0.0.1:5173` |
| Docker local | Build servido pelo FastAPI | Mesmo container, porta interna 8000 | `http://127.0.0.1:8080` |
| Vercel | Arquivos estáticos de `dist` | Função Python via `api/index.py` | `https://dataexpert-eight.vercel.app` |

Em desenvolvimento, `vite.config.ts` encaminha `/api` para a porta 8000. No Docker e na Vercel, frontend e API utilizam a mesma origem.

## 4. Estrutura do repositório

```text
data_expert/
├── .github/workflows/ci.yml         # Validações do GitHub Actions
├── api/index.py                    # Entrypoint ASGI da Vercel
├── backend/
│   ├── __init__.py
│   ├── main.py                     # Rotas, modelos e arquivos estáticos
│   ├── finance.py                  # Dados demonstrativos e cálculos
│   ├── report.py                   # Composição do PDF
│   ├── neon_repository.py          # PostgreSQL com identidade RLS por transação
│   ├── test_finance.py             # Testes de cálculo e API
│   └── requirements.txt            # Dependências de desenvolvimento/testes
├── src/
│   ├── main.tsx                    # Telas, componentes e chamadas à API
│   └── styles.css                  # Estilos e responsividade
├── neon/migrations/
│   └── 001_initial.sql             # Tabelas, índice e políticas RLS
├── .dockerignore                   # Exclusões do contexto Docker
├── .env.example                    # Modelo de variáveis Neon
├── .gitignore                      # Exclusões do Git
├── .python-version                 # Versão Python para deploy
├── .vercelignore                   # Exclusões de upload
├── compose.yaml                    # Serviço Docker local
├── Dockerfile                      # Build em etapas: Node e Python
├── index.html                      # HTML inicial
├── package.json                    # Dependências e scripts frontend
├── package-lock.json               # Versões resolvidas pelo npm
├── requirements.txt                # Dependências Python de execução
├── tsconfig.json                   # Configuração TypeScript
├── vercel.json                     # Build, função e reescrita de rotas
├── vite.config.ts                  # Vite e proxy local
└── README.md
```

`node_modules`, `dist`, `.venv`, `.vercel`, caches, arquivos `.env`, `tmp` e `output` não são versionados. `.env.example` contém somente valores ilustrativos.

## 5. Início rápido com Docker

Executa a aplicação completa sem exigir Node ou Python instalados diretamente na máquina.

### Pré-requisitos

- Git.
- Docker Desktop iniciado com containers Linux, ou Docker Engine com Compose.
- Porta local `8080` livre.

### Iniciar

```bash
git clone https://github.com/Matheus-27mm/data_expert.git
cd data_expert
docker compose up -d --build
```

Se o repositório já estiver clonado, execute apenas o último comando na pasta existente.

- Dashboard: [http://127.0.0.1:8080](http://127.0.0.1:8080).
- Saúde: [http://127.0.0.1:8080/api/health](http://127.0.0.1:8080/api/health).
- Swagger: [http://127.0.0.1:8080/api/docs](http://127.0.0.1:8080/api/docs).

### Operação

| Ação | Comando |
| --- | --- |
| Consultar estado e saúde | `docker compose ps` |
| Acompanhar logs | `docker compose logs -f dashboard` |
| Consultar últimos logs | `docker compose logs --tail 100 dashboard` |
| Parar sem remover o container | `docker compose stop` |
| Iniciar container existente | `docker compose start` |
| Recriar após alterar código | `docker compose up -d --build` |
| Parar e remover containers e rede deste projeto | `docker compose down` |

### Funcionamento da imagem

- `node:22-alpine` instala dependências com `npm ci` e compila o React.
- `python:3.12-slim` instala os requisitos de execução e recebe backend e `dist`.
- O processo roda como `appuser`, sem privilégios de root.
- `STATIC_DIR=/app/dist` habilita os arquivos estáticos no FastAPI.
- O healthcheck consulta `/api/health` a cada 30 segundos, com timeout de 5 segundos, período inicial de 15 segundos e limite de 3 falhas.
- O Compose configura `restart: unless-stopped` e `init: true`.

A imagem se chama `lucra-dashboard:local`. O mapeamento `127.0.0.1:8080:8000` permite acesso somente pela própria máquina. Não existem volumes ou banco no Compose atual: os dados fictícios são recriados em memória.

> Construir a imagem local não a publica em um registry. Não há envio automático para Docker Hub ou GHCR. Hospedar em outro servidor exige configurar o destino, acesso de rede e HTTPS.

## 6. Ambiente de desenvolvimento

### Pré-requisitos

Git, Node.js 22, npm, Python 3.12, pip e portas `5173` e `8000` disponíveis.

### 6.1. Clonar e instalar o frontend

```bash
git clone https://github.com/Matheus-27mm/data_expert.git
cd data_expert
npm ci
```

### 6.2. Criar um ambiente Python isolado

**Windows / PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Se `py` não estiver disponível, use `python -m venv .venv` após confirmar a versão com `python --version`. Usar o executável do ambiente diretamente evita a necessidade de alterar a política de execução do PowerShell.

**Linux / macOS:**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

### 6.3. Iniciar a API

Mantenha este terminal aberto, na raiz do projeto.

**Windows / PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Linux / macOS:**

```bash
.venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 6.4. Iniciar a interface

Em outro terminal, também na raiz:

```bash
npm run dev
```

Abra [http://127.0.0.1:5173](http://127.0.0.1:5173). A documentação da API fica em [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs). Use `Ctrl+C` em cada terminal para encerrar os processos.

### Scripts frontend

| Comando | Finalidade |
| --- | --- |
| `npm run dev` | Inicia o Vite com atualização durante o desenvolvimento |
| `npm run build` | Verifica TypeScript e gera `dist` |
| `npm run preview` | Visualiza o bundle compilado; não inicia a API |

O frontend depende da API para os indicadores e o simulador. Para validar a aplicação compilada completa, prefira Docker, que serve frontend e backend na mesma origem.

## 7. Configuração

A demonstração não exige credenciais. Para a área da empresa, crie `.env` na raiz a partir de `.env.example`. O backend carrega esse arquivo automaticamente, sem sobrescrever variáveis já definidas no servidor. O arquivo `.env` fica fora do Git e da imagem Docker.

```env
DATABASE_URL=postgresql://USUARIO:SENHA@HOST/neondb?sslmode=require&channel_binding=require
NEON_AUTH_URL=https://SEU-ENDPOINT/neondb/auth
```

Copie a URL completa do banco em **Neon → Connect → Postgres database**. Use a conexão com pooling para a aplicação. Em **Connect → Auth**, copie a URL pública de autenticação. Não use os asteriscos da senha mascarada como senha real.

| Variável | Finalidade | Exposição |
| --- | --- | --- |
| `DATABASE_URL` | Conexão PostgreSQL, incluindo senha | Privada; somente servidor |
| `NEON_AUTH_URL` | Endpoint público do Neon Auth | Pode ser enviado ao navegador |
| `NEON_AUTH_JWKS_URL` | Opcional; padrão: Auth URL + `/.well-known/jwks.json` | URL das chaves públicas |
| `NEON_AUTH_ISSUER` | Opcional; padrão: Auth URL | Emissor esperado do JWT |
| `NEON_AUTH_AUDIENCE` | Opcional; padrão: origem da Auth URL, sem o caminho `/neondb/auth` | Destinatário esperado do JWT |
| `STATIC_DIR` | Diretório do frontend compilado | `/app/dist` no Docker |

Os parâmetros JWT devem corresponder à configuração do seu projeto; a API rejeita tokens com assinatura, emissor, destinatário ou validade incorretos. Nunca desative a verificação para contornar um erro de login.

Cadastre `http://localhost:5173`, `http://127.0.0.1:5173` e a origem publicada da aplicação nos domínios permitidos do Neon Auth. Adicione `http://127.0.0.1:8080` se utilizar Docker local. Configure também a verificação de e-mail no provedor.

Não coloque `DATABASE_URL` em variáveis com prefixo `VITE_`. O endpoint `/api/config` retorna somente o estado da configuração e a URL pública de autenticação.

No Docker, Compose lê `.env` e injeta suas variáveis no container. Na Vercel, cadastre as mesmas variáveis em **Settings → Environment Variables** e faça um novo deploy; o arquivo local não é enviado.

## 8. Dados demonstrativos

A empresa fictícia é a **Casa Nova Store**. A base possui 6 produtos e 960 registros, cada um com uma unidade: 480 vendas em julho de 2026 e 480 em agosto de 2026. Os valores mensais são iguais e distribuídos deterministicamente pelos dias.

A data inicial selecionada é **31/08/2026**, no período mensal.

### Resultado de cada mês

| Indicador | Valor |
| --- | ---: |
| Faturamento | R$ 150.000,00 |
| CMV | R$ 105.000,00 |
| Lucro estimado | R$ 45.000,00 |
| Impostos estimados | R$ 9.000,00 |
| Cartão e antecipação | R$ 12.000,00 |
| Comissões | R$ 5.800,00 |
| Deduções após CMV | R$ 26.800,00 |
| Resultado das vendas | **R$ 18.200,00** |
| Margem de contribuição | **12,13%** |

### Produtos com prejuízo no mês

| Produto | Unidades | Parcelas | Margem | Resultado |
| --- | ---: | ---: | ---: | ---: |
| Fone Bluetooth Pulse | 120 | 12x | -12% | -R$ 2.880,00 |
| Smartwatch Connect | 90 | 12x | -13% | -R$ 2.340,00 |
| Caixa de Som Mini | 80 | 10x | -10% | -R$ 1.600,00 |

### Períodos

| Seleção | Intervalo considerado |
| --- | --- |
| Diário | Somente a data de referência |
| Semanal | Segunda-feira a domingo da semana que contém a data |
| Mensal | Primeiro ao último dia do mês da data |

Os limites são inclusivos. Uma semana pode atravessar meses: `31/08/2026` considera `31/08/2026` a `06/09/2026`. Dias sem registros recebem valores zerados. Fora da base demonstrativa, o dashboard apresenta totais zerados e lista de produtos vazia.

## 9. Regras de cálculo

### 9.1. Unidades e arredondamento

Os valores monetários da base e das respostas da API são **inteiros em centavos**. `1820000` representa `R$ 18.200,00`.

O simulador recebe preço e custo em **reais**, com até duas casas decimais, e os converte para centavos. Taxas são percentuais: `6` significa `6%`.

As deduções monetárias usam `ROUND_HALF_UP`. O preço de equilíbrio é arredondado para cima. A interface formata moeda em `pt-BR` e pode exibir percentuais com menos casas decimais que a API.

### 9.2. Dashboard

```text
Lucro estimado = receita - CMV
Deduções = impostos + cartão/antecipação + comissões
Resultado das vendas = lucro estimado - deduções
Margem (%) = resultado das vendas / receita × 100
```

Sem receita, a margem retornada é zero. Os produtos são agrupados por nome, categoria e parcelas, ordenados por unidades vendidas decrescentes; em empate, pelo resultado crescente.

O campo `daily` contém valores de cada dia. O gráfico React acumula esses valores dentro do período selecionado.

### 9.3. Simulador

| Premissa padrão | Valor |
| --- | ---: |
| Imposto | 6% |
| Comissão | 4% |
| Cartão / MDR | 2% |
| Antecipação | 1,5% ao mês |

```text
Prazo médio = (número de parcelas + 1) / 2
Taxa total de cartão (%) = MDR + antecipação mensal × prazo médio
Dedução de cada taxa = preço de venda × taxa / 100
Resultado = preço - CMV - imposto - comissão - cartão
Preço de equilíbrio = CMV / (1 - soma das taxas / 100)
```

O modelo considera a primeira parcela em 30 dias e utiliza uma aproximação linear. Contratos reais podem adotar outro cálculo. Com soma de taxas igual ou superior a 100%, a API retorna `breakeven: null`.

**Exemplo:** preço de R$ 200,00, custo de R$ 180,00 e 12 parcelas com taxas padrão:

| Etapa | Resultado |
| --- | ---: |
| Prazo médio | 6,5 meses |
| Taxa total de cartão | 11,75% |
| Imposto | R$ 12,00 |
| Cartão e antecipação | R$ 23,50 |
| Comissão | R$ 8,00 |
| Resultado por unidade | **-R$ 23,50** |
| Margem | **-11,75%** |
| Preço de equilíbrio calculado | **R$ 230,04** |

O equilíbrio é uma referência matemática: arredondamentos individuais podem produzir diferenças de centavos. Ele não inclui despesas fixas ou uma margem desejada.

### 9.4. Cascata

O waterfall usa os totais do período selecionado: receita, CMV, impostos, cartão e comissões. Na área da empresa, inclui despesas, devoluções e CMV recuperado. O último valor representa o resultado calculado, inclusive quando negativo. As taxas do simulador não alteram esse gráfico.

## 10. Referência da API

- Swagger UI: `/api/docs`.
- ReDoc: `/api/redoc`.
- OpenAPI: `/api/openapi.json`.

As rotas demonstrativas desta seção são públicas e trabalham com dados fictícios. As rotas autenticadas de cadastro, importação e persistência estão documentadas na seção 12.

| Método | Rota | Finalidade |
| --- | --- | --- |
| `GET` | `/api/health` | Saúde da aplicação |
| `GET` | `/api/dashboard` | Indicadores, produtos e série diária |
| `POST` | `/api/simulate` | Simulação de uma venda |
| `GET` | `/api/reports/pdf` | Relatório do período |

### 10.1. Saúde

```http
GET /api/health
```

```json
{"status":"ok","mode":"demo"}
```

Confirma que a API responde; não testa conectividade com o Neon nem o estado das migrações.

### 10.2. Dashboard

```http
GET /api/dashboard?period=monthly&anchor=2026-08-31
```

| Parâmetro | Valores | Padrão |
| --- | --- | --- |
| `period` | `daily`, `weekly` ou `monthly` | `monthly` |
| `anchor` | Data ISO `AAAA-MM-DD` | `2026-08-31` |

| Campo da resposta | Conteúdo |
| --- | --- |
| `start`, `end` | Limites inclusivos em formato ISO |
| `period` | Tipo de período |
| `totals` | Receita, CMV, deduções, quantidade, estimativa, resultado e margem |
| `products` | Grupos com nome, categoria, quantidade, parcelas, receita, resultado e margem |
| `daily` | Dias com `date`, `estimated` e `net` |
| `source` | `demo` na implementação atual |

Objeto `totals` de agosto de 2026:

```json
{
  "revenue": 15000000,
  "cmv": 10500000,
  "tax": 900000,
  "card": 1200000,
  "commission": 580000,
  "quantity": 480,
  "estimated": 4500000,
  "hidden": 2680000,
  "net": 1820000,
  "margin": 12.13
}
```

### 10.3. Simulação

```http
POST /api/simulate
Content-Type: application/json
```

```json
{
  "price": 200,
  "cost": 180,
  "installments": 12,
  "tax_rate": 6,
  "commission_rate": 4,
  "card_base": 2,
  "anticipation_rate": 1.5
}
```

| Campo | Obrigatório | Limites |
| --- | --- | --- |
| `price` | Sim | Maior que zero, até R$ 10.000.000,00; até 2 casas decimais |
| `cost` | Sim | De zero a R$ 10.000.000,00; até 2 casas decimais |
| `installments` | Sim | Inteiro de 1 a 12 |
| `tax_rate` | Não | 0 a 50%; padrão 6 |
| `commission_rate` | Não | 0 a 50%; padrão 4 |
| `card_base` | Não | 0 a 50%; padrão 2 |
| `anticipation_rate` | Não | 0 a 20% ao mês; padrão 1,5 |

Resposta, com moeda em centavos:

```json
{
  "price": 20000,
  "cost": 18000,
  "tax": 1200,
  "commission": 800,
  "card": 2350,
  "net": -2350,
  "margin": -11.75,
  "card_rate": 11.75,
  "breakeven": 23004
}
```

Entradas fora dos tipos ou limites recebem HTTP `422`, com detalhes de validação. Resultado financeiro negativo é uma resposta válida, com HTTP `200`.

### 10.4. Exemplos no PowerShell

```powershell
# Docker local. Para desenvolvimento, troque 8080 por 8000.
$lucraBaseUrl = 'http://127.0.0.1:8080'

Invoke-RestMethod "$lucraBaseUrl/api/health"
Invoke-RestMethod "$lucraBaseUrl/api/dashboard?period=monthly&anchor=2026-08-31"

$lucraSimulation = @{
    price = 200
    cost = 180
    installments = 12
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "$lucraBaseUrl/api/simulate" -ContentType 'application/json' -Body $lucraSimulation
```

## 11. Relatórios em PDF

Na interface, selecione período e data e use **Exportar relatório**. A tela **Relatórios** oferece o mesmo download.

```http
GET /api/reports/pdf?period=monthly&anchor=2026-08-31
```

A resposta utiliza `Content-Type: application/pdf` e `Content-Disposition: attachment`. O nome segue `lucra-{period}-{anchor}.pdf`.

O documento inclui empresa e intervalo, resumo financeiro, produtos no prejuízo, comentário sobre deduções, metodologia, limitações e paginação.

O PDF usa os mesmos dados agregados do dashboard. Não inclui a simulação digitada pelo usuário nem reproduz os gráficos da interface. É gerado em memória e enviado na resposta, sem armazenamento permanente pelo backend.

```powershell
New-Item -ItemType Directory -Force output/pdf | Out-Null
Invoke-WebRequest -Uri 'http://127.0.0.1:8080/api/reports/pdf?period=monthly&anchor=2026-08-31' -OutFile 'output/pdf/lucra-mensal-agosto-2026.pdf'
```

## 12. Neon e modelo de dados

### Preparação do banco

Depois de preencher `.env` e instalar as dependências Python:

```powershell
python -m scripts.migrate
```

O comando aplica `neon/migrations/*.sql` em ordem, em uma transação, e registra nome e checksum em `lucra_migrations`. Execuções seguintes pulam migrações já aplicadas. Mudanças em arquivos aplicados são rejeitadas: crie uma nova migração. Use o proprietário do banco na preparação inicial, pois ela cria e concede a role `lucra_app`.

### Modelo persistido

| Tabela | Conteúdo |
| --- | --- |
| `companies` | Empresa e identificador do proprietário autenticado |
| `products` | SKU, nome, categoria, custo, preço e estado ativo |
| `sales` | Identificador externo único por empresa, data, quantidade, receita e deduções |
| `expenses` | Despesas operacionais por data e categoria |
| `adjustments` | Devoluções e estornos vinculados à venda original |
| `settlements` | Recebimentos com referência bancária única por empresa |
| `payment_terms` | Condições de parcelamento e taxas cadastradas |
| `report_history` | Snapshot financeiro usado em cada PDF |
| `report_schedules` | Periodicidade, destinatário confirmado e estado do agendamento |
| `report_deliveries` | Controle de execução e prevenção de envios repetidos |
| `stock_movements` | Entradas e saídas por produto, com referência única |
| `bills` | Fornecedor, competência, vencimento e valor devido |
| `bill_payments` | Baixas parciais ou totais de cada conta |

Valores monetários são inteiros em centavos. Nas vendas, representam totais do registro, não valores unitários. A API recebe o token do Neon Auth, valida-o e abre uma transação com `SET LOCAL ROLE lucra_app`. A identidade validada fica em uma configuração local à transação, utilizada pelas políticas RLS. A role não tem login nem permissão para ignorar RLS. O navegador nunca acessa a credencial PostgreSQL.

Cada empresa pertence a um usuário. As políticas limitam consultas e gravações às empresas desse proprietário. Não há compartilhamento por convites nesta versão. Vendas, despesas e ajustes são lançamentos imutáveis; produtos, condições e agendamentos permitem edição. O banco impede devoluções acumuladas acima da receita ou do CMV original.

### Uso da área da empresa

1. Abra `/#/workspace/dashboard` e crie sua conta ou faça login.
2. Crie uma empresa e selecione-a no cabeçalho.
3. Cadastre produtos e vendas ou importe um CSV pela tela **Importar CSV**.
4. Registre despesas, recebimentos e devoluções para compor o resultado operacional.
5. Consulte a conciliação e gere relatórios preservados no histórico.
6. Em **Movimentar estoque**, registre o saldo inicial, entradas e saídas. O cadastro de uma venda não movimenta estoque automaticamente; registre a saída correspondente.
7. Em **Cadastrar conta**, informe fornecedor, competência, vencimento e valor. A despesa é reconhecida automaticamente na competência; não cadastre a mesma despesa novamente.
8. Em **Pagar conta**, registre cada baixa. Pagamentos não duplicam a despesa, e valores acima do saldo são bloqueados. **Contas a pagar** exibe pendências e vencimentos.
9. Em **Importar recebimentos**, envie um CSV com `reference,external_id,received_on,amount`. Use uma linha por crédito identificado: vendas desconhecidas e referências repetidas bloqueiam o lote. A prévia sempre precede a confirmação.

Estoque, contas e pagamentos são registros imutáveis. O estoque admite correção por movimento inverso. Não existe cancelamento/edição de contas já lançadas nesta versão; confira os valores antes de confirmar.

O CSV utiliza vírgulas, datas `AAAA-MM-DD` e valores em reais com ponto decimal. Há limite de 1.000 vendas e 2 MB por envio. Baixe o modelo na interface, confira a prévia e confirme a importação. Um conflito cancela todo o lote. O identificador externo evita importar novamente a mesma venda.

### API autenticada

Todas estas rotas exigem `Authorization: Bearer <JWT>`:

| Método | Rota sob `/api/workspace` | Uso |
| --- | --- | --- |
| GET / POST | `/companies` | Listar / criar empresas |
| GET | `/{company_id}/dashboard` | Indicadores reais; parâmetros `period` e `anchor` |
| GET / POST | `/{company_id}/records/{table}` | Consultar / cadastrar registros permitidos |
| PATCH | `/{company_id}/records/{table}/{id}` | Editar produtos, condições ou agendamentos |
| POST | `/{company_id}/imports/preview` | Validar CSV e detectar duplicidades |
| POST | `/{company_id}/imports/confirm` | Gravar o lote em uma transação |
| GET | `/{company_id}/reconciliation` | Comparar recebimentos e valores esperados |
| GET / POST | `/{company_id}/reports` | Listar histórico / salvar snapshot |
| GET | `/{company_id}/reports/{id}/pdf` | Baixar PDF do snapshot armazenado |

Resultado operacional = resultado das vendas − despesas − devoluções + CMV recuperado. A conciliação compara recebimentos registrados com receita − cartão − devoluções. Isso não constitui integração automática com bancos ou apuração fiscal.

## 13. Publicação na Vercel

| Configuração | Valor |
| --- | --- |
| Repositório | `Matheus-27mm/data_expert` |
| Branch de produção utilizada | `main` |
| Pasta raiz | Raiz do repositório |
| Framework | Vite |
| Build | `npm run build` |
| Saída estática | `dist` |
| Entrada Python | `api/index.py` |
| Reescrita | `/api/:path*` → `/api/index` |
| Duração máxima configurada | 60 segundos |
| Requisitos Python | `requirements.txt` da raiz |

`api/index.py` importa `backend.main.app`. A Vercel serve os arquivos estáticos e encaminha a API para a função Python. Mantenha `STATIC_DIR` sem definição nesse ambiente. A pasta `.vercel` contém a associação local da CLI e não deve ser versionada.

### CLI

```bash
npx vercel login
npx vercel
npx vercel --prod
```

O segundo comando publica um preview; o terceiro publica em produção. Confira a conta e o projeto selecionados. A conexão Git foi configurada para este repositório e permite publicar alterações enviadas à branch de produção.

### Verificação após publicar

- Página inicial: dashboard carregado.
- `/api/health`: `status: ok`.
- `/api/dashboard?period=monthly&anchor=2026-08-31`: `net: 1820000`.
- `/api/docs`: documentação acessível.
- `/api/reports/pdf?period=monthly&anchor=2026-08-31`: PDF válido.
- Simulador: testar uma venda, pois utiliza `POST`.

### Trocar o repositório

Após criar o destino e definir como preservar seu histórico:

```bash
git remote -v
git remote set-url origin https://github.com/SEU_USUARIO/NOVO_REPOSITORIO.git
git push -u origin main
```

Atualize **Settings → Git** na Vercel, as permissões do novo repositório, os links e o badge deste README. Não use push forçado para contornar divergências sem analisar o histórico.

O código não depende de uma organização específica. A elegibilidade do repositório e os limites devem ser conferidos nas condições vigentes do plano utilizado.

Referência: [runtime Python da Vercel](https://vercel.com/docs/functions/runtimes/python).

## 14. Testes e integração contínua

### Comandos locais

```bash
npm run build
```

**Windows:**

```powershell
.\.venv\Scripts\python.exe -m pytest backend -q
```

**Linux/macOS:**

```bash
.venv/bin/python -m pytest backend -q
```

### Cobertura atual

Os testes financeiros verificam:

1. Reconciliação mensal e consistência entre produtos, dias e total.
2. Períodos vazios, filtros, semanas entre meses e fevereiro bissexto.
3. Igualdade entre soma diária e resultado mensal.
4. Simulação negativa e rejeição de entradas inválidas.
5. Ausência de equilíbrio quando as taxas consomem a receita.
6. PDFs dos três períodos e validação de parâmetros do dashboard.

Os testes de PDF conferem assinatura do arquivo e cabeçalhos HTTP; não substituem inspeção visual. Os testes adicionais cobrem JWTs inválidos, configuração sem exposição de senha, importação CSV, relatórios e destinatários de agendamentos.

Para os testes de integração, defina `NEON_TEST_DATABASE_URL` apontando para um PostgreSQL **descartável**. Eles aplicam migrações e verificam RLS entre usuários, devoluções, rollback integral de importações duplicadas, filtros de datas, snapshots e edição de produtos. Sem essa variável, esses dois testes são pulados. O CI fornece PostgreSQL 18 para executá-los. A autenticação remota deve ser conferida com uma conta da equipe e os domínios autorizados no Neon.

### Testes de navegador

```powershell
# Somente banco descartável: os testes criam registros.
$env:NEON_TEST_DATABASE_URL="postgresql://usuario:senha@localhost:5432/banco_testes"
npx playwright install chromium
npm run test:e2e
```

A suíte abre uma API isolada na porta 8011 e o frontend na 5174. A identidade Neon é simulada no teste, mas as rotas de negócio e o PostgreSQL são reais. Verifica responsividade em 360, 768 e 1440 pixels, mudança de período, PDF, criação de empresa/produto, estoque, contas, CSV, persistência do histórico e acessibilidade WCAG A/AA na tela de relatórios. Isso não equivale a uma certificação de acessibilidade nem testa a entrega de e-mails do Neon.

### GitHub Actions

O workflow `.github/workflows/ci.yml` roda em `push` e `pull_request`:

| Job | Verificações |
| --- | --- |
| `frontend` | Node 22, `npm ci` e build |
| `backend` | Python 3.12, requisitos e pytest |
| `docker` | Build da imagem, execução, saúde e página inicial |

O teste Docker repete a consulta durante a inicialização e imprime logs em caso de falha. O workflow tem permissão de leitura do repositório e não publica imagens em registries.

**CI e deploy são separados:** GitHub Actions valida; a integração Git da Vercel publica. O workflow atual não obriga a Vercel a aguardar todos os testes antes de publicar.

## 15. Fluxo de colaboração

A partir de uma árvore de trabalho limpa:

```bash
git switch main
git pull --ff-only
git switch -c feat/nome-da-melhoria
```

Depois de implementar e validar:

```bash
git status
git add CAMINHOS_DOS_ARQUIVOS_ALTERADOS
git diff --cached
git commit -m "feat: descreva a melhoria"
git push -u origin feat/nome-da-melhoria
```

Substitua os caminhos e o nome da branch. Abra um pull request e acompanhe os checks e o deploy de preview correspondente.

Ao contribuir:

- Mantenha cálculos no backend e reutilize-os no dashboard e no PDF.
- Preserve o contrato monetário: centavos nas respostas, reais na entrada do simulador.
- Atualize testes ao alterar cálculos, períodos e validações.
- Confira celular e desktop ao modificar layout.
- Documente alterações de API, configuração e execução.
- Não inclua credenciais, dados reais de clientes, ambientes virtuais ou builds no commit.

O repositório não possui arquivo de licença. A licença de distribuição ainda precisa ser definida pelos responsáveis pelo projeto.

## 16. Solução de problemas

| Sintoma | Causa provável | Verificação ou solução |
| --- | --- | --- |
| Interface não carrega dados | API desligada | Inicie Uvicorn na porta 8000 e consulte `/api/health` |
| Vite usa outra porta | Porta 5173 ocupada | Confira a URL impressa; revise as origens se alterar a configuração |
| Indicadores zerados | Data fora da base fictícia | Selecione agosto de 2026, período mensal |
| Simulação retorna `422` | Entrada fora dos limites | Confira o corpo de erro e a tabela da API |
| Venda dá prejuízo | Custos superam o preço | Revise as premissas; resultado negativo não é erro técnico |
| Docker não conecta ao engine | Docker parado | Inicie Docker Desktop/Engine e execute `docker info` |
| Porta 8080 ocupada | Outro serviço na porta | Troque o mapeamento por `127.0.0.1:8081:8000` em `compose.yaml` e recrie |
| Alteração não aparece no Docker | Imagem anterior | Execute `docker compose up -d --build` |
| `ModuleNotFoundError` | Dependências em outro Python | Instale e execute pelo mesmo executável de `.venv` |
| Falha com `STATIC_DIR` | Diretório inexistente | Gere o build e use caminho válido; não defina a variável com Vite |
| Site abre, mas API publicada falha | Função ou rewrite | Confira `vercel.json` e logs da Vercel |
| `/docs` retorna `404` | Documentação sob prefixo API | Use `/api/docs` |
| PDF não baixa | Erro ou indisponibilidade da API | Teste a rota diretamente e consulte logs |
| Área da empresa pede configuração | Variáveis ausentes | Preencha `.env`, aplique migrações e reinicie a API |

Ao relatar problemas, informe ambiente, período/data, comando e mensagem de erro. Não compartilhe tokens ou dados sensíveis em logs e issues.

## 17. Operação e configuração dos serviços

### Relatórios agendados

O workflow `operations.yml` executa diariamente às 10:00 UTC (06:00 em Manaus). Relatórios semanais são gerados na segunda-feira e mensais no primeiro dia do mês, sempre para o período encerrado. A entrega exige os secrets `DATABASE_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_FROM` no GitHub. Sem configuração, o workflow informa que o envio está inativo.

O destinatário é o e-mail confirmado da conta, não um endereço arbitrário. O worker registra cada execução com chave única por agendamento e período. Em falha de SMTP, confira o provedor antes de tentar novamente para evitar envio duplicado. O worker utiliza a conexão administrativa no servidor; essa credencial nunca deve ser fornecida ao frontend.

### Backup

`scripts/backup.py` usa `pg_dump` e criptografa o resultado com Fernet. Configure `DATABASE_URL` e `BACKUP_KEY` nos secrets do GitHub. Guarde a chave separadamente: ela é necessária para recuperar o backup. O workflow mantém os arquivos criptografados como artifacts por 14 dias. O workflow usa ferramentas PostgreSQL 18 via Docker para compatibilidade com o banco. O backup cobre os schemas `public` e `lucra_private`; contas e sessões do Neon Auth não estão incluídas.

Para backup manual, configure `BACKUP_KEY` no ambiente e execute `python -m scripts.backup`. Se não tiver as ferramentas PostgreSQL instaladas, defina `PG_USE_DOCKER=1` com Docker ativo.

Para restaurar, aponte `RESTORE_DATABASE_URL` para um banco vazio e execute `python -m scripts.restore caminho/arquivo.dump.enc`, usando a mesma `BACKUP_KEY`. O comando recusa bancos com tabelas existentes, restaura em uma transação e repõe as permissões da aplicação. O fluxo foi testado com comparação das contagens de seis tabelas em um banco separado. Guarde a chave de recuperação fora do repositório e separada dos backups.

### Imagem Docker

O workflow manual `container.yml` publica no GitHub Container Registry usando `GITHUB_TOKEN`, com permissão `packages: write`. Publicar uma imagem não inicia uma hospedagem remota: é necessário configurar um servidor de destino e suas variáveis de ambiente.

### Validação antes do uso real

Execute os testes, aplique as migrações e valide login, isolamento entre duas contas, importação e geração de PDF no projeto Neon configurado. Os testes locais não substituem essa validação remota. Confira as taxas efetivamente cobradas e os impostos com os responsáveis da empresa; o simulador é uma projeção baseada nos parâmetros informados.

O escopo atual é controle básico da empresa. Por decisão da equipe, envio por SMTP, hospedagem Docker remota, integrações com bancos/adquirentes e apuração tributária por regime ficam para uma etapa posterior. Impostos e taxas são valores informados nos lançamentos. O cadastro de condições não consulta contratos de adquirentes.

### Monitoramento básico

`/api/health` verifica a API; `/api/ready` verifica a conexão e as três migrações esperadas. Respostas incluem `X-Request-ID`. Os logs da aplicação registram método, rota, status e duração, sem corpo, token ou query string. O workflow operacional consulta a prontidão diariamente. Logs e checks não substituem um serviço externo de alertas em tempo real.
