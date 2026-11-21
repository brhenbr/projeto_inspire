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

## Regras de trabalho
- Documentação em **português**; código e identificadores em inglês.
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
- Tamanho medido: ~20.700 conjuntos em 311 organizações (soma de `qtdConjuntoDeDados`).
- A chave do cliente está em `.env` e foi validada (200). Nunca imprimir seu valor.

## Estrutura do repositório
- `app/` — código do produto.
- `docs/` — documentação do projeto (00-descoberta … 06-deploy, diario).
- `kit/` e `.claude/` — kit de processo **reaproveitável** em outros projetos. Mantê-lo livre de
  referências a este produto para poder ser extraído facilmente.
