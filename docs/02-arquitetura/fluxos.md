# C4 — Nível 4: Fluxos e estados

**Em palavras simples:** estes diagramas contam o que acontece, passo a passo, nas duas operações mais
importantes (trazer o catálogo do portal e curar com ajuda do LLM) e mostram por quais situações passam
as coisas que têm ciclo de vida (uma extração, um conjunto em curadoria, uma proposta do LLM). Não há
diagramas de classes, como combinado.

## 1. Extração do catálogo

A API do portal é intermitente: pode devolver lista vazia e logo depois devolver dados. Por isso uma
página vazia nunca encerra a coleta sozinha: o sistema tenta de novo e confere com o total que cada
organização declara ter.

```mermaid
sequenceDiagram
    autonumber
    actor U as Curador
    participant W as Web
    participant A as API
    participant F as Fila (PostgreSQL)
    participant K as Worker
    participant P as Portal dados.gov.br
    participant D as Banco (raw, catalogo)

    U->>W: Clica em Extrair catálogo
    W->>A: POST /v1/extracoes
    A->>F: Cria execução e enfileira o job
    A-->>W: 202 com o id da execução
    F->>K: Entrega o job
    K->>P: Dimensões (temas, tags, formatos, ODS, observância)
    K->>P: Organizações, todas as páginas
    Note over K,P: Cada organização informa quantos conjuntos tem, o total esperado
    loop Fase 1: listagem, página a página
        K->>P: GET conjuntos-dados?pagina=N
        alt Página vazia
            K->>P: Tenta de novo com espera crescente
            Note over K: Só considera o fim após confirmar com o total esperado
        end
        K->>D: Registra ids e resumos na fila de detalhe
    end
    loop Fase 2: detalhe de cada conjunto, com concorrência limitada
        K->>P: GET conjuntos-dados/id
        Note over K: Remove dados pessoais e calcula o hash
        alt Hash novo ou mudou
            K->>D: Grava o JSON em raw
            K->>D: Normaliza para catalogo
        else Hash igual
            K->>D: Só marca como visto nesta execução
        end
    end
    K->>D: Marca como removidos os conjuntos que não apareceram
    K->>D: Recalcula a qualidade dos conjuntos alterados
    K->>D: Grava o relatório (coletado x esperado, divergências, erros)
    W->>A: Consulta o progresso periodicamente
    A-->>W: Estado e contadores da execução
    U->>W: Abre o relatório da extração
```

**Pontos importantes**
- A execução pode ser **interrompida e retomada**: a fila de detalhe guarda o que falta.
- O hash é calculado **depois** de remover contatos pessoais (ver [modelo de dados](modelo-de-dados.md)).
- A chave da API só existe no ambiente do worker e nunca é registrada em log.

## 2. Curadoria assistida por LLM

Quem manda é o humano: escolhe os conjuntos, a tarefa e os parâmetros. O LLM só gera **propostas**.
Nada é aplicado sem aprovação.

```mermaid
sequenceDiagram
    autonumber
    actor U as Curador
    participant W as Web
    participant A as API
    participant F as Fila
    participant K as Worker
    participant X as Filtro de campos públicos
    participant L as Provedor de LLM
    participant D as Banco (curadoria)

    U->>W: Seleciona conjuntos, tarefa e parâmetros
    W->>A: POST /v1/execucoes-llm
    A->>F: Cria a execução e enfileira
    A-->>W: 202 com o id da execução
    F->>K: Entrega o job
    loop Para cada conjunto, um de cada vez
        K->>X: Monta o prompt com o texto do conjunto
        X-->>K: Prompt só com campos públicos
        K->>L: Pede a proposta
        alt Limite de uso ou falha temporária
            K->>L: Tenta de novo com espera e retoma depois
        end
        L-->>K: Texto proposto
        K->>D: Salva proposta pendente com modelo, versão, prompt e provedor
    end
    U->>W: Abre a fila de revisão
    W->>A: GET /v1/propostas
    A-->>W: Propostas com o original ao lado
    U->>W: Aprova, edita ou rejeita
    W->>A: PATCH /v1/propostas/id
    A->>D: Aplica na camada curada e registra autoria e histórico
```

**Pontos importantes**
- Cada proposta guarda **quem a gerou** (modelo, versão, provedor, "externo" ou "local"), o prompt e a
  decisão humana. Isso atende à supervisão humana e à auditabilidade exigidas pelo GuIA.
- Se o conjunto mudar no portal **depois** que a proposta foi gerada, a proposta fica **desatualizada**
  e não pode ser aprovada sem nova revisão (US-045).

## 3. Estados

### 3.1 Execução de extração
```mermaid
stateDiagram-v2
    [*] --> Enfileirada
    Enfileirada --> EmAndamento: worker pega o job
    EmAndamento --> Pausada: usuário pausa ou falha recuperável
    Pausada --> EmAndamento: retomada
    EmAndamento --> Concluida: tudo conferido
    EmAndamento --> ConcluidaComDivergencias: faltaram itens após as tentativas
    EmAndamento --> Falhou: erro não recuperável
    EmAndamento --> Cancelada: usuário cancela
    Pausada --> Cancelada: usuário cancela
    Concluida --> [*]
    ConcluidaComDivergencias --> [*]
    Falhou --> [*]
    Cancelada --> [*]
```

### 3.2 Status de curadoria de um conjunto
```mermaid
stateDiagram-v2
    [*] --> Pendente
    Pendente --> EmRevisao: curador assume
    EmRevisao --> Aprovado: revisão concluída
    EmRevisao --> Rejeitado: não aproveitar a curadoria
    EmRevisao --> Duplicado: marca duplicidade
    Aprovado --> EmRevisao: reabrir
    Rejeitado --> EmRevisao: reabrir
    Duplicado --> EmRevisao: reabrir
    Aprovado --> Pendente: conjunto mudou no portal
```

### 3.3 Proposta de LLM
```mermaid
stateDiagram-v2
    [*] --> Pendente: gerada pelo LLM
    Pendente --> Aprovada: humano aprova
    Pendente --> Editada: humano edita e aprova
    Pendente --> Rejeitada: humano rejeita
    Pendente --> Desatualizada: conjunto mudou no portal
    Desatualizada --> Pendente: reavaliada
    Aprovada --> [*]
    Editada --> [*]
    Rejeitada --> [*]
```
