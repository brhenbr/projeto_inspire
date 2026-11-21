# ADR-0003: Stack tecnológica do MVP

- **Status:** aceita (backend, frontend e restante da proposta); o provedor de LLM fica para o ADR-0004
- **Data:** 2026-11-21
- **Decisores:** cliente (dono do produto) e Claude

## Contexto
Proposta completa em [proposta-tecnologias.md](../02-arquitetura/proposta-tecnologias.md). O cliente
escolheu o backend e o frontend entre as alternativas apresentadas e não objetou ao restante.

## Decisão
- **Backend e worker:** Python 3.12 + FastAPI, SQLAlchemy 2 e Alembic. API REST `/v1` em OpenAPI.
- **Frontend:** React + TypeScript + Vite, consumindo apenas a API própria.
- **Banco:** PostgreSQL 16, com busca textual em português (`unaccent`, `pg_trgm`) e, depois, `pgvector`.
- **Jobs:** fila em PostgreSQL com processo worker separado da API. Sem Redis nem outro broker.
- **Arquitetura:** monolito modular com portas e adaptadores; Docker Compose com `web`, `api`,
  `worker` e `db`.
- **Contrato de LLM:** interface compatível com a API da OpenAI, escolhida por ser aberta e aceita por
  praticamente qualquer servidor ou serviço, o que mantém o provedor trocável.
- **Testes:** pytest, Playwright (E2E) e Vitest. **Qualidade de código:** ruff, mypy, ESLint, pre-commit.
- **CI:** **adiado.** O cliente ainda não tem experiência com CI e não é necessário agora. Começamos com
  um portão local (comando único que roda lint e testes, mais pre-commit). O workflow de CI será
  adicionado quando o repositório for ao GitHub, e o cliente será guiado nesse passo.

## Consequências
- O desenvolvimento local exige o Docker Desktop aberto.
- O C2 do rascunho muda conforme o ADR-0004: o runtime de LLM sai do desenho se o provedor for externo.
- Os itens de CI do backlog (US-062) e a varredura de dependências do ADR-0002 passam a depender do
  primeiro push; até lá, a verificação é local.
