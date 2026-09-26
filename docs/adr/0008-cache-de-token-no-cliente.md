# 0008 — JWT reutilizado em memória até perto da expiração

**Contexto.** Cada chamada à API buscava `/token` no Neon Auth antes da requisição: uma ida e volta extra por chamada.

**Decisão.** O cliente guarda o JWT em memória (sem `localStorage`) até 60 s antes do `exp`. O cache é descartado em qualquer 401 e no logout. Buscas simultâneas continuam compartilhando uma única requisição.

**Por que é seguro.** A API valida o JWT de forma stateless (assinatura JWKS e `exp`). Reutilizar o token não amplia a janela de validade que ele já tem.

**Consequências.** Uma ida ao provedor por token, em vez de uma por chamada. Coberto em `tests/browser/loading.spec.ts` (reuso e expiração próxima).
