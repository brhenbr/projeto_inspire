# ADR-0015: Formato de exportação DCAT-BR e DQV

- **Status:** aceita (decidida de forma autônoma, conforme combinado)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
O projeto adota DCAT-BR, DQV e FAIR (CLAUDE.md). Falta exportar a base curada nesses padrões (atividade A5, antecipada
para o MVP a pedido do cliente). O vocabulário oficial traz o exemplo em Turtle; o catálogo real tem 20 mil conjuntos.

## Opções
**Opção 1 — Turtle (RDF).** É o formato do exemplo oficial e legível por pessoas. Mas exige uma biblioteca RDF para
serializar com segurança (escapes, prefixos) ou código próprio frágil; mais difícil de consumir por aplicações web.

**Opção 2 — JSON-LD gerado por código próprio, em fluxo (escolhida).** Mesmo modelo RDF, em JSON que qualquer
linguagem lê, e que ferramentas RDF convertem para Turtle. Sem dependência nova, serializa por conjunto (memória
constante), reaproveita os filtros e coleções da exportação atual. Custo: menos legível que Turtle e sem validação
formal automática no MVP.

**Opção 3 — Biblioteca rdflib com várias saídas.** Turtle, JSON-LD e RDF/XML prontos. Mas é dependência grande para um
uso simples, monta o grafo todo em memória (20 mil conjuntos, ~150 MB) e amplia a superfície a auditar (ADR-0002).

## Decisão
**Opção 2.** Parâmetro `saida=jsonld` nas rotas de exportação existentes e botão "Exportar DCAT-BR" na busca e nas
coleções. Turtle pode ser acrescentado depois sem mudar o modelo. Mapeamento campo a campo em
[mapeamento-dcat-br.md](../02-arquitetura/mapeamento-dcat-br.md).

## Consequências
- Contato do responsável nunca é exportado (dado pessoal); o campo obrigatório de contato do DCAT-BR fica vazio.
- A nota de qualidade segue DQV, com métricas descritas no próprio arquivo.
- Valor curado prevalece e o arquivo informa o status de curadoria, para o consumidor saber o que é confiável.
- Exportar o catálogo inteiro leva ~45 s; é aceitável para um MVP monousuário.
