# Visão e escopo do MVP — Inspire Catálogo

- **Versão:** 0.2 (proposta para aprovação do cliente)
- **Data:** 2026-11-21
- **Status:** aguardando revisão. Itens marcados com **[?]** dependem de resposta do cliente.
- **Mudanças desde a 0.1:** respostas do cliente incorporadas; alinhamento ao Plano de Trabalho
  UFSCar/CPQD; verificação de links e AIE movidas para o backlog; backlog completo criado.

## 1. Contexto

O Projeto INSPIRE (ver [dossiê](../00-descoberta/Projeto_INSPIRE_Dossie_Detalhado.pdf)) usa IA para
melhorar serviços e dados do governo federal. Este trabalho se encaixa principalmente na **Camada 3
(plataformas e modelos de IA, incluindo LLMs em português)** e na **Camada 4 (aplicações inteligentes)**.

A frente da UFSCar, sob acordo com o CPQD, tem como objetivo central uma **API de catalogação de
metadados com uso intensivo de IA**. Este produto é o veículo prático para parte dessa frente:

| Atividade do plano | O que este produto entrega |
|---|---|
| A1 Mapeamento das bases | Espelho completo do catálogo público, com coleções (ex.: bases sociais de saúde, assistência e educação) |
| A4 Coleta de metadados | Extração resiliente, incremental e retomável (conector do dados.gov.br) |
| A6 Organização e gestão | Busca, curadoria (inserir, alterar, remover) e IA generativa para apoiar a curadoria |
| A7 API de catalogação | API REST própria, versionada e documentada em OpenAPI |
| A5 Padrão de metadados | **Fase 2:** mapeamento para DCAT-BR e DQV, quando o padrão for definido com o CPQD |
| A9 Evolução de taxonomias | **Futuro:** a busca semântica da fase 2 é a base |
| A10 Ontologias a partir de dados brutos | **Fora:** exige analisar o conteúdo dos arquivos |

O Portal Brasileiro de Dados Abertos (dados.gov.br) é um catálogo **federado**: guarda os metadados e
aponta para os arquivos, que ficam nos órgãos. Medimos em 2026-11-21 **cerca de 20.700 conjuntos de
dados em 311 organizações** (soma dos totais por organização; os maiores são BCB, IPEA e INPI).

## 2. Problema

1. **Descoberta ruim:** é difícil saber o que existe, quem publica, com que qualidade e cobertura.
2. **Metadados inconsistentes:** descrições curtas, tags duplicadas ou vagas, licença e periodicidade
   ausentes, temas mal atribuídos.
3. **Curadoria manual não escala** com 20 mil conjuntos e dezenas de critérios.
4. **Sem memória:** o portal mostra só o estado atual; não há histórico do que mudou nem trilha do
   que a curadoria propôs e decidiu.

## 3. Visão do produto

Uma aplicação web que **espelha o catálogo, deixa explorá-lo, mede a qualidade dos metadados e
organiza a curadoria**, em que **humanos definem os critérios e LLMs fazem o trabalho repetitivo,
sempre com revisão humana**. Em longo prazo é a base de um marketplace de dados abertos.

### Princípios
- **Humano no comando:** o LLM propõe, a pessoa aprova (supervisão humana e auditabilidade, como pede o GuIA do MGI).
- **Espelho separado da camada curada:** o que veio do portal nunca é sobrescrito. Isso prepara a futura devolução de propostas ao portal.
- **Rastreabilidade:** toda sugestão de LLM registra modelo, versão, parâmetros e quem aprovou.
- **Preparado, não construído:** o que está fora do escopo vira ponto de extensão, não código.
- **Custo mínimo:** open source e modelos gratuitos ou locais sempre que possível.
- **Pronto para ser público:** código, testes e documentação em padrão de repositório aberto, como o plano de trabalho prevê para a API.

## 4. Usuários e avaliadores

O MVP é monousuário, mas o desenho considera os papéis abaixo.

| Papel | O que faz | Necessidade principal |
|---|---|---|
| **Curador(a)** | Revisa e melhora metadados | Fila priorizada, edição rápida, ajuda do LLM |
| **Coordenação do projeto** | Acompanha a evolução | Indicadores de qualidade por órgão, tema e período |
| **Explorador(a) de dados** | Busca dados para análise ou produto | Busca boa, filtros, entender o dataset sem sair do app |

**Quem avalia o protótipo agora:** professores da UFSCar. Depois, órgãos públicos (MGI, CPQD e
outros). Por isso a demonstração deve mostrar o fluxo completo e o rigor de engenharia, e a
documentação precisa se sustentar sozinha, sem depender de explicação oral.

## 5. Escopo

Detalhamento em [backlog/backlog.md](backlog/backlog.md) (62 itens, 15 épicos), com versão para importar no Jira.

### MVP — Deve ter
| Épico | Entrega |
|---|---|
| EP-01 **Extração do catálogo** | Botão/comando que espelha organizações, temas, tags, formatos, conjuntos e recursos. Só metadados e só públicos; recursos apenas com link. Retomável, com relatório coletado × esperado. Snapshot bruto e histórico de mudanças (novo, alterado, removido). |
| EP-02 **Discovery** | Busca textual, filtros combináveis, detalhe do conjunto, visão por organização e painel geral. |
| EP-03 **Qualidade dos metadados** | Regras determinísticas e configuráveis com pontuação explicável por conjunto e por órgão, e lista priorizada de curadoria. |
| EP-04 **Curadoria humana** | Camada curada separada do espelho: editar, status, coleções e histórico de alterações. |
| EP-07 **Fundação técnica** | Docker Compose, CI, testes (unitários, integração, E2E) e documentação contínua. |

### MVP — Deveria ter
| Épico | Entrega |
|---|---|
| EP-05 **Curadoria assistida por LLM** | Humano escolhe tarefa e parâmetros; LLM propõe em lote; humano aprova. Provedor gratuito/local atrás de uma interface desacoplada, com registro de proveniência. Inclui um spike para avaliar modelos em português. |
| EP-06 **API própria e exportação** | API REST v1 em OpenAPI, usada pela interface web, e exportação em CSV/JSON. |

### Fase 2
| Épico | Observação |
|---|---|
| EP-08 Verificação de links | Worker separado; requisita os servidores dos órgãos, sem baixar dados. |
| EP-09 Exploração em linguagem natural | Busca semântica e chat sobre o catálogo curado. A API do MVP é desenhada para servir de ferramenta ao LLM. |
| EP-11 Padrões DCAT-BR e DQV | Mapeamento e exportação, após definição do padrão com o CPQD. |

### Backlog (futuro)
EP-10 Governança de IA (Autoavaliação de Impacto Ético, relatório de transparência), EP-12 Evolução
de taxonomias (A9), EP-13 Reusos e solicitações, EP-14 Devolução de propostas ao portal, EP-15
Multiusuário e nuvem.

### Fora do escopo
- Escrita no portal, datasets privados, download ou análise do conteúdo dos arquivos (inclui A10).
- Marketplace e integração com Data Space (apenas extensibilidade do modelo).

## 6. Critérios de sucesso do MVP (proposta)

1. Extração completa, com relatório de conferência (coletado × esperado por organização).
2. Reextração incremental que identifica corretamente novos, alterados e removidos.
3. Busca e filtros em até 1 segundo sobre o catálogo completo (meta a validar).
4. Pontuação de qualidade para 100% dos conjuntos coletados, explicável regra a regra.
5. Fluxo ponta a ponta demonstrável: selecionar conjuntos → LLM propõe → humano aprova → exporta.
6. Sobe com um único comando em Docker; suíte de testes verde no CI, com cobertura em torno de 80% na API (referência do plano, A7).

## 7. Requisitos não funcionais

- **Execução:** Docker (Compose) local, portável para nuvem depois.
- **Respeito ao portal:** concorrência baixa, retry com backoff e jitter, User-Agent identificado, timeouts explícitos.
- **Segredos:** chave só em `.env`; nunca em logs, banco ou git. Documentos institucionais restritos ficam fora do git.
- **Qualidade:** testes unitários, de integração (com API simulada) e E2E dos fluxos principais.
- **Observabilidade básica:** logs estruturados e histórico de execuções de extração.
- **Idioma:** interface e documentação em português; código em inglês.
- **Licença:** definir antes de publicar (o plano pede licença compatível com uso governamental).

## 8. Riscos e achados da descoberta

| Risco/achado | Impacto | Resposta proposta |
|---|---|---|
| **A API responde vazio de forma intermitente.** A mesma consulta (`pagina=1`) devolveu 0 e depois 15 itens; ao somar 21 páginas de organizações, quase todas precisaram de retry. | Uma página vazia **não** indica fim do catálogo; um extrator ingênuo perderia dados em silêncio. | Retry em respostas vazias, conferência contra totais por organização, relatório de divergências. |
| **A API exige chave** em todas as rotas, ao contrário da especificação do cliente. | Dependência de credencial; risco de bloqueio por abuso. | Chave em `.env`, taxa limitada, documentado no ADR de extração. |
| **A listagem traz só resumo** e o detalhe exige 1 chamada por conjunto (~20,7 mil chamadas). | Primeira extração é demorada. | Duas fases, retomável e paralelizada com limite; medir o tempo real. |
| **A listagem não informa o total.** | Difícil saber quando terminou. | Usar a soma por organização como total esperado. |
| **LLM gratuito pode ter qualidade baixa em português técnico.** | Propostas fracas. | Interface de provedor desacoplada; spike de avaliação; humano sempre revisa. |
| **Padrões de metadados ainda não definidos** (DCAT-BR, DQV, FAIR serão definidos com o CPQD). | Retrabalho nas regras de qualidade. | Regras configuráveis; mapeamento DCAT-BR/DQV na fase 2. |
| **Repositório pode ficar público.** | Vazamento de segredos ou documentos contratuais. | `.env` e `docs/00-descoberta/restrito/` fora do git; checagem antes de publicar (US-064). |

## 9. Perguntas abertas para o cliente

1. **Padrões de metadados:** o kickoff com o CPQD já definiu os padrões (DCAT-BR, DQV, FAIR)? Se não,
   uso DCAT-BR e DQV como hipótese e deixo as regras de qualidade configuráveis.
2. **Cronograma:** em que mês do plano vocês estão e quando é a demonstração para os professores? As
   atividades A4, A6 e A7 se estendem do mês 4 ao 15, então a data muda quanto escopo cabe.
3. **Repositório público:** o repo no seu GitHub será público? Sugiro a licença Apache-2.0, por conter
   concessão de patentes; confirme se a UFSCar ou o CPQD impõem alguma licença.
4. **Coleção "bases sociais":** o plano foca bases sociais (saúde, assistência, educação). Quero criar
   uma coleção curada inicial para isso. Quem define a lista, ou deduzo por tema e organização?
5. **Documentos restritos:** coloquei o Plano de Trabalho em `docs/00-descoberta/restrito/`, ignorado
   pelo git, por conter dados contratuais e financeiros. O dossiê do Inspire continua versionado.
   Faz sentido?

## 10. Próximos passos

1. Cliente revisa este documento, o backlog e responde às perguntas.
2. Rodada de arquitetura: C4 (C1–C3 e fluxos) e conversa sobre tecnologias (US-060).
3. ADRs de stack, extração, modelo de dados e provedor de LLM.
4. Início da implementação, começando por EP-07 e EP-01.
