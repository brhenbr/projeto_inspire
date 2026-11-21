# ADR-0005: Armazenamento em camadas (documento → tabular → analítico) em um único PostgreSQL

- **Status:** aceita (confirmada pelo cliente em 2026-11-21)
- **Data:** 2026-11-21
- **Decisores:** cliente (dono do produto) e Claude

## Contexto
O cliente sugeriu duas frentes de armazenamento: um banco de **documentos** para a extração, porque a
API devolve JSON, e uma visão **tabular/analítica** para a curadoria. A especificação técnica do
cliente recomenda o mesmo padrão em camadas (Raw/Bronze, Silver, Gold).

O volume é pequeno: ~20,7 mil conjuntos e dezenas de milhares de recursos, na ordem de centenas de MB
por foto completa do catálogo.

## Opções consideradas
1. **Dois motores:** MongoDB (ou similar) para o bruto e PostgreSQL para o tabular.
   - Prós: o bruto fica no formato natural.
   - Contras: dois sistemas para operar, copiar e proteger; sem transação entre as camadas; MongoDB usa
     a licença SSPL, que **não é open source reconhecido pela OSI**, ponto sensível para um projeto
     de governo; ganho nulo nesta escala.
2. **Um motor, camadas separadas (escolhida):** PostgreSQL com `jsonb` para o documento bruto e tabelas
   relacionais para o restante.
   - Prós: o `jsonb` é indexável e consultável; transações entre as camadas; um só backup; licença
     livre; menor custo operacional.
   - Contras: se um dia o bruto crescer muito, será preciso movê-lo.
3. **Só tabular, sem guardar o bruto:** mais simples, mas perde a capacidade de reprocessar e auditar.

## Decisão
Adotar a **separação em camadas que o cliente propôs**, em um único PostgreSQL, com um schema por camada:

| Camada | Schema | Conteúdo | Característica |
|---|---|---|---|
| Documento (bruto) | `raw` | JSON exatamente como veio da API, com hash, execução e data | Só inserção. O payload é gravado apenas quando o hash muda. |
| Tabular (espelho) | `catalogo` | Organizações, conjuntos, recursos, temas, tags etc., normalizados | **Reconstruível** a partir do `raw` por um passo de normalização idempotente. |
| Curadoria | `curadoria` | Alterações, status, coleções, propostas de LLM, execuções | Guarda diferenças sobre o espelho, com autoria e origem (humano ou modelo). |
| Analítico | `analitico` | Visões e visões materializadas: qualidade por conjunto/órgão/tema, séries históricas | Alimenta painéis e exportações; recalculável. |

Fluxo: `API do portal → raw (documento) → catalogo (normalização) → analitico (qualidade) ← curadoria`.

O acesso ao bruto passa por uma **porta** (`RawStore`). Se o volume ou a necessidade mudarem, trocar
por MongoDB/FerretDB ou armazenamento de objetos (ex.: MinIO) é trocar um adaptador, sem tocar no restante.

## Por que a camada bruta vale a pena
- Mudar uma regra de qualidade ou o mapeamento para DCAT-BR **não exige nova extração**: reprocessa-se
  o `raw`. Isso importa porque a extração completa é lenta (~20,7 mil chamadas) e a API é intermitente.
- Permite auditar o que o portal disse em cada data e detectar mudanças.

## Consequências
- O normalizador (raw → catálogo) é um componente central, testado e reexecutável.
- O modelo `catalogo` será desenhado já alinhado ao DCAT-BR, para facilitar a exportação futura (EP-11).
- Se no futuro o volume exigir outro motor para o bruto, troca-se o adaptador `RawStore`.
