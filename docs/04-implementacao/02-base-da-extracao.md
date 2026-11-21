# Implementação 02 — Base da extração

**Em palavras simples:** construímos as peças que a extração vai usar: um "telefonista" que fala com o portal
sem se perder quando ele falha, um "filtro" que tira dados pessoais antes de qualquer gravação, e uma
"gaveta" no banco que guarda o que o portal disse e só abre uma nova versão quando algo muda. Ainda não
há botão nem coleta completa; isso vem a seguir, em cima destas peças.

- **Data:** 2026-11-21
- **Backlog:** US-002 e US-009 concluídas; US-005 em andamento; base técnica da US-015

## O que foi construído (`app/backend/src/inspire/extraction/`)
| Peça | Arquivo | O que faz |
|---|---|---|
| Cliente do portal | `portal_client.py` | Envia a chave e um User-Agent identificado; tenta de novo em 429, 5xx, timeout e queda de conexão com espera crescente e aleatoriedade, respeitando `Retry-After`; **trata lista vazia como falha provisória**; limita a 4 chamadas simultâneas; nunca mostra a chave |
| Privacidade | `privacy.py` | Remove nome e e-mail do responsável (em qualquer nível do documento), guarda só se existiam; barreira final que recusa gravar se algum sobrar |
| Hash | `hashing.py` | Impressão digital do conteúdo, independente da ordem dos campos |
| Gaveta bruta | `raw_store.py` | Grava o documento só se o hash mudou; registra o que cada execução viu; cria execuções |
| Banco | migração `0002` | Tabelas `raw.execucao`, `raw.documento`, `raw.visto` e o índice que **impede duas execuções ativas** |

## Decisões
- **Uma execução ativa por vez é garantida pelo banco** (índice único parcial). Oito pedidos simultâneos
  criam uma só execução; um teste automatizado prova isso (ADR-0006).
- **Página vazia nunca encerra a coleta sozinha.** O fim só é aceito depois de 4 repetições vazias.
- **Defesa em profundidade para dados pessoais:** remove-se na ingestão e, além disso, a gravação recusa
  qualquer documento que ainda traga campo pessoal.
- **Os três serviços do backend compartilham uma única imagem** (`inspire-backend:dev`).

## Verificação
- Portão de qualidade: ruff, mypy estrito, 58 testes (unidade e PostgreSQL real), cobertura 92%.
- **Teste real contra o portal** (60 conjuntos de 26 organizações, páginas espalhadas pelo catálogo):
  - as 311 organizações e a soma de 20.700 conjuntos conferem com a medição anterior; o fim da lista foi
    confirmado após 17 esperas de retry;
  - 59 detalhes gravados; na **segunda rodada, 59 vieram "inalterado"**;
  - **0 campos pessoais no banco** (consulta direta); nome do responsável presente em 30 dos 59, nome com
    e-mail em 16; 0 e-mails em textos livres;
  - o teste limpou as tabelas ao terminar.

## Achados
1. **Detalhe que devolve sempre HTTP 400.** Um conjunto do IPEA aparece na listagem mas o detalhe falha de
   forma repetível ("Erro ao executar a consulta"). Taxa observada: 1 em 60. A coleta registrará esses
   itens como `conjunto_sem_detalhe` e os listará no relatório, sem interromper. É também um sinal de
   qualidade do catálogo.
2. **Erro de fato meu, corrigido:** eu havia afirmado que todo conjunto traz nome e e-mail do responsável,
   com base em 3 itens. A amostra maior mostrou que não. A regra de remoção não muda.
3. **Bug de implantação, achado e corrigido:** a imagem do serviço de migração era separada e ficou
   desatualizada, e o banco já estava numa versão mais nova. Os três serviços agora usam a mesma imagem.

## Pendências
- Coleta de dimensões e organizações (US-001), listagem (US-003), detalhe com tolerância ao 400 (US-004),
  normalizador (US-008) e a ligação ao worker e à fila (US-015, US-016, US-006).
- Medir a taxa real de detalhes com 400 e de e-mails em texto livre na primeira carga completa.
