# C4 — Nível 4: Fluxos e estados

**Em palavras simples:** estes diagramas contam o que acontece, passo a passo, nas operações mais importantes
(trazer o catálogo do portal, curar com ajuda do LLM, perguntar em português e escolher qual LLM usar) e mostram por
quais situações passam as coisas que têm ciclo de vida (uma extração, um conjunto em curadoria, uma proposta do LLM).
Não há diagramas de classes, como combinado.

Mapa: **1** Extração · **2** Curadoria com LLM · **3** Estados · **4** Perguntar e coleção por texto · **5** Roteador de LLM.

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

### 1.1 O que acontece quando alguém pede uma extração

**Em palavras simples:** antes de gastar qualquer processamento, o sistema confere se já há uma extração
em andamento e se passou tempo suficiente desde a última. Clicar várias vezes não custa quase nada:
quem decide é o backend, e a tela só mostra o resultado ([ADR-0006](../03-decisoes/0006-controle-de-extracoes.md)).

```mermaid
flowchart TB
    inicio(["Pedido de extração<br/>(botão, API ou comando)"]) --> ativa{"Já existe uma<br/>extração ativa?"}
    ativa -->|"Sim"| devolve["Devolve a extração em curso<br/>e não cria outra"]
    ativa -->|"Não"| forcada{"Pedido forçado<br/>e confirmado?"}
    forcada -->|"Sim"| registra["Registra quem forçou"]
    forcada -->|"Não"| intervalo{"Passou o intervalo mínimo<br/>desde a última bem-sucedida?"}
    intervalo -->|"Não"| bloqueia["Recusa com o motivo<br/>e o horário em que libera"]
    intervalo -->|"Sim"| cria["Cria a execução<br/>e enfileira"]
    registra --> cria
    cria --> tipo{"Tipo"}
    tipo -->|"Incremental (padrão)"| inc["Lista tudo e busca o detalhe<br/>só do que mudou"]
    tipo -->|"Completa"| comp["Lista tudo e busca o detalhe<br/>de todos os conjuntos"]

    classDef ok fill:#1168bd,stroke:#0b4884,color:#fff
    classDef nao fill:#999,stroke:#6b6b6b,color:#fff
    class cria,inc,comp,registra ok
    class devolve,bloqueia nao
```

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

## 4. Perguntar em linguagem natural e coleção por texto

**Em palavras simples:** você escreve o que procura. O LLM só **traduz** o pedido em filtros; quem busca é o próprio
catálogo, e você vê (e pode corrigir) os filtros usados. Na coleção por texto, nada é criado até você confirmar
([ADR-0016](../03-decisoes/0016-chat-como-tradutor-de-filtros.md)).

```mermaid
sequenceDiagram
    autonumber
    actor U as Pessoa
    participant W as Tela
    participant A as Servidor
    participant D as Banco
    participant R as Roteador de LLM

    U->>W: Escreve o pedido
    W->>A: Envia o texto
    A->>D: Lê a lista de temas e formatos (vocabulário público)
    A->>R: Texto + vocabulário (nada do catálogo curado, nenhum contato)
    R-->>A: Filtros em JSON
    Note over A: Valida cada filtro contra o vocabulário e descarta o que não existe
    A->>D: Busca com os filtros válidos
    alt Perguntar: nenhum resultado
        Note over A: Solta filtros um a um (periodicidade, esfera, nota, formato...) e avisa quais
    end
    A-->>W: Filtros entendidos, o que foi descartado e os primeiros resultados
    alt Coleção por texto
        U->>W: Ajusta os filtros (×), confere a amostra e confirma
        W->>A: Cria a coleção dinâmica com a regra
    end
```

**Pontos importantes**
- Só o **texto digitado** e o **vocabulário público** vão ao provedor; a tela avisa quando o provedor é externo.
- Na coleção **não há afrouxamento**: ela precisa refletir exatamente o que foi pedido; coleção com zero conjuntos não é criada.

## 5. Roteador de LLM: o que acontece quando um provedor falha ou acaba a cota

**Em palavras simples:** há vários LLMs gratuitos, cada um com uma cota pequena. O sistema tenta o primeiro; se ele
acabou a cota, passa para o próximo e volta a ele depois. Se tudo estiver indisponível, avisa em vez de travar
([ADR-0014](../03-decisoes/0014-roteador-de-provedores-llm.md)).

```mermaid
flowchart TB
    inicio(["Pedido de sugestão ou<br/>interpretação"]) --> prox{"Há provedor<br/>fora de pausa?"}
    prox -->|"Sim, o próximo da lista"| chama["Chama o provedor"]
    prox -->|"Não"| espera{"Alguma pausa termina<br/>em menos de 65 s?"}
    espera -->|"Sim"| aguarda["Espera e tenta de novo"]
    espera -->|"Não"| falha["Falha com mensagem clara:<br/>todos indisponíveis agora"]
    aguarda --> prox
    chama --> resp{"Resposta"}
    resp -->|"Ok"| ok["Usa a resposta e registra<br/>qual provedor respondeu"]
    resp -->|"Cota esgotada (429 ou 402)"| pausa["Pausa o provedor pelo tempo<br/>que ele informar"]
    resp -->|"Credencial recusada (401 ou 403)"| desliga["Desativa o provedor por 24 h"]
    resp -->|"Erro de rede ou 5xx"| curta["Pausa o provedor por 30 s"]
    pausa --> prox
    desliga --> prox
    curta --> prox

    classDef ok fill:#1168bd,stroke:#0b4884,color:#fff
    classDef nao fill:#999,stroke:#6b6b6b,color:#fff
    class ok,chama ok
    class falha,pausa,desliga,curta nao
```

**Pontos importantes**
- Provedor **sem chave** é ignorado. Cada proposta guarda **qual provedor respondeu**, para auditoria.
- A pausa vive na memória de cada processo (servidor e trabalhador separados); aceitável no MVP
  (ver [limites conhecidos](../01-produto/limites-conhecidos.md)).
