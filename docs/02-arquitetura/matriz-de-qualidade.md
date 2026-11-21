# Matriz de qualidade dos metadados

> Gerado por `python -m inspire.cli matriz-qualidade` a partir do código. **Não edite à mão**; para mudar pesos use a tela de configurações, e para mudar regras altere `quality/rules.py`.

**Em palavras simples:** cada conjunto recebe uma nota de 0 a 100 conforme cumpre uma lista de verificações simples (tem descrição? informa a licença? os dados estão atualizados? há formato aberto?). Cada verificação tem um peso. Quando falta informação para julgar uma verificação, ela fica de fora da conta em vez de punir o conjunto. Os pesos abaixo são um ponto de partida e podem ser ajustados.

Decisão e alternativas: [ADR-0009](../03-decisoes/0009-modelo-de-qualidade.md). Padrões de referência definidos pelo projeto: **DCAT-BR**, **DQV** e princípios **FAIR**; na dúvida, **DMBOK**.

## Como a nota é calculada
- `nota = 100 * (soma dos pesos das regras aprovadas) / (soma dos pesos das regras avaliáveis e ativas)`.
- A nota por dimensão usa a mesma conta restrita às regras da dimensão.
- A nota usa os valores **efetivos** (já com a curadoria): melhorar um metadado sobe a nota.
- Conjuntos removidos do portal ou sem detalhe disponível não recebem nota.

## Completude

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `COMP-01` Título descritivo | O título tem ao menos 15 caracteres e não parece um identificador. | 1 | DMBOK2 (completude e clareza); FAIR F2 |
| `COMP-02` Descrição adequada | A descrição tem ao menos 100 caracteres. | 3 | DMBOK2 (completude); FAIR F2/R1 |
| `COMP-03` Licença informada | O conjunto informa a licença de uso. | 2 | FAIR R1.1; DCAT-BR dct:license |
| `COMP-04` Periodicidade informada | O conjunto informa a periodicidade de atualização. | 2 | DQV (completude); DCAT dct:accrualPeriodicity |
| `COMP-05` Palavras-chave suficientes | O conjunto tem ao menos 3 palavras-chave. | 2 | FAIR F2/F4 (descoberta); DCAT dcat:keyword |
| `COMP-06` Tema atribuído | O conjunto está classificado em ao menos um tema. | 1 | FAIR F4; DCAT dcat:theme |
| `COMP-07` Cobertura informada | O conjunto informa cobertura temporal ou espacial. | 1 | DQV (completude); DCAT dct:temporal/dct:spatial |
| `COMP-08` Ponto de contato | O conjunto tem um responsável de contato registrado no portal. | 1 | DCAT-BR dcat:contactPoint |

## Compreensibilidade

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `COMP-09` Recursos descritos | Ao menos metade dos recursos tem descrição. | 1 | DQV (compreensibilidade); FAIR R1 |

## Atualidade

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `TIME-01` Atualizado conforme a periodicidade | A última atualização dos dados está dentro do intervalo esperado (com folga de 50%). | 3 | DMBOK2 (atualidade); DQV timeliness |
| `TIME-02` Atualizado segundo o portal | O portal classifica o conjunto como atualizado. | 1 | Indicador do próprio portal |

## Acessibilidade

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `ACC-01` Possui recurso | O conjunto tem ao menos um recurso associado. | 3 | FAIR A1; DQV availability |
| `ACC-02` Links válidos | Todos os recursos têm um link http(s) bem formado. | 2 | FAIR A1; DCAT dcat:accessURL (verificação ativa: fase 2) |

## Processabilidade

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `OPEN-01` Formato aberto | Ao menos um recurso está em formato aberto e legível por máquina. | 3 | 5 estrelas de dados abertos; FAIR I1 |
| `OPEN-02` Dados abertos segundo o portal | O portal marca os dados como abertos. | 1 | Indicador do próprio portal |

## Conformidade

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `CONF-01` Licença aberta | A licença informada é reconhecida como aberta. | 2 | FAIR R1.1; Open Definition |

## Consistência

| Regra | Verificação | Peso | Fonte |
|---|---|---|---|
| `CONS-01` Formato coerente com o link | O formato declarado bate com a extensão do link. | 1 | DMBOK2 (consistência); DQV consistency |

## Parâmetros das regras
- **Formatos abertos reconhecidos:** API, CSV, GEOJSON, JSON, JSON-LD, JSONLD, ODS, PARQUET, RDF, TSV, TTL, TURTLE, XML.
- **Licenças reconhecidas como abertas:** cc-by, cc-by-sa, cc-zero, cc0, gfdl, odc-by, odc-odbl, odc-pddl, ogl-uk, other-open.
- **Folga de atualidade:** 50% sobre o intervalo da periodicidade. Intervalos (dias): Tempo Real 1, Diaria 1, Semanal 7, Quinzenal 15, Mensal 31, Bimestral 62, Trimestral 92, Quadrimestral 123, Semestral 183, Anual 366, Bienal 731.

## Limites conhecidos
- Regras binárias são grosseiras (uma descrição com 99 caracteres reprova); gradação é possível no futuro.
- **Disponibilidade real dos links** (o link responde?) não é verificada: fica para a fase 2 (EP-08). Hoje só se verifica se o link é um endereço http(s) bem formado.
- A mensuração de aderência ao DCAT-BR (propriedades obrigatórias e recomendadas) entra com o épico EP-11; a especificação oficial v1.0 do Catálogo Nacional de Dados deve ser lida e mapeada antes (US-100).
- Os pesos não foram validados com o cliente nem com o CPQD.

