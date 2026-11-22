# ADR-0007: Fila de jobs do worker

- **Status:** aceita (decidida de forma autônoma; revisada e confirmada pelo cliente em 2026-11-21)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
A extração (até ~1 h) e os lotes de LLM precisam rodar fora da API, ser retomáveis e nunca duplicar. O
[ADR-0003](0003-stack-tecnologica.md) já previa uma fila no PostgreSQL, sem broker externo; falta decidir
**como**. O produto é monousuário, com um worker, e uma execução ativa por vez
([ADR-0006](0006-controle-de-extracoes.md)).

## Opções consideradas
### 1. Biblioteca de fila sobre PostgreSQL (ex.: Procrastinate)
- **Prós:** pronta, com retry, agendamento e painel; uso de `LISTEN/NOTIFY`.
- **Contras:** mais uma dependência e um schema próprio no banco; o estado do job ficaria separado do
  estado de negócio (`raw.execucao`), exigindo manter os dois coerentes; o modelo de "uma ativa por vez"
  e de retomada por fase precisaria ser reimplementado por cima.

### 2. As próprias tabelas de execução como fila (`SELECT … FOR UPDATE SKIP LOCKED`) — escolhida
- **Prós:** zero dependência nova; o estado do job **é** o estado de negócio (uma única fonte de verdade,
  já protegida pelo índice de "uma ativa por vez"); retomada por fase é natural; fácil de testar e de
  inspecionar com SQL; auditável.
- **Contras:** escrevemos o laço de polling e a lógica de reivindicação; sem painel pronto; polling a
  cada poucos segundos em vez de notificação (irrelevante nesta escala).

### 3. Celery com Redis
- **Prós:** padrão de mercado, muito maduro, escala horizontalmente.
- **Contras:** dois serviços novos (broker e backend de resultados), mais superfície de ataque e de
  operação, contra o princípio de custo e soberania mínimos; é desproporcional para um worker e poucos
  jobs por dia.

## Decisão
**Opção 2.** O worker consulta `raw.execucao` (e, para lotes de LLM, `curadoria.llm_execucao`) e
reivindica o próximo job com `FOR UPDATE SKIP LOCKED`. Ao iniciar, devolve à fila as execuções que
ficaram "em andamento" por queda do processo, retomando da fase em que estavam.

## Consequências
- Se um dia houver vários workers ou muitas execuções, a interface do worker permite trocar por uma
  biblioteca (opção 1) sem mudar a regra de negócio.
- É preciso testar a reivindicação concorrente e a retomada após queda (feito nos testes de integração).
