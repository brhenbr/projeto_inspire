# ADR-0013: Estratégia dos testes ponta a ponta (E2E)

- **Status:** aceita (decidida de forma autônoma; revisada e confirmada pelo cliente em 2026-11-21)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
É preciso provar que os fluxos principais funcionam de verdade, do navegador ao banco: extrair, buscar,
curar, usar o LLM, exportar, e respeitar o controle de pedidos. O portal real é lento, instável (respostas
vazias), **bloqueia chamadas rápidas** e muda com o tempo; usá-lo nos testes os tornaria lentos e frágeis e
sobrecarregaria um serviço público.

## Opções consideradas
### 1. E2E contra o portal real
- **Prós:** máximo realismo.
- **Contras:** lento (a extração completa leva horas), não determinístico, depende de rede e chave, sujeito a
  bloqueio (HTTP 405), impossível de simular casos como "o portal mudou este conjunto" ou "detalhe com erro".

### 2. E2E com respostas gravadas do portal (fixtures estáticas)
- **Prós:** determinístico e sem rede.
- **Contras:** não permite cenários que mudam durante o teste (mudança no portal, remoção de conjunto); as
  gravações envelhecem e precisam ser regravadas.

### 3. E2E com um portal falso fiel, executável, controlado pelo teste — escolhida
Um servidor HTTP que reproduz o comportamento **medido** do portal (chave obrigatória, páginas de 15, datas em
`dd/mm/aaaa`, respostas vazias intermitentes, detalhe com erro 400) e aceita comandos do teste para mudar o
"portal" no meio do cenário. O mesmo código alimenta os testes de integração.
- **Prós:** determinístico, rápido (segundos), cobre cenários impossíveis no portal real, sem carga em serviço
  público, roda em qualquer máquina com Docker.
- **Contras:** pode divergir do portal real; mitigado por construir o falso a partir de medições e por validar o
  cliente contra o portal real em testes manuais (feitos nesta fase, com a extração real completa).

## Decisão
**Opção 3.** Playwright (Chromium) em um contêiner próprio, contra a pilha completa subida por um arquivo
Compose dedicado (`docker-compose.e2e.yml`), com banco descartável, portal falso, API, worker e web reais. O
LLM roda no modo **simulado**. Os cenários cobrem os fluxos do MVP e as regras de custo e segurança.

## Consequências
- Um comando roda tudo e devolve código de saída para automação: ver `docs/05-testes/e2e.md`.
- O cliente participa da revisão dos cenários e de uma demonstração; o realismo do portal é checado por
  testes manuais com a chave real.
- O portal falso precisa ser mantido junto com o comportamento do portal real (registrado no `CLAUDE.md`).
