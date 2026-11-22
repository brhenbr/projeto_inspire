# ADR-0009: Modelo de pontuação da qualidade dos metadados

- **Status:** aceita (decidida de forma autônoma; revisada e confirmada pelo cliente em 2026-11-21)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
O projeto definiu DCAT-BR, DQV e os princípios FAIR como padrões, com o DMBOK como apoio nas dúvidas. Falta
decidir **como transformar isso em uma nota** por conjunto que seja explicável, configurável e útil para
priorizar a curadoria. O Plano de Trabalho da frente UFSCar pede padronização alinhada a DCAT-BR e DQV; o
cliente não forneceu pesos, então o modelo precisa ser ajustável.

## Opções consideradas
### 1. Nota única, regras binárias com pesos, agrupadas por dimensão — escolhida
Cada regra passa ou falha (ou "não é avaliável" por falta de dados) e tem um peso configurável. A nota é
a soma dos pesos das regras aprovadas sobre a soma dos pesos das regras avaliáveis, em 0 a 100. Cada regra
pertence a uma dimensão (Completude, Compreensibilidade, Atualidade, Acessibilidade, Processabilidade,
Conformidade, Consistência), com nota por dimensão.
- **Prós:** totalmente explicável ("perdeu pontos porque…"); simples de configurar e de auditar; regras não
  avaliáveis não punem injustamente; mapeia direto para dimensões do DQV, princípios FAIR e dimensões do DMBOK.
- **Contras:** regras binárias são grosseiras (descrição com 99 caracteres reprova); pesos iniciais são
  julgamento nosso, não do cliente.

### 2. Nota contínua por regra (0 a 1, com gradação)
- **Prós:** mais fina (ex.: completude proporcional).
- **Contras:** mais difícil de explicar e de testar; escolhas de curva arbitrárias para cada regra; custo
  maior sem validação do cliente que justifique a precisão.

### 3. Modelo estatístico ou baseado em LLM
- **Prós:** poderia captar qualidade semântica da descrição.
- **Contras:** opaco, não reprodutível, depende de provedor externo (ADR-0002/0004) e contraria o
  princípio de explicabilidade. O LLM entra como **apoio à curadoria**, não como juiz da nota.

## Decisão
**Opção 1.** As regras, dimensões, pesos e fontes estão em
[matriz-de-qualidade.md](../02-arquitetura/matriz-de-qualidade.md) e na tabela `analitico.regra_qualidade`.
Pesos e ativação são editáveis pela tela de configurações; ao mudar, a qualidade é recalculada. A nota usa
os valores **efetivos** (já com a curadoria), então melhorar um metadado sobe a nota.

## Consequências
- A nota é relativa a este conjunto de regras (versão registrada em cada cálculo).
- O cliente deve revisar os pesos; a matriz é o ponto de partida para a discussão com o CPQD.
- Verificação ativa de links (disponibilidade real) fica para a fase 2 e entra como nova regra.
