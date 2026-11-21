#!/usr/bin/env bash
# Formata e corrige o que o ruff consegue corrigir sozinho (dentro do Docker, sobre os arquivos locais).
# Uso (na raiz do repositório):  bash scripts/formatar.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd -W 2>/dev/null || pwd)"
docker compose build api >/dev/null
MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps \
  -v "$ROOT/app/backend/src:/app/src" -v "$ROOT/app/backend/tests:/app/tests" -v "$ROOT/app/backend/migrations:/app/migrations" \
  api sh -c "ruff check --fix . && ruff format ."
