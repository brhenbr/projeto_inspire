# C4 — Nível 1: Contexto

**Em palavras simples:** quem usa o sistema e com quais serviços de fora ele conversa. Três tipos de pessoa usam a tela;
o sistema busca as descrições no portal dados.gov.br e, se ligado, pede ajuda a um serviço de inteligência artificial.
Os resultados saem em arquivos que podem ir para planilhas ou outros sistemas.

*Leia primeiro [Como o sistema funciona](00-como-o-sistema-funciona.md). Aqui aparece só o que está fora do sistema.*

```mermaid
flowchart TB
    pessoas["👤 <b>Pessoas</b><br/>Explorador(a), curador(a), coordenação"]
    sistema["<b>Inspire Catálogo</b><br/>Cópia pesquisável do catálogo,<br/>com nota de qualidade e curadoria"]
    portal["<b>Portal dados.gov.br</b><br/>Fonte das descrições<br/>(cerca de 20 mil conjuntos)"]
    llm["<b>Serviços de LLM gratuitos</b><br/>Opcionais: Groq, Gemini e outros,<br/>com troca automática por cota"]
    saidas["<b>Planilhas e outros sistemas</b><br/>Recebem arquivos CSV, JSON e DCAT-BR"]

    pessoas -->|"1. Buscam, corrigem,<br/>organizam e exportam"| sistema
    sistema -->|"2. Traz as descrições<br/>(com chave de API)"| portal
    sistema -->|"3. Pede sugestões<br/>(só campos públicos)"| llm
    sistema -->|"4. Gera arquivos"| saidas

    classDef pessoa fill:#08427b,stroke:#052e56,color:#fff
    classDef nosso fill:#1168bd,stroke:#0b4884,color:#fff
    classDef externo fill:#999,stroke:#6b6b6b,color:#fff
    classDef opc fill:#999,stroke:#6b6b6b,color:#fff,stroke-dasharray: 5 3
    class pessoas pessoa
    class sistema nosso
    class portal,saidas externo
    class llm opc
```
*Tracejado = opcional.*

## Legenda das setas
| # | O que acontece | Observações |
|---|---|---|
| 1 | As pessoas usam o sistema pelo navegador | Um usuário por vez; não há login |
| 2 | O sistema copia as descrições do portal | Exige a chave de API do portal; ritmo limitado (4 chamadas por segundo) para não ser bloqueado |
| 3 | O sistema pede sugestões a um LLM | Desligado ou simulado por padrão; só campos públicos; nunca contatos pessoais |
| 4 | O sistema entrega arquivos | O que sai é só o que o usuário pede (uma busca ou uma coleção) |

## Para engenharia
- **Portal:** API REST com cabeçalho `chave-api-dados-abertos`. É intermitente (listas vazias ocasionais) e responde
  HTTP 405 se chamado rápido demais; o cliente trata as duas coisas (ver [fluxos](fluxos.md), seção 1).
- **LLM:** qualquer serviço compatível com a API "chat completions". Há provedor simulado (padrão) e um roteador de
  provedores gratuitos ([ADR-0014](../03-decisoes/0014-roteador-de-provedores-llm.md)).
- **Segurança e soberania** ([ADR-0002](../03-decisoes/0002-seguranca-e-soberania.md)): o único sistema externo que
  recebe dados do projeto é o provedor de LLM, e só com campos públicos ([ADR-0004](../03-decisoes/0004-provedor-de-llm-externo-controlado.md)).
- **Fora de escopo agora (fase 2):** verificar links dos recursos nos servidores dos órgãos e propor alterações de volta ao
  portal. O modelo de dados já separa o espelho da curadoria para viabilizar isso depois.
