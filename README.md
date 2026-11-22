# Inspire Catálogo — extração, discovery e curadoria do catálogo do dados.gov.br

Aplicação web para o time do projeto Inspire (frente UFSCar) **espelhar o catálogo de metadados do Portal
Brasileiro de Dados Abertos, explorá-lo, medir a qualidade dos metadados e curá-los**, com apoio de LLM
(sempre com aprovação humana). Só metadados são tratados: os arquivos continuam nos órgãos.

**Status:** MVP completo e testado (extração, discovery, qualidade, curadoria, coleções, LLM, exportação CSV/JSON/DCAT-BR, chat em
linguagem natural, interface web e testes E2E). Veja o que falta no [backlog](docs/01-produto/backlog/backlog.md).

## Experimente
```
docker compose up --build      # depois abra http://127.0.0.1:8080
```
1. Em **Extração**, clique em "Atualizar catálogo" (precisa da chave de API no `.env`, ver abaixo).
2. Explore em **Buscar**, veja a qualidade de um conjunto, edite metadados, crie coleções e exporte.
3. Em **Perguntar**, escreva o que procura em português; em **Coleções**, descreva uma coleção em texto.
4. Em **Sugestões de LLM**, rode o modo simulado (não usa IA nem rede) para ver o fluxo de revisão.

O Docker Desktop precisa estar aberto. API documentada em http://127.0.0.1:8080/api/docs.

## Configuração
Copie `.env.example` para `.env` e preencha `DADOS_GOV_API_KEY` (dados.gov.br, "Minha Conta"). O `.env` nunca é versionado.
Para um LLM real, veja [ADR-0011](docs/03-decisoes/0011-integracao-com-llm.md): só campos públicos são enviados, o recurso vem
desligado para provedores externos e exige lista de hosts aprovados.
Para LLMs gratuitos com troca automática por cota, use `LLM_PROVIDER=roteador` e as chaves `GROQ_API_KEY`, `GEMINI_API_KEY` etc.
no `.env` ([ADR-0014](docs/03-decisoes/0014-roteador-de-provedores-llm.md)); basta uma chave para começar.

## Qualidade e testes
```
bash scripts/qualidade.sh      # lint, tipos, testes unitários e de integração (PostgreSQL real), frontend
bash scripts/e2e.sh            # testes ponta a ponta (navegador + portal falso)
bash scripts/formatar.sh       # formata o backend
```

## Onde está cada coisa
- [docs/](docs/README.md) — descoberta, produto, arquitetura (C4), decisões (ADRs), implementação, testes, deploy e diário.
- [app/backend](app/backend) (Python, FastAPI) · [app/frontend](app/frontend) (React, TypeScript) · [app/e2e](app/e2e) (Playwright).
- [kit/](kit/) e `.claude/` — kit de processo reaproveitável em outros projetos.
- [CLAUDE.md](CLAUDE.md) — premissas do projeto e fatos verificados sobre o portal.

## Segurança em uma frase
Nada sai da infraestrutura do projeto sem decisão registrada; contatos pessoais dos responsáveis são removidos antes de gravar;
a chave do portal só existe no worker; contêineres sem privilégios; versões de dependências fixadas.
