# ADR-0010: Modelo de dados da curadoria

- **Status:** aceita (decidida de forma autônoma; revisada e confirmada pelo cliente em 2026-11-21)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
A curadoria (humana ou assistida por LLM) altera metadados de conjuntos. Requisitos já decididos:
o que veio do portal **nunca é sobrescrito**; é preciso histórico e autoria; a curadoria deve poder ser
revertida; e, no futuro, deve ser possível propor as alterações de volta ao portal
([ADR-0005](0005-armazenamento-em-camadas.md)). O portal pode mudar um campo que a curadoria também mudou.

## Opções consideradas
### 1. Sobrescrever o espelho e guardar uma cópia do original
- **Prós:** consulta simples.
- **Contras:** viola o princípio de não alterar o espelho; a próxima extração desfaria a curadoria ou
  exigiria lógica de mesclagem sobre dados misturados; perde a noção do que é do portal.

### 2. Cópia versionada do documento inteiro por conjunto (JSON curado)
- **Prós:** cada versão é completa e fácil de exibir; permite exportar um documento curado inteiro.
- **Contras:** duplica dados que não mudaram; difícil saber **o que** mudou entre versões; conflitos
  com mudanças do portal ficam opacos; o diff para propor ao portal exige recalcular.

### 3. Registro de alterações por campo, só inserção (event log) — escolhida
Tabela `curadoria.alteracao` com uma linha por alteração de campo: conjunto, campo, valor (JSON), origem
(`humano` ou `llm`), autor, comentário, data e a proposta de LLM que a originou. O valor **efetivo** é a
alteração mais recente de cada campo; uma alteração com valor nulo **reverte** o campo ao original.
- **Prós:** guarda só diferenças; histórico e auditoria naturais; reversão trivial (nova linha); mostra
  exatamente o que mudou (base do pacote de propostas ao portal); a origem (humano ou modelo) fica registrada.
- **Contras:** o valor efetivo exige agregação (resolvido pelo modelo de leitura, ADR-0008); só campos
  previstos são editáveis (título, descrição, tags, temas, periodicidade, licença).

## Decisão
**Opção 3.** O estado de revisão fica à parte (`curadoria.status_conjunto`: pendente, em revisão, aprovado,
rejeitado, duplicado).

**Conflito com o portal:** se o portal mudar um conjunto depois de curado, a curadoria **permanece**
(prevalece o valor curado), o status "aprovado" volta a "pendente" para nova revisão humana e as propostas
de LLM pendentes ficam "desatualizadas". Nada é perdido e nada é aprovado sem olhar.

## Consequências
- Cada campo editável precisa de validação e de comparação com o original (edição igual ao original vira
  reversão, para não marcar "curado" sem diferença real).
- O modelo de leitura é atualizado a cada alteração (por conjunto, na hora).
- O futuro pacote de propostas ao portal é, em essência, a lista de alterações efetivas aprovadas.
