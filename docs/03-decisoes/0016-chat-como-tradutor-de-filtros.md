# ADR-0016: Chat em linguagem natural como tradutor de filtros

- **Status:** aceita (decidida de forma autônoma, conforme combinado)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
O cliente quer explorar o catálogo por linguagem natural (desejável, não obrigatório) e, depois, montar coleções
descrevendo-as em texto. O LLM é externo e gratuito (ADR-0004, ADR-0014): não pode receber a base curada nem contatos,
tem cota baixa e pode errar. O catálogo tem 20 mil conjuntos, com busca por palavras e facetas já prontas (ADR-0008).

## Opções
**Opção 1 — LLM responde sobre os dados (RAG).** Recupera conjuntos, envia ao LLM e ele redige a resposta. Conversa
mais natural, mas envia dados do catálogo ao provedor externo a cada pergunta, gasta muita cota, e pode afirmar coisas
que não estão nos dados (alucinação) sem o usuário ter como conferir.

**Opção 2 — LLM só traduz o pedido em filtros; a busca existente executa (escolhida).** O modelo recebe apenas o texto
do usuário e o vocabulário público (temas, formatos, esferas, UFs); devolve JSON com filtros. O sistema valida cada
valor contra o vocabulário, descarta e informa o que não existe, resolve o órgão pelo nome real, e executa a busca de
sempre. O usuário vê os filtros e pode abri-los na busca para refinar. Custo: não "conversa" nem resume; entende
pedidos de filtragem, não perguntas analíticas.

**Opção 3 — Busca semântica por embeddings.** Acha por significado. Mas exige modelo de embeddings (API externa com os
dados do catálogo, ou modelo local em CPU), índice vetorial e reindexar a cada extração. Fica para a etapa de busca
semântica, avaliada à parte com o catálogo real.

## Decisão
**Opção 2.** `POST /v1/chat/perguntar` e a tela "Perguntar". Detalhes de segurança e qualidade:
- Só o texto (até 500 caracteres) e o vocabulário público vão ao provedor; a tela avisa para não escrever dados pessoais.
- Saída validada: valor fora do vocabulário é descartado e listado em "Não consegui usar".
- **Afrouxamento:** se a busca volta vazia, o sistema solta filtros especulativos um a um (periodicidade, esfera, nota,
  formato, tema, UF, órgão, palavras, nessa ordem) e diz quais soltou. Evita o "zero resultado" por excesso de filtro
  do modelo, medido no catálogo real.
- Modo simulado: reconhece temas, formatos, esfera e estado por regras, para demonstrar e testar sem rede.
- O mesmo interpretador servirá à criação de coleções por texto (próxima etapa).

## Consequências
- Nenhum dado do catálogo sai da infraestrutura por causa do chat; só a pergunta do usuário.
- A qualidade depende do modelo; por isso o usuário sempre vê e pode corrigir os filtros.
- Perguntas como "qual órgão publica mais?" não são atendidas (são analíticas); o painel cobre parte disso.

## Complemento: coleções por texto e vários temas
- `POST /v1/chat/colecao` usa o mesmo interpretador para **propor** os filtros de uma coleção dinâmica. Não cria nada:
  o usuário remove filtros (a contagem atualiza na hora), confere uma amostra e só então confirma. Aqui **não há
  afrouxamento**, porque uma coleção deve refletir exatamente o que foi pedido.
- O filtro `tema` passou a aceitar vários slugs separados por vírgula (casa qualquer um), pois "saúde, assistência e
  educação" é o caso típico de coleção. Antes, o pedido virava uma busca de palavras que dava poucos resultados.
- O prompt manda não deduzir tema a partir do nome do órgão (o que gerava "Ministério da Saúde + tema saúde + CSV" = 0).
