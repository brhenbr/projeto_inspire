# Backlog

Gerado por `kit/scripts/backlog_to_jira.py` a partir de `backlog.json`. Não edite este arquivo à mão.

## EP-01 — Extração do catálogo

*Highest · mvp, extracao*

Espelhar os metadados do catálogo do dados.gov.br (só públicos; recursos apenas com link), de forma manual, retomável e incremental. Plano de trabalho: A4.

- **US-001** (Story, Highest, mvp, extracao) — Coletar dimensões (organizações, temas, tags, formatos, ODS, observância legal)
- **US-002** (Story, Highest, mvp, extracao, tecnico) — Cliente HTTP resiliente para a API do portal
- **US-003** (Story, Highest, mvp, extracao) — Coletar listagem de conjuntos (fase 1)
- **US-004** (Story, Highest, mvp, extracao) — Coletar detalhe de cada conjunto e recursos (fase 2)
- **US-005** (Story, High, mvp, extracao) — Guardar snapshot bruto e hash por conjunto
- **US-006** (Story, High, mvp, extracao, web) — Disparar e acompanhar extração pela interface web
- **US-007** (Story, Medium, mvp, extracao, tecnico) — Disparar extração por linha de comando

## EP-02 — Discovery do catálogo

*Highest · mvp, discovery*

Explorar o catálogo espelhado com busca e filtros.

- **US-010** (Story, Highest, mvp, discovery) — Busca textual nos conjuntos
- **US-011** (Story, High, mvp, discovery) — Filtros combináveis
- **US-012** (Story, High, mvp, discovery) — Página de detalhe do conjunto
- **US-013** (Story, Medium, mvp, discovery) — Visão por organização
- **US-014** (Story, Medium, mvp, discovery) — Painel geral do catálogo

## EP-03 — Qualidade dos metadados

*Highest · mvp, qualidade*

Avaliar metadados por regras explicáveis. Pesos e critérios definidos com o time; alinhar com DCAT-BR/DQV quando o padrão for definido.

- **US-020** (Story, Highest, mvp, qualidade) — Motor de regras de qualidade configurável
- **US-021** (Story, High, mvp, qualidade) — Pontuação por conjunto e agregada por organização/tema
- **US-022** (Story, High, mvp, qualidade, curadoria) — Lista priorizada de conjuntos a curar

## EP-04 — Curadoria humana

*Highest · mvp, curadoria*

Camada curada separada do espelho do portal, com histórico. Plano de trabalho: A6.

- **US-030** (Story, Highest, mvp, curadoria, tecnico) — Modelo de dados com espelho e camada curada separados
- **US-031** (Story, High, mvp, curadoria, web) — Editar metadados curados
- **US-032** (Story, High, mvp, curadoria) — Status de curadoria
- **US-033** (Story, High, mvp, curadoria, web) — Criar e gerenciar coleções pela interface
- **US-036** (Story, High, mvp, curadoria, web) — Coleções dinâmicas a partir de filtros salvos
- **US-037** (Task, Medium, mvp, curadoria) — Criar a coleção inicial de bases sociais
- **US-034** (Story, Medium, mvp, curadoria) — Histórico e auditoria de alterações
- **US-035** (Story, Low, fase-2, curadoria) — Detecção de possíveis duplicados

## EP-05 — Curadoria assistida por LLM

*High · mvp, llm*

Humano parametriza, LLM executa, humano aprova. Provedor gratuito/local por trás de uma interface desacoplada. Plano de trabalho: A6.

- **US-040** (Story, High, mvp, llm, tecnico) — Interface de provedor de LLM desacoplada
- **US-041** (Story, High, mvp, llm, curadoria) — Tarefas de curadoria parametrizáveis
- **US-042** (Story, High, mvp, llm, curadoria) — Execução em lote com fila de revisão
- **US-043** (Story, High, mvp, llm, governanca) — Registro de execução e proveniência
- **US-044** (Spike, High, mvp, llm, spike) — Avaliar modelos gratuitos/locais para português
- **US-067** (Spike, High, mvp, llm, seguranca, spike) — Selecionar provedores gratuitos de LLM e validar condições de uso
- **US-068** (Task, High, mvp, llm, seguranca) — Salvaguardas do LLM externo (ADR-0004)

## EP-06 — API própria e exportação

*High · mvp, api*

API REST documentada (OpenAPI), versionada, usada pela interface web e preparada para outros consumidores e para ferramentas de LLM. Plano de trabalho: A7.

- **US-050** (Story, High, mvp, api) — API REST v1 documentada em OpenAPI
- **US-051** (Story, Medium, mvp, api) — Exportar base curada em CSV e JSON

## EP-07 — Fundação técnica e qualidade de software

*Highest · mvp, tecnico*

Execução em Docker, testes, CI e documentação contínua.

- **US-060** (Task, Highest, mvp, tecnico, adr) — Conversa e ADR de tecnologias (stack, banco, busca, fila, front)
- **US-061** (Task, Highest, mvp, tecnico) — Esqueleto do projeto com Docker Compose
- **US-062** (Task, High, mvp, tecnico) — Portão local de qualidade e, depois do primeiro push, CI
- **US-063** (Task, High, mvp, tecnico, teste) — Testes E2E dos fluxos principais
- **US-064** (Task, Medium, mvp, tecnico, governanca) — Definir licença e preparar repositório para publicação
- **US-066** (Task, High, mvp, tecnico, seguranca) — Checklist de segurança e soberania (ADR-0002)
- **US-065** (Task, Medium, mvp, tecnico, doc) — Documentação de implementação, testes e deploy

## EP-08 — Verificação de links dos recursos (link rot)

*Medium · fase-2, links*

Worker separado que verifica disponibilidade dos recursos sem baixar dados.

- **US-070** (Story, Medium, fase-2, links) — Worker de verificação HEAD/GET parcial
- **US-071** (Story, Medium, fase-2, links, qualidade) — Integrar disponibilidade à pontuação de qualidade

## EP-09 — Exploração em linguagem natural

*Medium · fase-2, llm, nl*

Perguntas em português sobre o catálogo curado, respondidas por um LLM que usa a API própria como ferramenta.

- **US-080** (Story, Medium, fase-2, nl) — Busca semântica com embeddings
- **US-081** (Story, Medium, fase-2, nl) — Chat sobre o catálogo

## EP-10 — Governança de IA e conformidade

*Medium · backlog, governanca*

Requisitos do GuIA/MGI que podem ser exigidos quando o produto for para órgãos públicos.

- **US-090** (Story, Medium, backlog, governanca) — Autoavaliação de Impacto Ético (AIE)
- **US-091** (Story, Low, backlog, governanca) — Relatório de transparência do uso de IA

## EP-11 — Padrões de metadados (DCAT-BR e DQV)

*Medium · fase-2, padroes*

Alinhar o modelo curado e a qualidade aos padrões a definir com o CPQD (A5). Hipótese de trabalho: DCAT-BR e DQV.

- **US-100** (Story, Medium, fase-2, padroes) — Mapear o modelo curado para DCAT-BR
- **US-101** (Story, Medium, fase-2, padroes) — Exportar catálogo em DCAT (JSON-LD) e qualidade em DQV

## EP-12 — Evolução automática de taxonomias

*Low · futuro, taxonomia*

Descobrir temas emergentes com embeddings, clustering e LLM. Plano de trabalho: A9.

- **US-110** (Story, Low, futuro, taxonomia) — Clusterizar conjuntos e sugerir novos temas

## EP-13 — Reusos e solicitações de dados

*Low · futuro, reusos*

Usar reusos e pedidos de abertura para priorizar a curadoria e achar lacunas.

- **US-120** (Story, Low, futuro, reusos) — Coletar reusos e solicitações

## EP-14 — Devolução de propostas ao portal

*Low · futuro, portal*

Propor alterações ao dados.gov.br a partir da curadoria. Exige perfil de administrador de organização; não está no curto nem no médio prazo.

- **US-130** (Story, Low, futuro, portal) — Gerar pacote de propostas por organização

## EP-15 — Multiusuário, acesso e escala

*Low · futuro, acesso*

Login, papéis (curador, coordenação, explorador), publicação em nuvem.

- **US-140** (Story, Low, futuro, acesso) — Autenticação e papéis
- **US-141** (Story, Low, futuro, acesso, tecnico) — Implantação em nuvem
