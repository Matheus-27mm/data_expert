# Lucra — clareza para decidir melhor

Primeiro MVP de análise de margem, com React + TypeScript, Python + FastAPI, pandas, relatório PDF via ReportLab, fundação Supabase e CI no GitHub Actions.

## Executar localmente

Requer Node.js 22 e Python 3.12. Na raiz, instale as dependências:

```powershell
npm ci
python -m pip install -r backend/requirements.txt
```

Terminal 1:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
npm run dev
```

Abra http://127.0.0.1:5173. O Vite encaminha `/api` para o FastAPI. Documentação interativa em http://127.0.0.1:8000/api/docs.

## Docker

Com o Docker Desktop iniciado, execute na raiz:

```powershell
docker compose up -d --build
```

Abra http://127.0.0.1:8080. A imagem compila o React em uma etapa Node e executa FastAPI como usuário sem privilégios em Python 3.12, servindo frontend e API na mesma origem. Não precisa de variáveis de ambiente para a demonstração. O container possui healthcheck e reinício automático.

```powershell
docker compose logs -f
docker compose down
```

O serviço fica acessível apenas neste computador. Para hospedar em servidor, configure domínio, HTTPS e publicação de portas no ambiente de destino. Nenhuma imagem é enviada automaticamente ao Docker Hub.

## Vercel e GitHub

Repositório: https://github.com/Matheus-27mm/data_expert

Importe esse repositório na Vercel com a pasta raiz e o preset Vite. `vercel.json` configura o build de `dist` e encaminha `/api/*` para `api/index.py`, que reutiliza o FastAPI. `requirements.txt` contém somente dependências de execução. A demonstração não requer credenciais Supabase.

Também é possível publicar pela CLI autenticada:

```powershell
npx vercel --prod
```

O projeto Vercel pode ser conectado ao GitHub para publicar novos commits automaticamente. Ao trocar o repositório, atualize `git remote set-url origin NOVA_URL` e a conexão em Settings > Git no projeto Vercel. Não é necessário mudar os cálculos ou o frontend.

## O que funciona

- Dashboard, comparação de lucro, evolução acumulada e decomposição das deduções.
- Filtros diário, semanal (segunda a domingo) e mensal, com data de referência.
- Produtos ordenados por unidades vendidas, busca e alertas de margem negativa.
- Simulação com CMV, 1–12 parcelas e taxas editáveis; resultado calculado pelo backend.
- Download de PDF com o mesmo período e os mesmos cálculos da tela.
- Estados de carregamento, erro, período vazio e interface responsiva.

A demonstração contém 960 vendas fictícias, divididas entre julho e agosto de 2026. O mês inicial é agosto. Cada mês reconcilia receita de R$ 150.000, CMV de R$ 105.000, lucro estimado de R$ 45.000, impostos de R$ 9.000, cartão de R$ 12.000, comissões de R$ 5.800 e resultado de R$ 18.200. Três produtos têm margem negativa.

## Premissas financeiras

Valores armazenados em centavos; arredondamento monetário HALF_UP. Lucro estimado = receita − CMV. Resultado das vendas = receita − CMV − impostos − cartão/antecipação − comissões. Os custos das transações são deduções efetivas da base fictícia; as taxas do simulador são premissas independentes editáveis.

Simulador: taxa cartão = MDR + taxa mensal de antecipação × (parcelas + 1) / 2. Trata-se de modelo linear ilustrativo, primeira parcela em 30 dias. Preço de equilíbrio = CMV / (1 − soma das taxas), arredondado para cima ao centavo. Não há equilíbrio quando a soma das taxas é >=100%. Taxas contratuais reais podem seguir outro modelo.

O gráfico de cascata é um exemplo didático fixo: R$ 100 − 60 de CMV − 6 de imposto − 22 de cartão − 4 de comissão = R$ 8. Está rotulado como independente do período.

**Não é saldo bancário nem lucro contábil.** Não inclui aluguel, folha, despesas fixas, devoluções ou conciliação de recebíveis. O Simples Nacional é uma premissa de 6%, não uma apuração fiscal. As datas da semana podem atravessar meses; períodos sem transações aparecem zerados, sem estimativas inventadas.

## Supabase: fundação preparada, conexão não ativada

O app funciona sem conta externa. `supabase/migrations/001_initial.sql` cria empresas e vendas com RLS isolando registros pelo proprietário autenticado. `backend/supabase_repository.py` fornece um adaptador paginado com JWT do usuário e chave pública. Não usa chave `service_role`.

Para a fase de dados reais: criar projeto Supabase, aplicar a migração, habilitar login, implementar envio/renovação do JWT na interface e conectar o adaptador às rotas após autenticação. O esquema permite múltiplas empresas, mas ainda não possui convite de colaboradores. Nenhuma credencial ou banco externo foi criado. Consulte [a documentação de RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).

Não exponha a API demonstrativa como um sistema de dados reais sem concluir autenticação e autorização. Para produção, publique frontend e API com HTTPS e configure proxy `/api` e origens CORS conforme [FastAPI](https://fastapi.tiangolo.com/tutorial/cors/). A fonte web tem fallback local.

## Validação e CI

```powershell
npm run build
python -m pytest backend -q
```

O workflow `.github/workflows/ci.yml` executa build React, testes Python e build/smoke test Docker em push e pull request. O deploy é feito pela integração Git da Vercel, não pelo workflow. Testes cobrem reconciliação, agregação diária, limites de períodos, entradas inválidas, simulação negativa, equilíbrio impossível e PDFs.
