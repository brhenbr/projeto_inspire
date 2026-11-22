# Backlog

Gerado por `kit/scripts/backlog_to_jira.py` a partir de `backlog.json`. Não edite este arquivo à mão.

## EP-01 — Extração do catálogo

*Highest · mvp, extracao*

Espelhar os metadados do catálogo do dados.gov.br (só públicos; recursos apenas com link), de forma manual, retomável e incremental. Plano de trabalho: A4.

- **US-001** (Story, Highest, mvp, extracao) — Coletar dimensões (organizações, temas, tags, formatos, ODS, observância legal) ✔ Concluído (tags vêm dos conjuntos)
- **US-002** (Story, Highest, mvp, extracao, tecnico) — Cliente HTTP resiliente para a API do portal ✔ Concluído
- **US-003** (Story, Highest, mvp, extracao) — Coletar listagem de conjuntos (fase 1) ✔ Concluído
- **US-004** (Story, Highest, mvp, extracao) — Coletar detalhe de cada conjunto e recursos (fase 2) ✔ Concluído
- **US-016** (Story, High, mvp, extracao) — Extração incremental pela data de alteração ✔ Concluído
- **US-005** (Story, High, mvp, extracao) — Guardar snapshot bruto e hash por conjunto ✔ Concluído
- **US-006** (Story, High, mvp, extracao, web) — Botão de extração na interface, com estado e controle ✔ Concluído
- **US-007** (Story, Medium, mvp, extracao, tecnico) — Disparar extração por linha de comando ✔ Concluído
- **US-017** (Story, Medium, fase-2, extracao) — Agendamento automático de extrações
- **US-015** (Story, Highest, mvp, extracao, tecnico) — Controle de pedidos de extração no backend (ADR-0006) ✔ Concluído
- **US-008** (Story, Highest, mvp, extracao, tecnico) — Normalizador raw para catálogo, reexecutável ✔ Concluído
- **US-009** (Story, Highest, mvp, extracao, seguranca) — Remover dados pessoais na ingestão ✔ Concluído

## EP-02 — Discovery do catálogo

*Highest · mvp, discovery*

Explorar o catálogo espelhado com busca e filtros.

- **US-010** (Story, Highest, mvp, discovery) — Busca textual nos conjuntos ✔ Concluído
- **US-011** (Story, High, mvp, discovery) — Filtros combináveis ✔ Concluído
- **US-012** (Story, High, mvp, discovery) — Página de detalhe do conjunto ✔ Concluído
- **US-013** (Story, Medium, mvp, discovery) — Visão por organização ✔ Concluído
- **US-014** (Story, Medium, mvp, discovery) — Painel geral do catálogo ✔ Concluído

## EP-03 — Qualidade dos metadados

*Highest · mvp, qualidade*

Avaliar metadados por regras explicáveis. Pesos e critérios definidos com o time; alinhar com DCAT-BR/DQV quando o padrão for definido.

- **US-020** (Story, Highest, mvp, qualidade) — Motor de regras de qualidade configurável ✔ Concluído
- **US-023** (Task, Highest, mvp, qualidade, padroes) — Matriz de qualidade: DQV x FAIR x DMBOK ✔ Concluído (especificação oficial do DCAT-BR lida em 2026-11-21)
- **US-021** (Story, High, mvp, qualidade) — Pontuação por conjunto e agregada por organização/tema ✔ Concluído (organização; por tema: só contagem no painel)
- **US-022** (Story, High, mvp, qualidade, curadoria) — Lista priorizada de conjuntos a curar ✔ Concluído

## EP-04 — Curadoria humana

*Highest · mvp, curadoria*

Camada curada separada do espelho do portal, com histórico. Plano de trabalho: A6.

- **US-030** (Story, Highest, mvp, curadoria, tecnico) — Modelo de dados com espelho e camada curada separados ✔ Concluído
- **US-031** (Story, High, mvp, curadoria, web) — Editar metadados curados ✔ Concluído
- **US-032** (Story, High, mvp, curadoria) — Status de curadoria ✔ Concluído
- **US-033** (Story, High, mvp, curadoria, web) — Criar e gerenciar coleções pela interface ✔ Concluído
- **US-036** (Story, High, mvp, curadoria, web) — Coleções dinâmicas a partir de filtros salvos ✔ Concluído
- **US-037** (Task, Medium, mvp, curadoria) — Criar a coleção inicial de bases sociais ✔ Em andamento (o sistema propõe a lista; também será caso de teste para os testadores)
- **US-034** (Story, Medium, mvp, curadoria) — Histórico e auditoria de alterações ✔ Concluído
- **US-035** (Story, Low, fase-2, curadoria) — Detecção de possíveis duplicados

## EP-05 — Curadoria assistida por LLM

*High · mvp, llm*

Humano parametriza, LLM executa, humano aprova. Provedor gratuito/local por trás de uma interface desacoplada. Plano de trabalho: A6.

- **US-040** (Story, High, mvp, llm, tecnico) — Interface de provedor de LLM desacoplada ✔ Concluído
- **US-041** (Story, High, mvp, llm, curadoria) — Tarefas de curadoria parametrizáveis ✔ Concluído
- **US-042** (Story, High, mvp, llm, curadoria) — Execução em lote com fila de revisão ✔ Concluído
- **US-043** (Story, High, mvp, llm, governanca) — Registro de execução e proveniência ✔ Concluído
- **US-044** (Spike, High, mvp, llm, spike) — Avaliar modelos gratuitos/locais para português
- **US-045** (Story, Medium, mvp, llm, curadoria) — Marcar propostas desatualizadas quando o conjunto mudar no portal ✔ Concluído
- **US-067** (Spike, High, mvp, llm, seguranca, spike) — Selecionar provedores gratuitos de LLM e validar condições de uso ✔ Parcial (4 provedores gratuitos validados com chaves reais em 2026-11-21; termos de uso a conferir)
- **US-068** (Task, High, mvp, llm, seguranca) — Salvaguardas do LLM externo (ADR-0004) ✔ Concluído
- **US-069** (Task, Low, futuro, llm, tecnico) — Perfil Docker 'llm-local' para rodar LLM em GPU (preparado, desativado)
- **US-150** (Story, High, mvp, llm, seguranca) — Roteador de provedores gratuitos de LLM com troca automática por cota ✔ Concluído

## EP-06 — API própria e exportação

*High · mvp, api*

API REST documentada (OpenAPI), versionada, usada pela interface web e preparada para outros consumidores e para ferramentas de LLM. Plano de trabalho: A7.

- **US-050** (Story, High, mvp, api) — API REST v1 documentada em OpenAPI ✔ Concluído
- **US-051** (Story, Medium, mvp, api) — Exportar base curada em CSV e JSON ✔ Concluído

## EP-07 — Fundação técnica e qualidade de software

*Highest · mvp, tecnico*

Execução em Docker, testes, CI e documentação contínua.

- **US-060** (Task, Highest, mvp, tecnico, adr) — Conversa e ADR de tecnologias (stack, banco, busca, fila, front) ✔ Concluído (ADR-0003)
- **US-061** (Task, Highest, mvp, tecnico) — Esqueleto do projeto com Docker Compose ✔ Concluído
- **US-062** (Task, High, mvp, tecnico) — Portão local de qualidade e, depois do primeiro push, CI ✔ Parcial (portão local pronto; CI depois do primeiro push)
- **US-063** (Task, High, mvp, tecnico, teste) — Testes E2E dos fluxos principais ✔ Concluído
- **US-064** (Task, Medium, mvp, tecnico, governanca) — Definir licença e preparar repositório para publicação
- **US-066** (Task, High, mvp, tecnico, seguranca) — Checklist de segurança e soberania (ADR-0002) ✔ Parcial (barreiras implementadas e testadas; falta varredura de dependências no CI)
- **US-065** (Task, Medium, mvp, tecnico, doc) — Documentação de implementação, testes e deploy ✔ Concluído
- **US-072** (Task, Low, mvp, doc) — Versão da arquitetura em linguagem acessível e revisão do C4 com o cliente
- **US-160** (Story, High, mvp, teste, kit) — Ferramenta independente de roteiro de testes (SQLite, sem dependências) ✔ Concluído
- **US-161** (Story, High, mvp, teste, doc) — Manual do usuário como roteiro de testes com dados reais
- **US-162** (Task, High, mvp, teste, deploy) — Pacote de teste com a base já carregada (Docker)
- **US-163** (Task, Medium, teste, doc, arquitetura) — Página 'como o sistema funciona' para os testadores

## EP-08 — Verificação de links dos recursos (link rot)

*Medium · fase-2, links*

Worker separado que verifica disponibilidade dos recursos sem baixar dados.

- **US-070** (Story, Medium, fase-2, links) — Worker de verificação HEAD/GET parcial
- **US-071** (Story, Medium, fase-2, links, qualidade) — Integrar disponibilidade à pontuação de qualidade

## EP-09 — Exploração em linguagem natural

*Medium · fase-2, llm, nl*

Perguntas em português sobre o catálogo curado, respondidas por um LLM que usa a API própria como ferramenta.

- **US-080** (Story, Medium, fase-2, nl) — Busca semântica com embeddings ✔ Fora do MVP (decisão do cliente em 2026-11-22)
- **US-081** (Story, Medium, fase-2, nl) — Chat sobre o catálogo ✔ Parcial (versão tradutor de filtros, ADR-0016: o LLM não vê os dados; sem respostas redigidas)
- **US-151** (Story, High, mvp, nl, colecoes) — Criar coleção dinâmica descrevendo-a em texto ✔ Concluído
- **US-152** (Story, High, mvp, nl) — Perguntar ao catálogo em linguagem natural ✔ Concluído

## EP-10 — Governança de IA e conformidade

*Medium · backlog, governanca*

Requisitos do GuIA/MGI que podem ser exigidos quando o produto for para órgãos públicos.

- **US-090** (Story, Medium, backlog, governanca) — Autoavaliação de Impacto Ético (AIE)
- **US-091** (Story, Low, backlog, governanca) — Relatório de transparência do uso de IA

## EP-11 — Padrões de metadados (DCAT-BR e DQV)

*Medium · fase-2, padroes*

Exportar e mapear o catálogo conforme DCAT-BR v1.0 e a qualidade conforme DQV (padrões já definidos pelo projeto). O modelo de dados já nasce alinhado; esta fase entrega a exportação e a validação.

- **US-100** (Story, Medium, fase-2, padroes) — Mapear o modelo curado para DCAT-BR ✔ Concluído (docs/02-arquitetura/mapeamento-dcat-br.md)
- **US-101** (Story, Medium, fase-2, padroes) — Exportar catálogo em DCAT (JSON-LD) e qualidade em DQV ✔ Concluído (ADR-0015; JSON-LD, antecipada para o MVP)

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
