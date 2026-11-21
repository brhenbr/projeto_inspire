# Inspire Catálogo — extração e curadoria do catálogo do dados.gov.br

Protótipo web para extrair, explorar (*data discovery*) e curar, com apoio de LLMs, os metadados do
catálogo do Portal Brasileiro de Dados Abertos, no contexto do projeto Inspire.

**Status:** fase de descoberta e desenho. Ainda não há código do produto.

## Onde está cada coisa
- [docs/](docs/) — descoberta, produto, arquitetura (C4), decisões (ADRs), implementação, testes, deploy e diário.
- [kit/](kit/) — kit de processo reaproveitável em outros projetos.
- [CLAUDE.md](CLAUDE.md) — instruções e premissas do projeto para o assistente.
- `app/` — código do produto (a criar).

## Configuração local
Copie `.env.example` para `.env` e preencha `DADOS_GOV_API_KEY`. O `.env` nunca é versionado.
