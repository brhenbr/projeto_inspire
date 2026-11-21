# Proposta de tecnologias (para decisão do cliente)

- **Status:** parcialmente aceita em [ADR-0003](../03-decisoes/0003-stack-tecnologica.md). Pendente: provedor de LLM (ADR-0004).
- **Tarefa de backlog:** US-060.

## 1. Critérios (vindos do cliente e do ADR-0002)
Open source e custo mínimo · Docker · simplicidade para um MVP rápido · API primeiro, desacoplada ·
segurança e soberania · um time pequeno e acadêmico precisa conseguir manter · espaço para IA
(busca semântica, LLM) sem trocar de plataforma.

## 2. Restrições do ambiente (medidas em 2026-11-21)
- Máquina de desenvolvimento: i7 de 4ª geração (4 threads), 16 GB de RAM, GPU antiga (GT 820M, 2 GB)
  **sem uso prático para LLM**. Docker instalado, mas o Docker Desktop precisa estar aberto.
- Consequência: nesta máquina só rodam LLMs pequenos, em CPU e devagar. Servem para testar o encaixe,
  **não para avaliar qualidade**. Qualidade real exige um servidor com GPU sob controle do projeto
  (a premissa 7 do plano prevê GPUs do CPQD). Ver US-067.
- Tamanho dos dados: ~20,7 mil conjuntos; poucos GB no total. Não é um problema de grande escala.

## 3. Estilo de arquitetura
**Monolito modular com portas e adaptadores**, entregue como poucos containers.

- Módulos com fronteiras claras: `extracao`, `catalogo`, `qualidade`, `curadoria`, `llm`. Cada módulo
  fala com os outros por interfaces, não por tabelas alheias.
- Adaptadores nas bordas: cliente do portal, provedor de LLM, armazenamento. Trocar o provedor de LLM
  ou, no futuro, escrever no portal é trocar um adaptador.
- Por que não microsserviços: custo operacional alto sem benefício na escala de um MVP. A fronteira
  modular permite separar depois.

## 4. Stack recomendada

| Camada | Recomendação | Alternativas consideradas | Por que |
|---|---|---|---|
| Backend / API | **Python 3.12 + FastAPI** | TypeScript (NestJS), Java/Spring, .NET | OpenAPI nativo (exigência do plano), melhor ecossistema de IA, e é a linguagem que pesquisadores da área costumam dominar. |
| Banco de dados | **PostgreSQL 16**, em camadas (ver [ADR-0005](../03-decisoes/0005-armazenamento-em-camadas.md)) | MongoDB, SQLite, DuckDB | Relacional, maduro, livre. Já cobre **busca textual em português** (full-text com `unaccent` e `pg_trgm`) e, com `pgvector`, **busca semântica** depois. Um só banco. |
| Busca | **Dentro do PostgreSQL** | OpenSearch/Elasticsearch, Meilisearch | 20 mil documentos não justificam outro serviço. Reavaliamos se a busca ficar lenta. |
| Fila/jobs | **Fila em PostgreSQL** (ex.: Procrastinate) com processo worker | Celery + Redis, RQ | Sem Redis nem broker extra. Extração e LLM rodam em worker separado da API, com retomada. |
| Migrações/ORM | SQLAlchemy 2 + Alembic | Django ORM | Padrão do ecossistema FastAPI. |
| Frontend | **React + TypeScript + Vite**, biblioteca de componentes livre (ex.: Mantine) | HTMX com páginas no servidor; Vue | SPA consome só a API própria (desacoplamento real). Interface "básica, mas boa". HTMX seria mais rápido de fazer, mas acopla a tela ao backend. |
| LLM | **Interface compatível com a API da OpenAI**, execução local com **Ollama** ou vLLM no servidor | Chamar API de nuvem direto | Protocolo aberto e aceito por quase todos os servidores locais; no futuro aceita modelos do CPQD sem mudar código. Nuvem externa proibida por padrão (ADR-0002). |
| Embeddings | Modelo multilíngue pequeno, local (candidato: família e5 ou bge, definido no spike) | API de nuvem | Roda em CPU; mantém soberania. |
| Testes | pytest (unidade e integração, API simulada), Playwright (E2E), Vitest | — | Cobre o pedido de "testes profissionais, proporcionais a um MVP". |
| Qualidade de código | ruff, mypy, ESLint, pre-commit | — | Barato e evita erro bobo. |
| CI | **GitHub Actions**, com varredura de dependências e de segredos | GitLab CI | O repositório irá ao GitHub do cliente. Ver nota de soberania abaixo. |
| Empacotamento | Docker Compose: `web`, `api`, `worker`, `db` e opcional `llm` | Kubernetes | Compose agora; as imagens servem para Kubernetes depois. |
| Observabilidade | Logs JSON (structlog) e histórico de execuções no banco | Prometheus/Grafana | Suficiente para o MVP. |

**Nota de soberania sobre o CI:** o GitHub é um serviço externo. O CI roda só código e dados públicos
de teste, nunca segredos reais nem a base curada. Para operação em órgãos públicos, o mesmo pipeline
pode migrar para GitLab ou Gitea sob controle deles.

**Licenças:** todas as peças recomendadas são livres (PostgreSQL, FastAPI, React, Ollama, pgvector).
Ainda vou confirmar a licença de cada modelo de LLM e de embeddings no spike antes de adotar.

## 5. C2 (contêineres)
Ver [c2-conteineres.md](c2-conteineres.md), que reflete as decisões aceitas.

Pontos de desenho que valem destacar:
- **Snapshot só quando muda:** o JSON bruto de um conjunto é guardado apenas se o hash mudou. Mantém o
  histórico sem multiplicar o armazenamento por execução.
- **Espelho × curadoria:** tabelas separadas; a curadoria guarda as diferenças, com autoria e origem
  (humano ou modelo).
- **Ponto único de entrada:** só o `web` fica exposto; `api`, `worker`, `db` e LLM ficam em rede interna.

## 6. Estratégia para o LLM
1. **MVP de plumbing:** modelo pequeno em CPU, só para validar o fluxo (tarefa, lote, aprovação, registro).
2. **Avaliação de qualidade (spike US-044/067):** comparar 2 a 3 modelos abertos em uma amostra
   rotulada, em um servidor com GPU sob controle do projeto.
3. **Contrato estável:** o domínio só conhece a interface; o modelo e o servidor mudam por configuração.
4. **Sem GPU disponível, o produto continua útil:** discovery, qualidade por regras e curadoria humana
   não dependem de LLM.

## 7. Riscos da proposta
| Risco | Mitigação |
|---|---|
| Qualidade dos LLMs pequenos em português técnico | Humano sempre aprova; spike com amostra; modelos maiores via servidor com GPU. |
| Python como linguagem única do time pode não ser a preferida | Decidir agora; trocar depois custa caro. |
| React exige mais disciplina que páginas simples | Interface enxuta, biblioteca de componentes pronta, poucos fluxos. |
| Busca no PostgreSQL pode não bastar para relevância fina | Medir no MVP; Meilisearch ou OpenSearch entram por adaptador se necessário. |

## 8. Decisões que preciso do cliente
1. Linguagem do backend (Python é a recomendação).
2. Frontend: SPA em React ou páginas simples com HTMX.
3. Onde o LLM pode rodar com qualidade: existe um servidor com GPU acessível (UFSCar, CPQD)?
4. Aceita o GitHub Actions para CI, com a ressalva de soberania acima?
5. Aprova a proposta como um todo, com ajustes?
