# CLAUDE.md — Inspire Catálogo (dados.gov.br)

Protótipo web, monousuário porém com arquitetura desacoplada, para **extração, discovery e curadoria
(humano + LLM) do catálogo de metadados do dados.gov.br**, no contexto do projeto Inspire.

## Papéis e relação com o cliente
- O cliente (dono do produto) decide escopo e produto. Eu atuo como Product Manager, Arquiteto de
  Soluções e Engenheiro de Software.
- Interação intensa durante escopo, desenho, features, arquitetura e tecnologias. Depois disso,
  autonomia, voltando ao cliente nos testes E2E e em decisões fora do escopo aprovado.
- Tecnologias: antes de fixar a stack, há uma tarefa explícita de conversa com o cliente.

## Escopo vigente (decisões do cliente)
- Só **metadados** do catálogo completo; recursos apenas apontados (link), nunca baixados.
- Só datasets **públicos**. Extração recorrente, por ora acionada manualmente (botão na web ou comando).
- Web + API, interação básica. Execução em **Docker**. Preferência por open source / free use; custo mínimo.
- LLM: curadoria = humano parametriza, LLM executa. Se custo alto, apenas deixar **pronto para integrar**
  (LLM gratuito/local). Exploração por linguagem natural é desejável, não obrigatória.
- Portal é **somente leitura** no curto/médio prazo; a arquitetura deve permitir propor alterações de
  volta no futuro (não implementar agora).

## Contexto institucional
- Frente UFSCar do Inspire, sob acordo UFSCar/CPQD. O cliente é pesquisador da UFSCar; o protótipo é
  avaliado primeiro por professores da UFSCar e depois por órgãos públicos (MGI, CPQD).
- Produto atende as atividades A1, A4, A6 e A7 do plano; DCAT-BR/DQV (A5) é fase 2; foco ignora a parte acadêmica.
- `docs/00-descoberta/restrito/` guarda documentos contratuais e é ignorado pelo git. Não resumir
  valores, bolsas ou desembolsos em arquivos versionados. O repositório pode se tornar público.
- Backlog: `docs/01-produto/backlog/backlog.json` é a fonte; `.md` e `.csv` são gerados.
- Diagramas: Mermaid nos `.md`; `docs/diagramas.html` é gerado por `kit/scripts/gerar_visualizador.py`. Renderizar e olhar antes de entregar.

## Padrões de metadados (definidos pelo projeto)
- **DCAT-BR** (perfil brasileiro do DCAT, usado no Catálogo Nacional de Dados), **DQV** e princípios **FAIR**.
  Em caso de dúvida, usar os princípios do **DMBOK**. O modelo `catalogo` nasce alinhado ao DCAT-BR.
- Regras de qualidade são organizadas por dimensões DQV/FAIR/DMBOK e citam a fonte (US-023).

## Armazenamento (ADR-0005, aceita)
- Um PostgreSQL com camadas: `raw` (JSON bruto) → `catalogo` (tabular, reconstruível) → `analitico`; `curadoria` separada.

## Segurança e soberania (ADR-0002) — vale para toda decisão
- Nada sai da infraestrutura do projeto sem ADR. Nuvem de LLM no exterior é proibida por padrão.
  **Exceção aprovada (ADR-0004):** API gratuita de LLM, só com campos públicos do catálogo, desligada por
  padrão, com lista de provedores aprovados e aviso na tela. Nunca enviar contatos pessoais nem a base curada.
- Só software livre e auditável, sem telemetria externa; dependências fixadas e varridas no CI.
- Contatos de responsáveis dos conjuntos (nome/e-mail) são dados pessoais: minimizar e nunca enviar a LLM.

## Extração: controle de custo (ADR-0006)
- Controle no backend, não só na tela: uma execução ativa por vez (índice único parcial), intervalo mínimo
  (incremental 60 min, completa 24 h, configuráveis), incremental por padrão, "forçar" só ignora o intervalo.
- Medido: detalhe ~0,17 s, listagem ~0,24 s por chamada; carga completa ~1 h em série (~15-20 min com 4 em
  paralelo); a data da listagem coincidiu com a do detalhe em 24/24 amostras (validar em escala).

## Cronograma e gestão
- Cliente é o gestor: dá as direções. Meta: o mais rápido possível e o máximo de features, com plano
  e cronograma ajustados em conjunto ao longo do caminho. Demonstração a professores da UFSCar em breve.

## Ambiente de desenvolvimento (medido em 2026-11-21)
- Windows, i7-4500U, 16 GB, sem GPU útil: LLM local só pequeno e em CPU. Docker Desktop precisa estar aberto (verificado funcionando, 8 GB para o Docker). Sem GPU: LLM via API (ADR-0004), com perfil `llm-local` preparado para GPU futura.

## Fatos do payload real (conferidos em 2026-11-21)
- Datas em texto `dd/mm/aaaa`; muitos campos nulos; no detalhe a organização vem como slug; há `conjuntoDadosAssociados`
  fora do Swagger; o portal já traz `selo` e `atualizado`. Nome e/ou e-mail do responsável vêm em boa parte dos detalhes
  (amostra de 59: nome em 30, nome+e-mail em 16): remover na ingestão (modelo-de-dados.md, seção 2).

## Testes e ferramentas
- Testes de integração rodam no banco `inspire_test` (criado pelo conftest) e RECUSAM rodar em outro banco. Nunca no
  banco da aplicação: um teste já deixou um job na fila e o worker o executou de verdade.
- `bash scripts/formatar.sh` formata/corrige o backend; `bash scripts/qualidade.sh` é o portão completo.
- E2E: `bash scripts/e2e.sh` (Playwright + portal falso, pilha descartável em `docker-compose.e2e.yml`). Ver docs/05-testes/e2e.md.
- Parâmetro de saída da exportação é `saida` (não `formato`, que é filtro de recurso).
- LLM: modo `simulado` (sem IA, sem rede) por padrão no compose; provedor real só por configuração (ADR-0011).

## Armadilhas já vividas
- Nunca editar migração já aplicada: criar uma nova (a 0006 reconcilia bancos migrados com a 0004 intermediária).
- nginx precisa resolver o nome da API dinamicamente (resolver do Docker), senão devolve 502 quando a API é recriada.
- `docker compose run` não reconstrói imagem: o `scripts/e2e.sh` faz `build` antes.

## Regras de trabalho
- Documentação em **português**; código e identificadores em inglês. O cliente achou os C4 técnicos demais:
  colocar um parágrafo "em palavras simples" no topo de cada doc de arquitetura e rever o C4 com ele no final.
- Todo o ciclo (concepção, desenho, implementação, testes, deploy) é registrado em `docs/`.
- Decisões relevantes viram ADR em `docs/03-decisoes/` (template em `kit/templates/`).
- Cada sessão de trabalho gera uma entrada em `docs/diario/`.
- Desenho com **C4**: C1, C2, C3 e, no nível 4, só fluxos/sequência/estados. Sem diagramas de classe.
  Diagramas em Mermaid, versionados junto da doc.
- Testes profissionais mas proporcionais a um MVP: o app não pode quebrar por coisa boba.
- Nunca commitar segredos. A chave da API vive em `.env` (ignorado pelo git; modelo em `.env.example`).
- Só fazer push para remoto quando o cliente autorizar. O remoto será o GitHub do cliente.

## Fatos verificados sobre a API do dados.gov.br (2026-11-21)
- OpenAPI: `https://dados.gov.br/v3/api-docs` (cópia em `docs/00-descoberta/`).
- **Todas as rotas de dados retornam 401 sem o header `chave-api-dados-abertos`**, inclusive as
  "públicas". A especificação técnica do cliente diz que seriam abertas; isso não se confirmou.
- Listagem paginada devolve só resumo (15 itens por página, `pagina` começa em 1, sem total); os
  metadados completos exigem chamada de detalhe por dataset.
- **A API é intermitente: a mesma consulta pode devolver lista vazia e logo depois 15 itens.** Página
  vazia NÃO significa fim; sempre tentar de novo e conferir contra o total por organização.
- **Alguns conjuntos aparecem na listagem mas o detalhe devolve sempre HTTP 400** ("Erro ao executar a consulta"):
  1 em 60 na amostra (um do IPEA). Não aborta a extração: registrar o item como indisponível e listar no relatório.
- **O portal bloqueia chamadas rápidas demais respondendo HTTP 405** (visto: ~3.500 chamadas seguidas a 4 em
  paralelo sem limite de taxa; 16.601 respostas 405; minutos depois os mesmos itens davam 200). Por isso o cliente
  limita a taxa (`PORTAL_MAX_RPS`, padrão 4/s) e pausa todas as threads ao ver 405/429/503. 400 ocasional é defeito
  de item específico; 405 NUNCA é erro definitivo do item.
- **Extração real completa feita em 2026-11-21** (89 min a 4 req/s): 20.218 conjuntos coletados de 20.682 declarados (cobertura 97,8%:
  por isso as remoções NÃO foram aplicadas, regra de segurança abaixo de 99%), 560 sem detalhe (2,8%, HTTP 400 do portal), 0 erros,
  256 organizações com conjuntos, 126.741 recursos, nota média 72,9. Em 19.658 detalhes, 13.363 tinham responsável: 0 foram gravados.
- Tamanho medido antes: ~20.700 conjuntos em 311 organizações (soma de `qtdConjuntoDeDados`).
- A chave do cliente está em `.env` e foi validada (200). Nunca imprimir seu valor.

## Comandos
- Subir: `docker compose up --build` (web em http://127.0.0.1:8080, API em `/api/docs`).
- Portão de qualidade: `bash scripts/qualidade.sh` (ruff, mypy, pytest com PostgreSQL real e cobertura >= 80%, eslint, tsc, vitest). Rodar antes de cada commit de código.
- Dependências: alterar `pyproject.toml`/`package.json` e regerar `uv.lock`/`package-lock.json` em contêiner; nunca instalar no host.
- Código em inglês; schemas/tabelas do banco em português (vocabulário do portal).

## Estrutura do repositório
- `app/` — código do produto.
- `docs/` — documentação do projeto (00-descoberta … 06-deploy, diario).
- `kit/` e `.claude/` — kit de processo **reaproveitável** em outros projetos. Mantê-lo livre de
  referências a este produto para poder ser extraído facilmente.
