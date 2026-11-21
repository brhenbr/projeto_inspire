# ADR-0004: Uso de API gratuita de LLM, restrito a metadados públicos

- **Status:** aceita (exceção ao item 1 do [ADR-0002](0002-seguranca-e-soberania.md))
- **Data:** 2026-11-21
- **Decisores:** cliente (dono do produto) e Claude

## Contexto
A máquina de desenvolvimento não tem GPU útil e não há servidor com GPU confirmado. O cliente quer
usar qualquer LLM com API gratuita. O ADR-0002 proíbe, por padrão, enviar dados a serviços externos.

O que o LLM processa é o **texto público do catálogo** (título, descrição, tags, tema). Isso é público
por natureza. O que merece proteção é a base curada como um todo, as decisões de curadoria e os dados
pessoais de contato dos responsáveis, que existem nos metadados do portal.

## Opções consideradas
1. **Sem LLM até haver servidor próprio:** soberania total, mas adia uma das funções centrais e
   dificulta a demonstração.
2. **API gratuita sem restrições:** simples, mas contraria o ADR-0002.
3. **API gratuita com salvaguardas, só para metadados públicos (escolhida):** entrega a função agora,
   limita o risco e mantém a saída para um LLM soberano.

## Decisão
O uso de API externa gratuita é permitido **somente** com todas as salvaguardas abaixo:

1. **Desligado por padrão.** Só é ativado por configuração explícita (`LLM_ENABLED`).
2. **Lista de provedores aprovados.** O sistema só chama hosts presentes na lista de configuração.
3. **Minimização de dados.** O montador de prompts aceita apenas campos públicos: título, descrição,
   tags, tema, organização, formato, licença e periodicidade. Nome e e-mail de responsáveis nunca são
   enviados. Um teste automatizado garante isso.
4. **Um conjunto por vez.** Nunca se envia a base curada em bloco nem o histórico de decisões.
5. **Transparência.** A interface exibe um aviso quando um LLM externo está ativo, e cada proposta
   registra o provedor, o modelo e a marca "externo" (proveniência, US-043).
6. **Humano aprova** toda proposta (princípio do produto).
7. **Embeddings e busca semântica ficam locais** (modelo pequeno em CPU), sem envio a terceiros.
8. **Provedor trocável por configuração** (contrato compatível com a API da OpenAI), para migrar a um
   LLM soberano do CPQD ou da UFSCar sem alterar código. Quando existir um, esta exceção deve ser
   revista.

**Escolha dos provedores:** feita no spike US-067 contra estes critérios: contrato compatível com a
OpenAI; cota gratuita utilizável; termos sobre retenção e uso dos dados lidos e aceitos para dados
públicos; disponibilidade a partir do Brasil; qualidade em português. Nenhum provedor está aprovado
até o spike terminar.

## Consequências
- Cotas gratuitas têm limites de taxa e podem mudar ou acabar: o worker precisa de fila, retry e
  tolerância a falhas, e o produto não pode depender de um único provedor.
- A qualidade do modelo gratuito pode variar; a revisão humana continua obrigatória.
- Se alguém ampliar o que é enviado (ex.: textos de curadoria), é necessário novo ADR.
- O C2 passa a mostrar o provedor de LLM **fora** do sistema, como serviço externo opcional.
