# Decisões (ADRs)

Cada decisão relevante de arquitetura ou de produto tem um registro com contexto, opções (com prós e contras), a
decisão e as consequências. Modelo em [`kit/templates/adr.md`](../../kit/templates/adr.md).

| # | Decisão | Quem decidiu |
|---|---|---|
| [0001](0001-premissas-de-processo-e-escopo-inicial.md) | Premissas de processo e escopo inicial | Cliente e Claude |
| [0015](0015-formato-de-exportacao-dcat-br-dqv.md) | Exportação DCAT-BR/DQV em JSON-LD gerado em fluxo | Claude, em autonomia |
| [0002](0002-seguranca-e-soberania.md) | Segurança e soberania como requisitos de projeto | Cliente e Claude |
| [0003](0003-stack-tecnologica.md) | Stack: Python/FastAPI, React/TypeScript, PostgreSQL, Docker | Cliente e Claude |
| [0004](0004-provedor-de-llm-externo-controlado.md) | API gratuita de LLM só com metadados públicos | Cliente e Claude |
| [0005](0005-armazenamento-em-camadas.md) | PostgreSQL em camadas (raw, catalogo, curadoria, analitico) | Cliente e Claude |
| [0006](0006-controle-de-extracoes.md) | Controle de pedidos de extração (custo e carga no portal) | Cliente e Claude |
| [0007](0007-fila-de-jobs.md) | Fila de jobs sobre as tabelas de execução | Claude, em autonomia |
| [0008](0008-busca-e-modelo-de-leitura.md) | Busca no PostgreSQL com tabela de leitura materializada | Claude, em autonomia |
| [0009](0009-modelo-de-qualidade.md) | Nota de qualidade: regras binárias ponderadas por dimensão | Claude, em autonomia |
| [0010](0010-modelo-de-curadoria.md) | Curadoria como registro de alterações por campo | Claude, em autonomia |
| [0011](0011-integracao-com-llm.md) | LLM: protocolo compatível com OpenAI e modo simulado | Claude, em autonomia |
| [0012](0012-bibliotecas-do-frontend.md) | Frontend com React Router e componentes próprios | Claude, em autonomia |
| [0013](0013-estrategia-de-testes-e2e.md) | E2E com portal falso executável | Claude, em autonomia |
| [0014](0014-roteador-de-provedores-llm.md) | Roteador próprio de provedores gratuitos de LLM, com troca por cota | Cliente e Claude |

As decisões de 0007 a 0013 foram tomadas enquanto o cliente estava ausente, por delegação dele. Revisados e confirmados pelo cliente em 2026-11-21.
