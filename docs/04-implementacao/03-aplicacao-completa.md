# Implementação 03 — Aplicação completa do MVP

**Em palavras simples:** o sistema agora faz tudo o que o escopo do MVP prometia: traz o catálogo do portal
(com cuidado para não sobrecarregá-lo), deixa explorá-lo, dá uma nota de qualidade explicável a cada
conjunto, permite curar à mão ou com sugestões de um LLM (sempre com aprovação humana), organiza em
coleções e exporta. Este documento é o mapa do que existe e das decisões tomadas no caminho.

- **Período:** 2026-11-21, em modo autônomo (decisões críticas registradas em ADR, com três opções cada)
- **Backlog entregue:** EP-01 a EP-07 (ver o quadro abaixo)

## Mapa por épico
| Épico | O que foi entregue | Onde está |
|---|---|---|
| EP-01 Extração | Cliente do portal resiliente com limite de taxa e pausa coletiva; dimensões, organizações, listagem, detalhe; extração incremental pela data; remoção de dados pessoais; snapshot com hash; normalizador; relatório de conferência; controle de pedidos; CLI e botão | `extraction/`, `worker/`, `api/routes/extracoes.py`, ADR-0006/0007 |
| EP-02 Discovery | Busca em português sem acento, facetas, filtros combináveis (por URL), ordenação, detalhe, organizações, painel, exportação | `discovery/`, `analytics/read_model.py`, ADR-0008 |
| EP-03 Qualidade | 17 regras por dimensão (DQV/FAIR/DMBOK), nota explicável, histórico, agregados por organização, fila priorizada, pesos configuráveis, matriz gerada do código | `quality/`, ADR-0009, [matriz](../02-arquitetura/matriz-de-qualidade.md) |
| EP-04 Curadoria | Edição de campos sobre o espelho (nunca sobrescreve), reversão, status, ação em lote, coleções manuais e dinâmicas com exceções e diferença entre extrações, histórico | `curation/`, ADR-0010 |
| EP-05 LLM | Provedor compatível com OpenAI e provedor simulado, contexto só com campos públicos, três tarefas, execução em lote com revisão, proveniência, propostas desatualizadas | `llm/`, ADR-0011 |
| EP-06 API e exportação | API REST `/v1` em OpenAPI; CSV (com proteção de fórmulas) e JSON com original, curado e status | `api/`, `export/` |
| EP-07 Fundação | Docker Compose, portão de qualidade, E2E, documentação | `docker-compose*.yml`, `scripts/`, `app/e2e/` |
| Interface | 9 telas em React com busca na URL, aviso de provedor externo/simulado, acessibilidade básica | `app/frontend/`, ADR-0012 |

Fora do MVP (fase 2 e futuro, ver backlog): verificação de links, busca semântica e chat, DCAT-BR/DQV exportados, taxonomia
evolutiva, devolução ao portal, multiusuário, agendamento automático, detecção de duplicados.

## Decisões críticas desta fase (ADRs)
| ADR | Decisão | Alternativas |
|---|---|---|
| [0007](../03-decisoes/0007-fila-de-jobs.md) | As tabelas de execução são a fila do worker | Biblioteca de fila no PostgreSQL; Celery + Redis |
| [0008](../03-decisoes/0008-busca-e-modelo-de-leitura.md) | Tabela de leitura materializada no PostgreSQL | Motor de busca dedicado; consulta direta às tabelas |
| [0009](../03-decisoes/0009-modelo-de-qualidade.md) | Regras binárias ponderadas por dimensão | Nota contínua; modelo estatístico/LLM |
| [0010](../03-decisoes/0010-modelo-de-curadoria.md) | Registro de alterações por campo, só inserção | Sobrescrever o espelho; cópia versionada do documento |
| [0011](../03-decisoes/0011-integracao-com-llm.md) | Protocolo compatível com OpenAI + modo simulado | SDK por fornecedor; biblioteca de abstração |
| [0012](../03-decisoes/0012-bibliotecas-do-frontend.md) | React Router e componentes próprios | Biblioteca de componentes completa; sem roteador |
| [0013](../03-decisoes/0013-estrategia-de-testes-e2e.md) | E2E contra portal falso fiel e executável | Portal real; respostas gravadas |

## Problemas encontrados e como foram resolvidos
1. **O portal bloqueia chamadas rápidas com HTTP 405.** A primeira extração real marcou 16.601 conjuntos como "sem detalhe" porque o
   cliente tratava 405 como erro definitivo do item. Corrigido: limite de taxa (padrão 4 req/s), pausa coletiva e crescente
   ao ver 405/429/503, e 400 confirmado antes de ser aceito como definitivo. Há testes de regressão e a extração real foi refeita.
2. **Testes usavam o banco da aplicação.** Um teste deixou um job na fila e o worker o executou de verdade. Corrigido: os testes de
   integração rodam em `inspire_test` e **recusam** rodar em outro banco.
3. **Parâmetro `formato` colidia** entre a saída da exportação e o filtro de formato do recurso: a exportação perdia 20 de 61
   conjuntos. Corrigido (`saida`) com teste de regressão.
4. **Busca em português:** o stemmer depende de acento para "-ção/-ções". Corrigido com normalização aplicada ao índice e à
   consulta ("-ões" vira "-ão").
5. **Imagem do serviço de migração desatualizada** (já tratado na implementação 02): os três serviços do backend usam uma só imagem.

## Números (2026-11-21)
- Testes: backend 247 (cobertura 92,6%), frontend 32, E2E 52.
- Extração real: 20.218 conjuntos, 256 organizações, 126.741 recursos, nota média 72,9; 560 conjuntos sem detalhe no portal.
- Desempenho: consultas entre 0,07 e 0,66 s sobre o catálogo real.
- Observação: o painel mostra "alterados" alto na última extração real porque ela completou os detalhes de conjuntos que a
  primeira tentativa (bloqueada pelo portal) deixara sem detalhe; não são mudanças do portal.
