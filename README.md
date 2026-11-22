# Inspire Catálogo — extração, discovery e curadoria do catálogo do dados.gov.br

Aplicação web para o time do projeto Inspire (frente UFSCar) **espelhar o catálogo de metadados do Portal
Brasileiro de Dados Abertos, explorá-lo, medir a qualidade dos metadados e curá-los**, com apoio de LLM
(sempre com aprovação humana). Só metadados são tratados: os arquivos continuam nos órgãos.

**Status:** MVP (fase 1) completo e testado: extração, discovery, qualidade, curadoria, coleções, LLM (roteador de
provedores gratuitos), exportação CSV/JSON/DCAT-BR, chat em linguagem natural, interface web, testes E2E, manual de
testes e pacote de teste com a base carregada. O que ficou para a fase 2 está em
[limites conhecidos](docs/01-produto/limites-conhecidos.md) e no [backlog](docs/01-produto/backlog/backlog.md).

**Quer entender rápido?** Leia [Como o sistema funciona](docs/02-arquitetura/00-como-o-sistema-funciona.md) (uma página, sem
jargão). Para engenharia, siga com os [C4](docs/02-arquitetura/c1-contexto.md).

## Experimente
```
docker compose up --build      # depois abra http://127.0.0.1:8080
```
1. Em **Extração**, clique em "Atualizar catálogo" (precisa da chave de API no `.env`, ver abaixo).
2. Explore em **Buscar**, veja a qualidade de um conjunto, edite metadados, crie coleções e exporte.
3. Em **Perguntar**, escreva o que procura em português; em **Coleções**, descreva uma coleção em texto.
4. Em **Sugestões de LLM**, rode o modo simulado (não usa IA nem rede) para ver o fluxo de revisão.

O Docker Desktop precisa estar aberto. API documentada em http://127.0.0.1:8080/api/docs.

## Testar com a base já carregada (sem esperar a extração)
Quem vai **testar** o sistema recebe um pacote com a base extraída (~52 MB) e não precisa da chave do portal:
```
bash scripts/pacote-de-teste.sh carregar pacote/inspire-base-AAAAMMDD.dump
bash scripts/testes-de-aceitacao.sh       # abre a página de testes em http://127.0.0.1:8090
```
Detalhes em [pacote de teste](docs/06-deploy/pacote-de-teste.md) e no [manual de testes](docs/07-manual/LEIA-ME.md)
(43 casos de uso com dados reais; a página de testes guarda os resultados em SQLite).

## Configuração
Copie `.env.example` para `.env` e preencha `DADOS_GOV_API_KEY` (dados.gov.br, "Minha Conta"). O `.env` nunca é versionado.
Sem LLM configurado, o sistema usa o **modo simulado** (regras simples, sem IA e sem rede).
Para um LLM real, use `LLM_PROVIDER=roteador` e as chaves `GROQ_API_KEY`, `GEMINI_API_KEY` etc. no `.env`
([ADR-0014](docs/03-decisoes/0014-roteador-de-provedores-llm.md)); basta uma chave para começar, e o sistema troca de
provedor sozinho quando a cota de um acaba. Só campos públicos são enviados ([ADR-0004](docs/03-decisoes/0004-provedor-de-llm-externo-controlado.md)).

## Qualidade e testes
```
bash scripts/qualidade.sh              # lint, tipos, testes unitários e de integração (PostgreSQL real), frontend
bash scripts/e2e.sh                    # testes ponta a ponta (navegador + portal falso)
bash scripts/formatar.sh               # formata o backend
bash scripts/auditar-dependencias.sh   # vulnerabilidades conhecidas nas dependências fixadas
bash scripts/validar-casos.sh          # valida os casos do manual de testes
```

## Onde está cada coisa
- [docs/](docs/README.md) — descoberta, produto, arquitetura (C4), decisões (ADRs), implementação, testes, deploy, manual e diário.
- [app/backend](app/backend) (Python, FastAPI) · [app/frontend](app/frontend) (React, TypeScript) · [app/e2e](app/e2e) (Playwright).
- [kit/](kit/) e `.claude/` — kit de processo reaproveitável em outros projetos (inclui a [ferramenta de roteiro de testes](kit/roteiro-de-testes/README.md)).
- [CLAUDE.md](CLAUDE.md) — premissas do projeto e fatos verificados sobre o portal.

## Segurança em uma frase
Nada sai da infraestrutura do projeto sem decisão registrada; contatos pessoais dos responsáveis são removidos antes de gravar;
a chave do portal só existe no worker; contêineres sem privilégios; versões de dependências fixadas e auditadas
([checklist](docs/05-testes/seguranca-e-soberania.md)).
