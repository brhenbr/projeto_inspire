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

## Pendências / próximos passos
- Cliente cria a chave de API e a coloca no `.env` local.
- Redigir visão e escopo do MVP (`docs/01-produto/`) para aprovação.
- Rodada de arquitetura com C4 e tarefa de conversa sobre tecnologias.
