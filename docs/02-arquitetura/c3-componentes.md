# C4 — Nível 3: Componentes do servidor

**Em palavras simples:** por dentro, o servidor é dividido em **módulos**, cada um com uma função: trazer dados do
portal, organizá-los, buscar, medir a qualidade, registrar a curadoria, conversar com o LLM e exportar. Cada módulo cuida
da sua parte e pede aos outros o que não é dele. Tudo o que fala com o mundo de fora (portal, banco, LLM) passa por uma
peça trocável; é isso que permite, por exemplo, trocar de LLM sem mexer no resto.

*O servidor (`api`) e o trabalhador (`worker`) usam o mesmo código. Muda só quem dispara: uma chamada da tela ou um
pedido da fila.*

```mermaid
flowchart TB
    entradas["<b>Entradas</b><br/>API REST (chamadas da tela)<br/>e trabalhador (pedidos da fila)"]

    subgraph m1["Trazer, achar e medir"]
        direction LR
        extracao["<b>Extração</b><br/>Copia e atualiza<br/>as descrições"]
        descoberta["<b>Descoberta</b><br/>Busca, filtros,<br/>painel, organizações"]
        qualidade["<b>Qualidade</b><br/>Nota explicada<br/>de 0 a 100"]
    end

    subgraph m2["Melhorar, organizar e entregar"]
        direction LR
        curadoria["<b>Curadoria</b><br/>Correções, status<br/>e coleções"]
        assistente["<b>Assistente de LLM</b><br/>Sugestões e interpretação<br/>de pedidos"]
        exporta["<b>Exportação</b><br/>CSV, JSON, DCAT-BR"]
    end

    subgraph fora["Peças que falam com o mundo de fora"]
        direction LR
        cliente["<b>Cliente do portal</b><br/>Ritmo limitado e<br/>nova tentativa"]
        banco["<b>Banco em camadas</b><br/>raw, catalogo,<br/>curadoria, analitico"]
        gate["<b>Roteador de LLM</b><br/>Só campos públicos; troca<br/>de provedor por cota"]
    end

    entradas -->|"chamam"| m1
    entradas -->|"chamam"| m2
    extracao -->|"1. pede ao portal"| cliente
    assistente -->|"2. pede ao LLM"| gate
    m1 -->|"3. leem e gravam"| banco
    m2 -->|"3. leem e gravam"| banco

    classDef ent fill:#08427b,stroke:#052e56,color:#fff
    classDef mod fill:#1168bd,stroke:#0b4884,color:#fff
    classDef ada fill:#5b9bd5,stroke:#3a6fa0,color:#fff
    class entradas ent
    class extracao,descoberta,qualidade,curadoria,assistente,exporta mod
    class cliente,banco,gate ada
```

## O que cada módulo faz
| Módulo | Função, em palavras simples | Pasta do código (`app/backend/src/inspire/`) | Quem o aciona |
|---|---|---|---|
| **Extração** | Copia as descrições do portal, tira os dados pessoais e transforma em tabelas; atualiza só o que mudou | `extraction/`, `worker/` | Botão "Atualizar catálogo" ou comando |
| **Descoberta** | Busca em português, filtros, painel, organizações, detalhe do conjunto | `discovery/`, `analytics/` | Telas Buscar, Painel, Organizações |
| **Qualidade** | Calcula a nota por regras e explica cada ponto | `quality/` | Depois de cada extração e ao editar os pesos |
| **Curadoria** | Guarda as correções ao lado do original, o status de revisão e as coleções | `curation/` | Telas Detalhe, Fila, Coleções |
| **Assistente de LLM** | Gera sugestões de curadoria; traduz pedidos em português em filtros; escolhe o provedor | `llm/` | Telas Sugestões de LLM, Perguntar, Coleções |
| **Exportação** | Gera CSV, JSON e DCAT-BR com qualidade em DQV | `export/` | Botões "Exportar" |
| *Entradas* | Rotas REST e laço do trabalhador | `api/`, `worker/` | Tela e fila |

## Regras de dependência (para quem altera o código)
- Cada módulo só usa as funções públicas dos outros; nenhum lê as tabelas de outro módulo por conta própria.
- **Só a Curadoria escreve no schema `curadoria`.** O Assistente de LLM apenas **propõe**; a aplicação da proposta passa
  pela Curadoria e só acontece com a aprovação de uma pessoa.
- **O LLM nunca recebe dados sem passar pela barreira de campos públicos** (testada: contatos pessoais não saem).
  O roteador de provedores fica atrás dessa barreira ([ADR-0014](../03-decisoes/0014-roteador-de-provedores-llm.md)).
- A tela usa apenas a API REST; não acessa o banco nem o LLM.
- O que depende de tecnologia concreta (Postgres, HTTP, provedor de LLM) fica nas peças de fora; trocar uma delas não
  exige mexer nos módulos.

## As telas (frontend)
| Tela | Módulos que usa |
|---|---|
| Painel, Buscar, Organizações, Detalhe | Descoberta, Qualidade, Curadoria |
| Perguntar | Assistente de LLM, Descoberta |
| Fila de curadoria, Coleções | Curadoria, Descoberta, Assistente de LLM (coleção por texto) |
| Sugestões de LLM | Assistente de LLM, Curadoria |
| Extração | Extração |
| Configurações | Qualidade |
