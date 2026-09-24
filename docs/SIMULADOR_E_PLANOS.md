# Simulador e planos de ação

Atualização de 24/09/2026.

## Simulador

O catálogo considera os produtos **ativos da empresa selecionada**. Custo e preço vêm do cadastro; alterar o preço na simulação não muda o produto. Escolha quantidades e condições de pagamento para calcular o resultado antes das despesas operacionais.

O carregamento consulta somente produtos e condições, sem esperar o histórico de recebimentos. A tela distingue carregamento, falha com nova tentativa, catálogo vazio e produtos inativos. As chamadas de autenticação e API têm tempo máximo de espera. Datas de venda e vencimento ficam apenas no cadastro de venda.

A simulação não salva venda nem movimenta estoque.

Parcelas é uma seleção de 1x a 12x; pagamentos à vista usam 1x. Uma condição cadastrada aplica seu próprio parcelamento.

## Planos de ação

- Indicadores: a fazer, em andamento, prazo vencido e concluídos.
- Quadro dividido em três etapas, com busca e filtro de prioridade.
- Planos vencidos e de maior prioridade aparecem primeiro em cada etapa.
- **Novo plano** abre o cadastro de título, objetivo, prioridade e prazo opcional.
- Clique no cartão para alterar o andamento, editar os detalhes ou registrar uma atualização no histórico.
- Os cartões também oferecem **Iniciar plano**, **Marcar como concluído** e **Reabrir plano**, conforme a etapa atual. O prazo indica atraso, mas não altera a etapa automaticamente.
- Registros existentes são preservados. O histórico contém as atualizações escritas; mudanças de etapa não geram uma anotação automática.

No celular, as etapas ficam empilhadas. Os dados continuam restritos à empresa, usando as mesmas rotas autenticadas e políticas de isolamento.
