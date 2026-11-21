# Implementação 01 — Esqueleto do projeto

**Em palavras simples:** montamos a "carcaça" do sistema: as cinco peças (tela, API, worker, banco e a
rotina que prepara o banco) sobem juntas com um comando e conversam entre si. Ainda não faz nada do
catálogo; serve de base sólida para construir a extração em cima, já com testes e verificações automáticas.

- **Data:** 2026-11-21
- **Backlog:** US-061 (concluída), US-062 (parcial: portão local pronto, CI depois do primeiro push)

## O que existe
| Peça | Onde | O que faz hoje |
|---|---|---|
| Banco | contêiner `db` (PostgreSQL 16) | Guarda os dados; não é publicado no host |
| Migração | contêiner `migrate` | Cria os schemas `raw`, `catalogo`, `curadoria`, `analitico` e as extensões `unaccent` e `pg_trgm`, e termina |
| API | `app/backend`, contêiner `api` | `GET /v1/saude`; documentação OpenAPI em `/api/docs` |
| Worker | `app/backend`, contêiner `worker` | Processo vivo com batimento em log; a fila de jobs entra com a extração |
| Web | `app/frontend`, contêiner `web` | Página que mostra o estado da API e do banco; é a única porta publicada, só em localhost |

## Como rodar
```
docker compose up --build        # sobe tudo; abra http://127.0.0.1:8080
docker compose down              # para (os dados do banco ficam no volume)
bash scripts/qualidade.sh        # portão de qualidade (PowerShell: .\scripts\qualidade.ps1)
```
O Docker Desktop precisa estar aberto. A chave do portal fica no `.env` (ver `.env.example`).

## Decisões de implementação
- **Versões fixas:** `uv.lock` (Python) e `package-lock.json` (Node) são versionados; os contêineres
  instalam exatamente o que está no lock (ADR-0002).
- **Menor privilégio:** contêineres rodam sem root, com `no-new-privileges` e todas as capacidades Linux
  removidas. A chave do portal só é entregue ao worker, nunca à API nem à web.
- **Publicação:** só o `web` é exposto, em `127.0.0.1`. O nginx encaminha `/api/` para a API e remove o
  prefixo; a API é informada disso por `--root-path /api`.
- **Idioma no código:** identificadores em inglês; nomes de schemas e tabelas do banco em português, para
  acompanhar o vocabulário do portal e do modelo de dados (`conjunto`, `recurso`, `organizacao`).
- **Migrações escritas à mão** com Alembic, sem autogenerate; reversíveis.
- **Segredos:** `SecretStr` na configuração, para a chave não aparecer em `repr` nem em log. Teste cobre isso.

## Verificação (2026-11-21)
- Backend: ruff, mypy estrito, 9 testes (unitários e com PostgreSQL real), cobertura 84% (meta 80%).
- Frontend: eslint, `tsc`, 3 testes.
- Sistema completo no Docker: página 200; `/api/v1/saude` ok; OpenAPI com servidor `/api`; nenhuma porta
  fora de localhost; a chave não aparece nos logs.

## Pendências conhecidas
- Aviso de depreciação do Starlette sobre `httpx` no cliente de teste: acompanhar, não afeta o produto.
- O worker ainda não tem teste do laço principal (`main`); entra quando a fila de jobs chegar.
- Pre-commit e CI: só após o primeiro push (ADR-0003).
