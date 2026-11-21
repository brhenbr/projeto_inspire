# ADR-0011: Integração com LLM na curadoria

- **Status:** aceita (decidida de forma autônoma, durante a ausência do cliente)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
O cliente quer curadoria em que **o humano parametriza e o LLM executa**, com custo mínimo, sem GPU local e
com possibilidade de rodar um modelo em GPU no futuro. O [ADR-0004](0004-provedor-de-llm-externo-controlado.md)
já permite API gratuita externa, **somente** com campos públicos, desligada por padrão, com lista de
provedores aprovados e aviso na tela. Não há provedor aprovado nem chave: a escolha do provedor pertence
ao cliente. Falta decidir **como integrar** e **o que entregar já funcionando**.

## Opções consideradas
### 1. SDKs específicos de cada fornecedor
- **Prós:** recursos exclusivos de cada um.
- **Contras:** acopla o código a fornecedores; cada troca exige código novo; cresce a superfície de
  dependências (e de telemetria embutida nos SDKs).

### 2. Cliente HTTP próprio para o protocolo "chat completions" compatível com OpenAI — escolhida
- **Prós:** protocolo aberto aceito por quase todos os servidores (Ollama, vLLM, llama.cpp, LM Studio e vários
  serviços gratuitos); **trocar de provedor é só configuração**; mesmo contrato serve a um LLM soberano futuro;
  uma dependência já existente (`httpx`); fácil de testar com respostas simuladas.
- **Contras:** só o mínimo comum (texto e JSON); recursos avançados de cada fornecedor ficam de fora.

### 3. Biblioteca de abstração (LiteLLM, LangChain e similares)
- **Prós:** muitos provedores prontos.
- **Contras:** dependência grande, com muitas transitivas e histórico de telemetria opcional; contraria
  "software auditável e enxuto" (ADR-0002); esconde a barreira de dados que precisamos controlar.

## Decisão
**Opção 2**, com estas peças:
- Interface `LlmProvider` e duas implementações: **`openai-compatible`** (HTTP) e **`simulado`**.
- O **simulado** não usa IA: gera sugestões determinísticas por regras simples a partir dos metadados e é
  **sempre rotulado como simulado** na tela e no registro. Existe para que o fluxo completo (selecionar,
  executar, revisar, aprovar, auditar) funcione e possa ser demonstrado e testado **sem qualquer dado sair
  da máquina** e sem chave. Não substitui a avaliação de um modelo real.
- **Barreiras do ADR-0004, implementadas no código:** desligado por padrão (`LLM_ENABLED=false`); só
  chama hosts da lista `LLM_ALLOWED_HOSTS` (padrão: apenas locais); o prompt é montado por uma **lista
  fixa de campos públicos** (título, descrição, tags, temas, organização, formatos, licença,
  periodicidade) e nada além disso; um conjunto por chamada; o registro de cada proposta guarda provedor,
  modelo, indicação "externo" ou "local" e o prompt completo; a interface exibe aviso quando há provedor externo.
- **Humano aprova sempre.** Proposta nunca altera o catálogo sozinha.
- **Tarefas** parametrizáveis e versionadas: melhorar descrição, sugerir tags, sugerir tema.

## Consequências
- O cliente precisa escolher um provedor (ou subir um servidor com GPU) e preencher as variáveis `LLM_*`; sem
  isso, o produto funciona com o modo simulado e todo o resto.
- A qualidade das propostas depende do modelo escolhido; o spike US-067 avalia opções.
- A saída do modelo é tratada como **não confiável**: validada (JSON, tipos, limites) antes de virar proposta.
