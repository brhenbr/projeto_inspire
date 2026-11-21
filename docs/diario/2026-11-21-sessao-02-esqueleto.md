# Diário — 2026-11-21 — Sessão 02: esqueleto do projeto

## Objetivo da sessão
Sair do desenho e ter o sistema inteiro subindo em Docker, com testes e portão de qualidade.

## O que foi feito
- Cliente aprovou o desenho (diagramas "muito bons"), a remoção de contatos pessoais na ingestão e deu
  início à implementação.
- Backend (Python 3.12, FastAPI, SQLAlchemy, Alembic, structlog), frontend (React, TypeScript, Vite) e
  `docker-compose.yml` com `db`, `migrate`, `api`, `worker` e `web`.
- Migração `0001` cria os quatro schemas das camadas e as extensões de busca.
- Portão de qualidade local: `scripts/qualidade.sh`.
- Documentação: `docs/04-implementacao/01-esqueleto.md`, `docs/05-testes/estrategia.md`,
  `docs/06-deploy/execucao-local.md`.

## Decisões tomadas
- Versões fixas por lock (`uv.lock`, `package-lock.json`), contêineres sem root e sem capacidades, chave do
  portal só no worker, só o `web` publicado em localhost. Detalhes em `docs/04-implementacao/01-esqueleto.md`.
- Código em inglês; nomes de schemas e tabelas em português.

## Descobertas e problemas
- Primeira execução do portão falhou só por formato de dois arquivos de teste e por uma dependência não
  declarada do eslint (`@eslint/js`); ambos corrigidos.
- O FastAPI avisou que o parâmetro `root_path` está obsoleto; a configuração foi movida para o servidor
  (`--root-path /api`).
- A instalação das dependências do frontend na primeira vez levou ~5 minutos (rede); depois, cache.
- Um comando meu com heredocs aninhados falhou por erro de aspas, sem efeito colateral; passei a escrever
  arquivos com a ferramenta própria.

## Verificação
Backend: ruff, mypy, 9 testes, cobertura 84%. Frontend: eslint, tsc, 3 testes. Sistema completo no Docker
conferido de fora (página, API pelo nginx, OpenAPI, portas, logs sem a chave) e a página foi vista renderizada.

## Pendências / próximos passos
- EP-01: extração (US-002 cliente HTTP resiliente, US-001 dimensões, US-003 listagem, US-004 detalhe,
  US-009 remoção de dados pessoais, US-005 snapshot e hash, US-008 normalizador, US-006 botão na web).
- Medir o tempo real da primeira carga (~20,7 mil chamadas).
