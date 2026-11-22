# ADR-0014: Roteador de provedores gratuitos de LLM

- **Status:** aceita
- **Data:** 2026-11-21
- **Decisores:** cliente (direção) e Claude (desenho)

## Contexto
O cliente pediu usar as APIs gratuitas dos principais fornecedores (Groq, Gemini, DeepSeek e outros com camada
gratuita) e que o sistema **troque de provedor sozinho quando um estourar o limite**. Camadas gratuitas têm
cotas baixas e mudam com frequência. O [ADR-0004](0004-provedor-de-llm-externo-controlado.md) continua valendo:
só campos públicos, desligado por padrão, provedores aprovados explicitamente e aviso na tela.

## Opções
**Opção 1 — Um provedor por vez, troca manual no `.env`.** Simples e já existia. Mas a cota gratuita acaba no
meio de uma execução em lote e o item falha; exige intervenção humana.

**Opção 2 — Biblioteca pronta de roteamento (LiteLLM e similares).** Muitos provedores e recursos prontos.
Mas é dependência grande, com histórico de mudanças rápidas e superfície de ataque maior, em conflito com a regra
"dependências mínimas, auditáveis" ([ADR-0002](0002-seguranca-e-soberania.md)); também faria telemetria/atualizações
de preço fora do nosso controle.

**Opção 3 — Roteador próprio, pequeno, sobre o protocolo "chat completions" (escolhida).** Os provedores citados
falam esse protocolo, que o projeto já usa ([ADR-0011](0011-integracao-com-llm.md)). O roteador tenta os provedores
na ordem de preferência; HTTP 429 (cota, com `Retry-After`) ou 402 (saldo) coloca o provedor em pausa e passa ao
próximo; 401/403 desativa o provedor por 24 h; falha transitória (rede, 5xx) pausa por 30 s. Se todos estão em
pausa por pouco tempo, espera; se por muito, o item falha com mensagem clara. Custo: manter nosso código (~150 linhas
com testes) e atualizar modelos padrão quando as camadas gratuitas mudarem.

## Decisão
**Opção 3.** Detalhes:
- `LLM_PROVIDER=roteador`. `LLM_ROUTER_PROVIDERS` lista os provedores aprovados **por nome**; o host de cada um é fixo
  no código (não vem do ambiente), então a lista é a aprovação do ADR-0004 e não dá para apontar para um host qualquer.
- Provedor sem chave é ignorado; sem nenhuma chave, o recurso fica desligado com motivo explícito.
- Chaves: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`
  (modelo trocável por `LLM_<NOME>_MODEL`). Ficam só no `.env` e em `SecretStr`; nunca em log ou `repr`.
- Cada proposta registra quem respondeu (`curadoria.llm_proposta.provedor`, migração 0007), para auditoria.
- As chaves vão à API e ao worker (a API valida o provedor ao criar a execução); é um afrouxamento pequeno do menor
  privilégio, aceito porque a API não chama o provedor.

## Consequências
- Execuções em lote deixam de parar por cota de um único provedor.
- O estado de pausa vive na memória do processo (por execução); não é compartilhado entre execuções. Aceitável no MVP.
- DeepSeek não tem camada gratuita permanente (cobra por uso); fica na lista, mas só é usado se o cliente criar chave.
- Modelos padrão foram conferidos com chamadas reais em 2026-11-21 (groq gpt-oss-120b, gemini-3.5-flash, openrouter nemotron free, cerebras gpt-oss-120b); nomes antigos (llama-3.3, gemini-2.5) já não existiam para contas novas, então devem ser reconferidos de tempos em tempos.
- Todos os provedores da lista recebem **somente campos públicos**; é a mesma barreira de antes, aplicada antes do roteador.
