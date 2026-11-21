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

## Pendências / próximos passos
- Cliente cria a chave de API e a coloca no `.env` local.
- Redigir visão e escopo do MVP (`docs/01-produto/`) para aprovação.
- Rodada de arquitetura com C4 e tarefa de conversa sobre tecnologias.
