#!/usr/bin/env bash
# Portão local de qualidade: lint, tipos, testes e build, tudo dentro do Docker.
# Uso (na raiz do repositório):  bash scripts/qualidade.sh
set -euo pipefail
cd "$(dirname "$0")/.."

etapa() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

etapa "Construindo imagens"
docker compose build api
docker build --target build -t inspire-web-build app/frontend

etapa "Backend: ruff (lint e formato)"
docker compose run --rm --no-deps api ruff check .
docker compose run --rm --no-deps api ruff format --check .

etapa "Backend: mypy (tipos)"
docker compose run --rm --no-deps api mypy

etapa "Backend: testes e cobertura (com PostgreSQL real)"
docker compose up -d --wait db
docker compose run --rm api pytest --cov --cov-report=term-missing

etapa "Frontend: lint"
docker run --rm inspire-web-build npm run lint

etapa "Frontend: tipos e testes"
docker run --rm inspire-web-build npm run typecheck
docker run --rm inspire-web-build npm test

printf '\n\033[1;32mTudo certo.\033[0m\n'
