# Kit de processo (reaproveitável)

Elementos usados para conduzir e documentar o produto, independentes do domínio. Para reutilizar em
outro projeto, copie `kit/` e `.claude/` e adapte o `CLAUDE.md`.

| Elemento | Local | Função |
|---|---|---|
| Template de ADR | `kit/templates/adr.md` | Registrar decisões de arquitetura |
| Template de diário | `kit/templates/diario.md` | Registrar cada sessão de trabalho |
| Backlog para Jira | `kit/scripts/backlog_to_jira.py` | Converte `backlog.json` em CSV do Jira e Markdown |
| Roteiro de Testes | `kit/roteiro-de-testes/` | Conduz testadores caso a caso e guarda os resultados (SQLite, sem dependências) |
| Skill registrar-decisao | `.claude/skills/registrar-decisao/` | Criar ADR numerado a partir do template |

Regra: nada aqui pode citar o dados.gov.br ou o projeto Inspire.
