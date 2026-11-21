# C4 — Nível 2: Contêineres

**Em palavras simples:** o sistema é feito de cinco peças que rodam juntas: a tela que o usuário vê (Web), o
"cérebro" que atende pedidos (API), um trabalhador que faz as tarefas demoradas em segundo plano (Worker), o
banco de dados e, de forma opcional, um LLM rodando localmente. Fora dele ficam o portal de dados e,
opcionalmente, uma API de LLM.

Mostra as partes executáveis do Inspire Catálogo e como se comunicam. Reflete
[ADR-0003](../03-decisoes/0003-stack-tecnologica.md) (stack),
[ADR-0004](../03-decisoes/0004-provedor-de-llm-externo-controlado.md) (LLM) e
[ADR-0005](../03-decisoes/0005-armazenamento-em-camadas.md) (armazenamento).
Linhas tracejadas são opcionais ou futuras.

```mermaid
flowchart TB
    user["👤 Curador / Coordenação / Explorador"]

    subgraph sistema["Inspire Catálogo (Docker Compose)"]
        web["<b>Web</b><br/>[React + TypeScript]<br/>Interface do usuário"]
        api["<b>API</b><br/>[Python, FastAPI]<br/>REST /v1 em OpenAPI;<br/>regras de negócio e orquestração"]
        worker["<b>Worker</b><br/>[Python]<br/>Extração, normalização,<br/>qualidade e lotes de LLM"]
        db[("<b>PostgreSQL</b><br/>schemas: raw · catalogo ·<br/>curadoria · analitico<br/>+ busca textual + fila de jobs")]
        llmlocal["<b>LLM local</b><br/>[Ollama ou vLLM]<br/>Perfil opcional 'llm-local',<br/>só com GPU"]
    end

    portal["<b>Portal dados.gov.br</b><br/>[externo]"]
    llmext["<b>API de LLM</b><br/>[externo opcional, gratuito]<br/>campos públicos apenas"]

    user -->|HTTPS| web
    web -->|"JSON/HTTPS"| api
    api -->|"consulta e grava;<br/>enfileira jobs"| db
    worker -->|"consome jobs;<br/>grava as camadas"| db
    worker -->|"HTTPS + chave de API"| portal
    worker -->|"prompts e propostas<br/>(API compatível com OpenAI)"| llmext
    worker -.->|"mesma interface,<br/>rede interna"| llmlocal

    classDef nosso fill:#1168bd,stroke:#0b4884,color:#fff
    classDef opc fill:#5b9bd5,stroke:#3a6fa0,color:#fff,stroke-dasharray: 5 3
    classDef ext fill:#999,stroke:#6b6b6b,color:#fff
    class web,api,worker,db nosso
    class llmlocal opc
    class portal,llmext ext
```

## Notas de desenho
- **Troca de LLM por configuração:** o worker fala com qualquer servidor compatível com a API da
  OpenAI, externo ou local. Habilitar GPU no futuro é ligar o perfil `llm-local` e apontar a
  configuração para ele; nenhum código de negócio muda (US-069).
- **Ponto único de entrada:** só o `web` fica exposto; `api`, `worker`, `db` e LLM local ficam em rede
  interna.
- **Snapshot só quando muda:** o JSON bruto é gravado em `raw` apenas se o hash mudou.
- **A API também consulta o LLM no futuro** (chat em linguagem natural, EP-09); por isso o contrato é
  compartilhado entre API e worker.
