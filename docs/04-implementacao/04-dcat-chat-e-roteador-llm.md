# Implementação 04 — Roteador de LLM, exportação DCAT-BR, chat e coleção por texto

**Em palavras simples:** o sistema agora (1) usa vários LLMs gratuitos e troca sozinho de um para o outro quando a cota
de um acaba, (2) exporta o catálogo no padrão do governo (DCAT-BR) com a nota de qualidade (DQV), (3) deixa você
**perguntar em português** o que procura e (4) deixa **descrever uma coleção em texto**. Em todos os casos o LLM nunca
vê os dados do catálogo e nada é criado ou alterado sem a sua confirmação.

- **Período:** 2026-11-21, em modo autônomo
- **Backlog:** US-100, US-101, US-150, US-151, US-152 concluídos; US-081 parcial; US-067 parcial (ver [backlog](../01-produto/backlog/backlog.md))

## O que existe
| Entrega | Onde | Decisão |
|---|---|---|
| Roteador de provedores (Groq, Gemini, OpenRouter, Cerebras, Mistral, DeepSeek), pausa por cota, registro de quem respondeu | `llm/providers.py`, migração 0007 | [ADR-0014](../03-decisoes/0014-roteador-de-provedores-llm.md) |
| Exportação DCAT-BR em JSON-LD com DQV, em fluxo | `export/dcat.py`, `saida=jsonld` | [ADR-0015](../03-decisoes/0015-formato-de-exportacao-dcat-br-dqv.md), [mapeamento](../02-arquitetura/mapeamento-dcat-br.md) |
| Chat: pedido em português vira filtros da busca | `llm/interpret.py`, `api/routes/chat.py`, tela **Perguntar** | [ADR-0016](../03-decisoes/0016-chat-como-tradutor-de-filtros.md) |
| Coleção dinâmica por texto, com ajuste de filtros e confirmação | `POST /v1/chat/colecao`, cartão em **Coleções** | ADR-0016 (complemento) |
| Filtro de tema com vários valores (qualquer um) | `discovery/search.py` | ADR-0016 (complemento) |
| Descrição por LLM: recusa respostas do tipo "descrição não informada" | `llm/tasks.py` (tarefa versão 2) | — |

## Medido com os provedores reais (2026-11-21)
- Quatro provedores responderam com os modelos padrão atuais; **os nomes de modelo que eu tinha escolhido por memória
  (llama-3.3, gemini-2.5) não existiam mais para contas novas**: os modelos agora são conferidos com chamadas reais.
- Pedidos de teste no catálogo real: "violência contra a mulher" achou 5 conjuntos certeiros; "Ministério da Saúde em
  CSV" achou 149; "bases sociais federais de saúde, assistência e educação" virou 3 temas + esfera e achou 25.
- Exportar o catálogo inteiro em DCAT-BR: 20.218 conjuntos, ~150 MB, ~45 s.

## Problemas encontrados e como foram resolvidos
1. **Modelos padrão inexistentes** (404 nos quatro provedores): listei os modelos de cada conta e testei cada candidato.
2. **O modelo filtrava demais** (repetia o tema em palavras-chave, deduzia tema do nome do órgão): prompt mais claro e
   **afrouxamento** de filtros especulativos no chat, com aviso ao usuário. Na coleção não afrouxa, de propósito.
3. **Pedidos com vários temas** viravam busca de palavras: o filtro de tema aceita lista.
4. **Mensagem "Salvo" sumia** ao salvar um metadado (o formulário remonta ao recarregar, e a mensagem morava nele):
   o estado foi para o componente pai.
5. **Testes herdavam as chaves reais do `.env`** do shell: o conftest ignora qualquer variável `*_API_KEY`.
6. **E2E:** seletores antigos ficaram ambíguos com os campos novos e um teste de ordenação lia a lista antes de ela
   atualizar (corrida no próprio teste); corrigidos.
7. **Descrição "não foi informada":** uma proposta de LLM dizia isso em vez de descrever; agora o prompt proíbe e a
   validação recusa.

## Limites conhecidos
- O estado de pausa por cota fica na memória de cada processo (API e worker separados); aceitável no MVP.
- O chat entende pedidos de **filtragem**, não perguntas analíticas ("qual órgão publica mais?").
- DCAT-BR: sem contato do responsável (dado pessoal), sem selos Bronze/Prata/Ouro e sem validação SHACL.
- Busca semântica por embeddings (US-080) **não foi feita**; o chat cobre grande parte do uso com custo muito menor.
