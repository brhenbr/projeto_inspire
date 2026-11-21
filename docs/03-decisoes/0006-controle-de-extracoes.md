# ADR-0006: Controle de pedidos de extração (custo e carga no portal)

- **Status:** aceita, com valores padrão configuráveis (ajustáveis pelo cliente)
- **Data:** 2026-11-21
- **Decisores:** cliente (dono do produto) e Claude

## Contexto
O cliente levantou um risco: um botão "Extrair" clicado a cada minuto gastaria processamento à toa e
sobrecarregaria o portal. O controle precisa existir, e não só na tela, porque a API também pode ser
chamada por outros clientes e porque duas abas abertas contornariam um controle só visual.

**Medições em 2026-11-21** (amostra pequena, a confirmar na primeira carga completa):
- Detalhe de um conjunto: ~0,17 s. Página de listagem: ~0,24 s.
- Carga completa: ~1 h em série (20,7 mil detalhes), ~15 a 20 min com 4 chamadas em paralelo.
  Só a listagem (~1.400 páginas): ~6 min.
- A data de última alteração da listagem coincidiu com a do detalhe em 24 de 24 conjuntos.
  Isso permite buscar o detalhe só do que mudou.

## Decisão
1. **A autoridade fica no backend.** A tela apenas reflete o que a API informa (botão desabilitado,
   motivo e horário de liberação). Assim, nenhum outro cliente nem aba duplicada contorna a regra.
2. **Uma execução ativa por vez.** Garantido no banco por um índice único parcial sobre as execuções em
   estado ativo (enfileirada, em andamento ou pausada), não apenas em código. Um novo pedido enquanto há
   uma ativa **não cria nada**: devolve a execução em curso (resposta idempotente). Clicar várias vezes
   custa uma consulta ao banco.
3. **Incremental por padrão.** Percorre a listagem e busca o detalhe só dos conjuntos novos ou com data
   de alteração diferente da guardada. A **completa** é uma opção explícita e mais restrita.
4. **Intervalo mínimo desde o início da última execução bem-sucedida:**
   - incremental: 60 minutos;
   - completa: 24 horas.
   Dentro do intervalo, a API responde `429` com o motivo e `disponivel_em`. Valores configuráveis
   (`EXTRACTION_MIN_INTERVAL_INCREMENTAL_MIN`, `EXTRACTION_MIN_INTERVAL_FULL_MIN`).
5. **Falha ou cancelamento não inicia o intervalo**, mas há espera mínima de 5 minutos para não repetir
   uma falha em laço.
6. **"Forçar"** existe para o curador, com confirmação na tela, e ignora **apenas o intervalo**, nunca a
   regra de uma execução por vez. Toda execução forçada é registrada com quem pediu e quando.
7. **Rede de segurança contra mudanças que não alteram a data:** a tela mostra há quantos dias foi a
   última extração completa e sugere refazê-la (recomendação inicial: semanal). Uma agenda automática
   fica para a fase 2 e substituirá boa parte do uso manual.
8. **Proteção do portal:** concorrência máxima de 4 chamadas simultâneas (configurável), com retry e
   espera crescente, como já previsto.

## Opções consideradas
- **Só controle na tela:** simples, mas qualquer outro cliente ou aba duplicada o ignora. Rejeitada.
- **Só intervalo mínimo, sem incremental:** limita a frequência, mas cada execução ainda custa ~1 h.
  Rejeitada; o incremental é o que reduz o custo real.
- **Sem botão, só agenda:** o menor custo, mas tira do curador a possibilidade de atualizar na hora.
  Mantida como fase 2, ao lado do botão.

## Consequências
- A tabela `raw.execucao` ganha o tipo (incremental ou completa), se foi forçada e quem pediu.
- A API `POST /v1/extracoes` tem três respostas: `202` (nova), `200` (já havia uma em curso, devolve a
  existente) e `429` (dentro do intervalo, com `disponivel_em`).
- Os valores de 60 min, 24 h e 4 em paralelo são ponto de partida: serão ajustados com a medição real.
- O incremental depende da data da listagem refletir mudanças. A completa periódica e o hash do
  conteúdo cobrem os casos em que não reflita.
