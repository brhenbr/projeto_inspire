# Inspire Catálogo — extração e curadoria do catálogo do dados.gov.br

Protótipo web para extrair, explorar (*data discovery*) e curar, com apoio de LLMs, os metadados do
catálogo do Portal Brasileiro de Dados Abertos, no contexto do projeto Inspire.

**Status:** desenho concluído; esqueleto do sistema funcionando (API, worker, banco e web em Docker). Próximo: extração do catálogo.

## Onde está cada coisa
- [docs/](docs/) — descoberta, produto, arquitetura (C4), decisões (ADRs), implementação, testes, deploy e diário.
- [kit/](kit/) — kit de processo reaproveitável em outros projetos.
- [CLAUDE.md](CLAUDE.md) — instruções e premissas do projeto para o assistente.
- `app/` — código do produto (`backend` em Python/FastAPI, `frontend` em React).

## Como rodar
```
docker compose up --build    # depois abra http://127.0.0.1:8080
bash scripts/qualidade.sh    # lint, tipos e testes
```
Detalhes em [docs/06-deploy/execucao-local.md](docs/06-deploy/execucao-local.md).

## Configuração local
Copie `.env.example` para `.env` e preencha `DADOS_GOV_API_KEY`. O `.env` nunca é versionado.
