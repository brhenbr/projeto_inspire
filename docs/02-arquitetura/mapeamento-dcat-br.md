# Mapeamento para o DCAT-BR e o DQV

**Em palavras simples:** o DCAT-BR é o "formulário padrão" que o governo brasileiro usa para descrever conjuntos de
dados. Esta página mostra, campo a campo, como o nosso catálogo preenche esse formulário quando você usa o botão
"Exportar DCAT-BR". A nota de qualidade segue o DQV, o vocabulário do W3C para qualidade de dados.

Fonte: [Vocabulário Padrão DCAT-BR v1.0](https://www.gov.br/governodigital/pt-br/infraestrutura-nacional-de-dados/catalogo-nacional-de-dados/materiais-de-apoio/vocabulario-padrao-dcat-br-v1.0)
(leitura completa em 2026-11-21). Formato de saída: JSON-LD (`saida=jsonld`), em fluxo, com valor **efetivo**
(curado, quando existe). Decisão: [ADR-0015](../03-decisoes/0015-formato-de-exportacao-dcat-br-dqv.md).

## Conjunto de dados (`dcat:Dataset`)
| Propriedade DCAT-BR | Origem no sistema | Observação |
|---|---|---|
| `dct:title` | título efetivo | curado prevalece |
| `dct:description` | descrição efetiva | curada prevalece |
| `dcat:keyword` | tags efetivas | |
| `dcat:theme` | temas efetivos | `skos:Concept` com o slug do tema do portal em `skos:notation` |
| `dct:publisher` | organização | `foaf:Organization` com nome e slug |
| `dct:license` | licença efetiva | URI conhecida quando há equivalente (cc-by, odbl...); senão o texto; `notspecified` é omitido |
| `dct:accrualPeriodicity` | periodicidade efetiva | URI do vocabulário de frequências; **quadrimestral não tem termo**, vai como texto |
| `dct:issued` | primeira catalogação no portal | data |
| `dct:modified` | última alteração dos metadados | data |
| `dct:language` | fixo `pt-BR` | |
| `dct:accessRights` | fixo PUBLIC | só entram conjuntos públicos (escopo) |
| `dcat:version` | versão do portal | |
| `dct:spatial` / `dct:temporal` | cobertura espacial / temporal | só quando informadas; data `dd/mm/aaaa` convertida |
| `dcat:landingPage`, `prov:wasDerivedFrom` | página do conjunto no dados.gov.br | |
| `dcat:distribution` | recursos | ver abaixo |
| `dcat:contactPoint` | **não exportado** | nome e e-mail são dados pessoais e nem existem no banco (ADR-0002) |
| `dct:creator` | não exportado | o portal não informa a área técnica de forma confiável |

## Distribuição (`dcat:Distribution`)
`dcat:accessURL` (link do recurso, nunca baixado), `dct:title`, `dct:description`, `dct:format`, `dcat:byteSize`
(omitido quando 0, que significa "desconhecido").

## Qualidade (DQV)
Cada conjunto traz `dqv:hasQualityMeasurement` com a **nota geral** e **uma medida por dimensão** (Completude,
Atualidade, Conformidade, Consistência, Compreensibilidade, Processabilidade, Acessibilidade). As métricas
(`dqv:Metric`) são descritas uma vez no início do grafo, lidas das regras de qualidade (ADR-0009). O prefixo das
métricas é nosso (`inspire:`), em domínio reservado `.invalid`, até haver um endereço institucional.

## Extensões nossas (prefixo `inspire:`)
`inspire:statusCuradoria` (pendente, aprovado...) e `inspire:curado` (houve edição humana ou aprovada de LLM).

## Limites conhecidos
- O DCAT-BR define "selos" Bronze/Prata/Ouro por propriedade preenchida; **não calculamos selos** aqui (a nota é a nossa).
- Não validamos contra SHACL; a estrutura segue o exemplo oficial do vocabulário.
- Catálogo inteiro: ~150 MB e ~45 s (20 mil conjuntos); prefira exportar por coleção ou filtro.
- Textos do portal com caracteres corrompidos (�) saem como estão; o defeito é do portal.
