# Carregamento para a apresentação

As consultas do painel, estoque, contas a pagar, conciliação e recebíveis usam uma conexão por operação, com uma transação de leitura consistente. O usuário continua restrito pelas políticas RLS e pela identidade definida com SET LOCAL. Não há cache compartilhado de dados entre empresas.

No frontend, chamadas simultâneas compartilham a solicitação em andamento do token. Quando ela termina, a referência é descartada; uma nova rodada consulta a autenticação novamente. Tokens não são persistidos no navegador por essa otimização.

Em uma medição do computador de desenvolvimento ao Neon, o resumo de setembro da Perceptron passou de 8,88 s para 4,69 s. É uma amostra sujeita à rede, não um SLA nem uma medição do navegador em produção.

Depois da apresentação: avaliar pool de conexões, cache por usuário/empresa com invalidação após alterações, paginação, agregações SQL e tarefas em segundo plano. Essas mudanças exigem medições e testes próprios antes da publicação.
