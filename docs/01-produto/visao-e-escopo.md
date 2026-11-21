# Visão e escopo do MVP — Inspire Catálogo

- **Versão:** 0.1 (proposta para aprovação do cliente)
- **Data:** 2026-11-21
- **Status:** aguardando revisão. Itens marcados com **[?]** dependem de resposta do cliente.

## 1. Contexto

O Projeto INSPIRE (ver [dossiê](../00-descoberta/Projeto_INSPIRE_Dossie_Detalhado.pdf)) usa IA para
melhorar serviços e dados do governo federal. Este trabalho se encaixa principalmente na **Camada 3
(plataformas e modelos de IA, incluindo LLMs em português)** e na **Camada 4 (aplicações inteligentes)**.

O Portal Brasileiro de Dados Abertos (dados.gov.br) é um catálogo **federado**: guarda os metadados
e aponta para os arquivos, que ficam nos órgãos publicadores. A qualidade desses metadados limita o
quanto o portal é encontrável, compreensível e reutilizável.

Medimos o catálogo em 2026-11-21: **cerca de 20.700 conjuntos de dados em 311 organizações**
(soma dos totais por organização; os maiores são BCB, IPEA e INPI).

## 2. Problema

1. **Descoberta ruim:** é difícil saber o que existe no catálogo, quem publica, com que qualidade e
   com que cobertura.
2. **Metadados inconsistentes:** descrições curtas, tags duplicadas ou vagas, licença e periodicidade
   ausentes, temas mal atribuídos.
3. **Curadoria manual não escala** com 20 mil conjuntos e dezenas de critérios.
4. **Sem memória:** o portal mostra o estado atual; não há histórico do que mudou nem trilha do que a
   curadoria propôs e decidiu.

## 3. Visão do produto

Uma aplicação web para o time do Inspire que **espelha o catálogo, deixa explorá-lo, mede a qualidade
dos metadados e organiza a curadoria**, em que **humanos definem os critérios e LLMs fazem o trabalho
repetitivo, sempre com revisão humana**. Em longo prazo é a base de um marketplace de dados abertos.

### Princípios
- **Humano no comando (human-in-the-loop):** o LLM propõe, a pessoa aprova. Alinhado ao GuIA do MGI,
  que exige supervisão humana e auditabilidade.
- **Espelho separado da camada curada:** o que veio do portal nunca é sobrescrito pela curadoria. Isso
  também prepara a futura devolução de propostas ao portal.
- **Rastreabilidade:** toda sugestão de LLM registra modelo, versão, parâmetros e quem aprovou.
- **Preparado, não construído:** o que está fora do escopo vira ponto de extensão, não código.
- **Custo mínimo:** open source e modelos gratuitos ou locais sempre que possível.

## 4. Usuários

O MVP é monousuário, mas o desenho considera os papéis abaixo.

| Papel | O que faz | Necessidade principal |
|---|---|---|
| **Curador(a)** | Revisa e melhora metadados | Fila de trabalho priorizada, edição rápida, ajuda do LLM |
| **Coordenação do projeto** | Acompanha a evolução | Indicadores de qualidade por órgão, tema e período |
| **Explorador(a) de dados** | Busca dados para análise ou produto | Busca boa, filtros, entender o dataset sem sair do app |

## 5. Escopo do MVP (priorização MoSCoW)

### Deve ter (Must)
| # | Épico | Entrega |
|---|---|---|
| E1 | **Extração do catálogo** | Botão/comando que espelha organizações, temas, tags, formatos, conjuntos e recursos. Só metadados; recursos apenas com link. Só públicos. Retomável, com progresso visível e relatório (esperado × coletado). Mantém snapshot bruto e histórico de mudanças (novo, alterado, removido). |
| E2 | **Discovery** | Busca textual, filtros (organização, esfera, UF, tema, formato, licença, atualidade), página de detalhe do conjunto, visão por organização. |
| E3 | **Qualidade dos metadados** | Regras determinísticas (completude, formato aberto, atualidade × periodicidade, licença, tags) com pontuação por conjunto e por órgão, explicável regra a regra. |
| E4 | **Curadoria humana** | Camada curada separada: editar título/descrição/tags/tema, marcar status (pendente, em revisão, aprovado, rejeitado, duplicado), agrupar em coleções, ver histórico de alterações. |

### Deveria ter (Should)
| # | Épico | Entrega |
|---|---|---|
| E5 | **Curadoria assistida por LLM** | Humano escolhe conjuntos, tarefa e parâmetros (ex.: melhorar descrição, sugerir tags, avaliar qualidade); LLM gera propostas em lote; humano aprova ou rejeita. Registro completo de execução. No MVP, com um provedor gratuito/local (a escolher em ADR). |
| E6 | **Exportação** | Base curada em CSV e JSON. |

### Poderia ter (Could), preparado mas não necessariamente entregue
| # | Épico | Observação |
|---|---|---|
| E7 | **Exploração em linguagem natural** | A API própria da aplicação será desenhada para servir de ferramenta ao LLM. Entrega só se o custo for baixo. |
| E8 | **Verificação de links (link rot)** | Worker separado com HEAD nas URLs dos recursos. Não baixa dados, mas faz requisições aos órgãos. **[?]** Entra no MVP ou na fase 2? |
| E9 | **Reusos e solicitações de dados** | Endpoints existem no portal; úteis para priorizar curadoria por uso real. |

### Fora do escopo (agora)
- Escrita no portal (propor/aplicar alterações de volta). Previsto para o futuro; o modelo de dados já separa espelho e curadoria.
- Datasets privados, download ou análise do conteúdo dos arquivos.
- Multiusuário, perfis e autenticação (o MVP é monousuário, mas a API não deve impedir isso depois).
- Conectores para portais CKAN setoriais (previsto como ponto de extensão).
- Marketplace.

## 6. Critérios de sucesso do MVP (proposta)

1. Extração completa do catálogo, com relatório de conferência (coletado × esperado por organização).
2. Reextração incremental que identifica corretamente novos, alterados e removidos.
3. Busca e filtros respondem em até 1 segundo sobre o catálogo completo (meta a validar).
4. Pontuação de qualidade disponível para 100% dos conjuntos coletados, explicável por regra.
5. Fluxo ponta a ponta demonstrável: selecionar conjuntos → LLM propõe → humano aprova → exporta.
6. Sobe com um único comando em Docker; roda a suíte de testes automatizados sem falhas.

## 7. Requisitos não funcionais

- **Execução:** Docker (Compose) local, portável para nuvem depois.
- **Respeito ao portal:** concorrência baixa, retry com backoff e jitter, User-Agent identificado,
  timeouts explícitos. A API **exige chave** e responde de forma intermitente (ver riscos).
- **Segredos:** chave só em `.env`; nunca em logs, banco ou git.
- **Qualidade:** testes unitários, de integração (com API simulada) e E2E dos fluxos principais.
- **Observabilidade básica:** logs estruturados e histórico de execuções de extração.
- **Idioma:** interface e documentação em português.

## 8. Riscos e achados da descoberta

| Risco/achado | Impacto | Resposta proposta |
|---|---|---|
| **A API responde vazio de forma intermitente.** A mesma consulta (`pagina=1`) devolveu 0 e depois 15 itens; ao somar 21 páginas de organizações, quase todas precisaram de retry. | Uma página vazia **não** indica fim do catálogo; um extrator ingênuo perderia dados em silêncio. | Retry em respostas vazias, conferência contra totais por organização, relatório de divergências. |
| **A API exige chave** em todas as rotas, ao contrário da especificação do cliente. | Dependência de credencial; risco de bloqueio por abuso. | Chave em `.env`, taxa limitada, documentado no ADR de extração. |
| **A listagem traz só resumo** e o detalhe exige 1 chamada por conjunto (~20,7 mil chamadas). | Primeira extração é demorada. | Extração em duas fases, retomável e paralelizada com limite; medir o tempo real. |
| **A listagem não informa o total.** | Difícil saber quando terminou. | Usar soma por organização como total esperado. |
| **Custo e qualidade de LLM gratuito** para português técnico. | Qualidade das propostas pode ser baixa. | Interface de provedor desacoplada; avaliar modelos no desenho; humano sempre revisa. |
| **Enquadramento regulatório** (GuIA, AIE do MGI). | Uso de IA no governo exige documentação e supervisão. | Trilha de auditoria desde o MVP; **[?]** confirmar se o time precisa fazer a Autoavaliação de Impacto Ético. |

## 9. Perguntas abertas para o cliente

1. **Frameworks de metadados:** quais o Inspire quer aplicar (ex.: o padrão de metadados do próprio
   dados.gov.br, DCAT/DCAT-BR, FAIR, escala de 5 estrelas, outro)? Há documento ou critérios com pesos?
   Sem isso, começo com as regras genéricas da especificação do cliente.
2. **Relação com o Catálogo Nacional de Dados (CND):** o dossiê cita a automação do CND com dashboards
   de qualidade. Este produto é complementar ao CND, ou concorrente/independente?
3. **Link rot (E8):** entra no MVP ou fica para a fase 2?
4. **Papéis institucionais:** você citou o CNPq como coordenador; o dossiê aponta MGI (coordenação),
   CPQD (liderança técnica) e MCTI/Finep (fomento). Quem será o comprador/avaliador do protótipo?
5. **Eixos:** entendi "eixos 3 e 4" como as Camadas 3 e 4 do dossiê (o dossiê também fala em 7 frentes,
   que não detalha). Está correto?
6. **LLM soberano:** o Inspire desenvolve LLMs em português. Há chance de acesso a um desses modelos
   futuramente? Isso favorece manter a integração aberta a provedores.

## 10. Próximos passos

1. Cliente revisa este documento e responde às perguntas.
2. Rodada de arquitetura: C4 (C1–C3 e fluxos), com a conversa sobre tecnologias.
3. ADRs de stack, extração, modelo de dados e provedor de LLM.
4. Backlog detalhado por épico e início da implementação.
