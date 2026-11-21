# ADR-0008: Busca textual e modelo de leitura (discovery)

- **Status:** aceita (decidida de forma autônoma, durante a ausência do cliente)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
O discovery precisa de busca em português com tolerância a acentos, filtros combináveis com contagem
(facetas), ordenação por relevância e resultado **que reflita a curadoria** (o conjunto "efetivo": original
mais alterações aprovadas). O catálogo tem ~20,7 mil conjuntos. A meta é resposta em até 1 s. O
[ADR-0003](0003-stack-tecnologica.md) já indicou a busca no PostgreSQL; falta decidir **como** e **onde**
fica o dado consultado.

## Opções consideradas
### 1. Motor de busca dedicado (Meilisearch ou OpenSearch)
- **Prós:** relevância e tolerância a erro de digitação de primeira linha; facetas nativas.
- **Contras:** novo serviço para operar, proteger e manter sincronizado com o banco; **segunda cópia dos
  dados** (risco de divergência com a curadoria); mais memória (a máquina de desenvolvimento tem 16 GB e o
  Docker 8 GB); desproporcional para 20 mil documentos.

### 2. PostgreSQL consultando direto as tabelas normalizadas (`catalogo` + `curadoria`)
- **Prós:** nenhuma cópia; simples.
- **Contras:** calcular o "efetivo" (junções com a última alteração de cada campo, arrays de tags e temas)
  a cada busca é lento e complica filtros e facetas; difícil indexar.

### 3. PostgreSQL com tabela de leitura materializada (`analitico.conjunto_busca`) — escolhida
Uma linha por conjunto, já com os valores efetivos, arrays (tags, temas, formatos), nota de qualidade, estado
de curadoria e um `tsvector` em português sem acentos. Índices GIN para texto e arrays, e trigram para
tolerância a erros de digitação no título.
- **Prós:** um único banco; consulta rápida e simples; facetas por `GROUP BY` sobre uma tabela só; é o
  "andar analítico" já previsto no ADR-0005; recalculável a qualquer momento a partir das camadas abaixo.
- **Contras:** é um derivado que precisa ser atualizado quando o catálogo ou a curadoria mudam (por conjunto,
  na hora; e completo ao fim de cada extração). Relevância menos sofisticada que a de um motor dedicado.

## Decisão
**Opção 3.** Busca por `websearch_to_tsquery('portuguese', …)` sobre texto sem acentos, com pesos (título >
tags e temas > descrição), mais fallback por similaridade de trigramas no título quando a busca exata não
retorna nada. Facetas calculadas sobre os mesmos filtros, sem contar o próprio filtro.

## Consequências
- A atualização do modelo de leitura é parte do fluxo de extração, de qualidade e de curadoria (testada).
- Se a relevância não bastar, um motor dedicado entra por trás da mesma API, alimentado por esta tabela.
- A busca semântica (fase 2) acrescenta uma coluna vetorial (`pgvector`) à mesma tabela.
