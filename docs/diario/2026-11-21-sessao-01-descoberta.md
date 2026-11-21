# Diário — 2026-11-21 — Sessão 01: descoberta

## Objetivo da sessão
Entender o pedido, fechar as primeiras premissas com o cliente e validar a API real do portal.

## O que foi feito
- Rodada de perguntas ao cliente e registro das respostas (resumidas no `CLAUDE.md`, seção "Escopo vigente").
- Validação da API do dados.gov.br e arquivamento do OpenAPI em `docs/00-descoberta/`.
- Leitura da especificação técnica do cliente (`docs/00-descoberta/especificacao-tecnica-cliente.md`).
- Criação do repositório local, estrutura de pastas, `CLAUDE.md`, kit de processo e `.env.example`.

## Decisões tomadas
- [ADR-0001](../03-decisoes/0001-premissas-de-processo-e-escopo-inicial.md).

## Descobertas e problemas
- **A API exige chave em todas as rotas de dados** (401 sem `chave-api-dados-abertos`), contrariando a
  especificação do cliente, que as descreve como abertas. Testado com vários User-Agents.
- Erro meu: na primeira resposta afirmei que a pasta estava vazia sem listá-la. Já havia a especificação
  do cliente na raiz. Passei a ler tudo que existe antes de afirmar algo sobre o workspace.
- A especificação do cliente traz boas diretrizes que vamos adotar como ponto de partida: snapshot bruto
  + hash para detectar mudanças, retry com backoff, concorrência limitada, índice de qualidade e
  verificação de links em worker separado. Ficam como proposta até o desenho de arquitetura.

## Continuação: dossiê, chave e visão
- Lido o dossiê do Inspire (`docs/00-descoberta/Projeto_INSPIRE_Dossie_Detalhado.pdf`). Pontos que
  afetam o produto: GuIA e supervisão humana (human-in-the-loop), Autoavaliação de Impacto Ético,
  Camadas 3 e 4 (LLMs soberanos em português, aplicações inteligentes) e a automação do CND.
- Chave de API colocada pelo cliente em `.env` e validada (HTTP 200, valor não exibido).
- **Descoberta:** a API é intermitente (respostas vazias aleatórias). Catálogo medido em ~20,7 mil
  conjuntos / 311 organizações. Detalhes em `docs/01-produto/visao-e-escopo.md`, seção 8.
- Redigida a versão 0.1 do documento de visão e escopo, com 6 perguntas abertas.

## Continuação: plano de trabalho UFSCar/CPQD e backlog
- Lido o Plano de Trabalho nº 1 (UFSCar/CPQD). Partes acadêmicas ignoradas, a pedido. O produto
  atende A1, A4, A6 e A7; A5 (DCAT-BR/DQV) vira fase 2; A9 vira futuro; A10 fica fora.
- O plano tem dados contratuais e financeiros: o PDF foi movido para `docs/00-descoberta/restrito/`,
  ignorado pelo git. O repositório pode ficar público.
- Respostas do cliente: produto complementar ao CND; verificação de links na fase 2; AIE no backlog;
  avaliadores atuais são professores da UFSCar.
- Criado o backlog (62 itens, 15 épicos) em `docs/01-produto/backlog/`, com gerador genérico em
  `kit/scripts/backlog_to_jira.py` e CSV para Jira (importação não testada em Jira real).
- Visão e escopo atualizados para a versão 0.2.

## Continuação: segurança, soberania e início da arquitetura
- Cliente: padrões de metadados já definidos (nomes ainda não informados); cronograma "o mais rápido
  possível" com o cliente como gestor; repo será público; coleções viram feature do app; segurança e
  soberania são prioridade. Registrado em [ADR-0002](../03-decisoes/0002-seguranca-e-soberania.md).
- Backlog ajustado: coleções como feature (US-033, US-036, US-037), checklist de segurança (US-066) e
  spike de onde rodar o LLM (US-067). Agora 66 itens.
- Medido o ambiente de desenvolvimento: sem GPU útil, 16 GB de RAM, Docker Desktop fechado. Isso limita
  o LLM local e foi incorporado à proposta.
- Criados o C1 (`docs/02-arquitetura/c1-contexto.md`) e a proposta de tecnologias com rascunho de C2.
  (Renderização conferida mais adiante nesta sessão.)

## Continuação: padrões, armazenamento e diagramas
- Cliente: padrões DCAT-BR, DQV e FAIR (apoio: DMBOK); sem GPU, LLM por API com extensão para GPU local; CI adiado; Docker ligado (verificado).
- Cliente propôs armazenamento em duas frentes (documento e tabular). Concluí que o desenho em camadas
  faz sentido, mas em um único PostgreSQL (`jsonb` + tabelas), pelos motivos do
  [ADR-0005](../03-decisoes/0005-armazenamento-em-camadas.md). Fica em proposta até o cliente confirmar.
- C2 movido para arquivo próprio e atualizado. Criado o visualizador offline `docs/diagramas.html`.
  **Os diagramas C1 e C2 foram renderizados em navegador headless e conferidos**, o que não havia sido feito antes.
- Backlog: matriz de qualidade (US-023), normalizador raw→catálogo (US-008), perfil `llm-local` (US-069). Agora 70 itens.
- Pesquisa: o DCAT-BR v1.0 é publicado pelo Catálogo Nacional de Dados (gov.br); a especificação precisa ser obtida e lida (US-023).

## Pendências / próximos passos
- Cliente confirma o ADR-0005 (armazenamento em camadas em um único PostgreSQL).
- C3 (componentes), fluxos (extração e curadoria com LLM) e modelo de dados.
- Esqueleto do projeto em Docker, depois extração, discovery e qualidade.
- Spike de provedores gratuitos de LLM (US-067) e matriz de qualidade DQV/FAIR/DMBOK (US-023).
