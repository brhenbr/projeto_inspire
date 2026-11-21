# C4 — Nível 1: Contexto do sistema

Mostra o Inspire Catálogo, quem o usa e com quais sistemas externos ele conversa. Não depende de
tecnologia. Linhas tracejadas são integrações previstas para depois do MVP.

```mermaid
flowchart TB
    curador["👤 <b>Curador(a)</b><br/>Revisa e melhora metadados"]
    coord["👤 <b>Coordenação do projeto</b><br/>Acompanha a qualidade e a evolução"]
    explorador["👤 <b>Explorador(a) de dados</b><br/>Busca dados para análise"]

    sistema["<b>Inspire Catálogo</b><br/>[Sistema de software]<br/>Espelha o catálogo do dados.gov.br, permite explorá-lo,<br/>mede a qualidade dos metadados e organiza a curadoria<br/>com apoio de LLM"]

    portal["<b>Portal dados.gov.br</b><br/>[Sistema externo]<br/>API REST com chave; fonte dos metadados<br/>(~20,7 mil conjuntos)"]
    llm["<b>Provedor de LLM</b><br/>[Sistema externo controlado]<br/>Local ou sob controle do projeto;<br/>troca por configuração"]
    orgaos["<b>Servidores dos órgãos</b><br/>[Sistema externo]<br/>Hospedam os recursos (arquivos e APIs)"]
    jira["<b>Jira</b><br/>[Ferramenta de gestão]<br/>Backlog do projeto"]

    curador -->|"Cura metadados e aprova<br/>propostas do LLM [web]"| sistema
    coord -->|"Consulta indicadores [web]"| sistema
    explorador -->|"Busca e explora [web]"| sistema
    sistema -->|"Extrai metadados<br/>[HTTPS, chave de API]"| portal
    sistema -->|"Pede propostas de curadoria<br/>[API compatível com OpenAI]"| llm
    sistema -.->|"Fase 2: verifica links<br/>(sem baixar dados)"| orgaos
    sistema -.->|"Futuro: propõe alterações"| portal
    jira -.->|"Backlog importado por CSV<br/>(manual, fora do sistema)"| sistema

    classDef pessoa fill:#08427b,stroke:#052e56,color:#fff
    classDef nosso fill:#1168bd,stroke:#0b4884,color:#fff
    classDef externo fill:#999,stroke:#6b6b6b,color:#fff
    class curador,coord,explorador pessoa
    class sistema nosso
    class portal,llm,orgaos,jira externo
```

## Notas
- O Jira não integra com o sistema em tempo de execução; aparece só para situar o backlog.
- A seta tracejada de volta ao portal exige perfil de administrador de organização e não está no
  curto nem no médio prazo; o modelo de dados já separa espelho e curadoria para viabilizá-la.
- Segurança e soberania ([ADR-0002](../03-decisoes/0002-seguranca-e-soberania.md)): o único sistema
  externo que recebe dados do projeto seria o provedor de LLM, e ele deve ser local ou controlado.
