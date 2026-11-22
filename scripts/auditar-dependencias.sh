#!/usr/bin/env bash
# Varre as dependências fixadas em busca de vulnerabilidades conhecidas (backend: uv.lock; frontend: package-lock.json).
# Sai com erro se achar alguma. O pip-audit e o npm audit rodam em contêineres descartáveis; nada é instalado no computador.
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'rm -f req-lock.tmp' EXIT

echo "== Backend (pip-audit sobre o uv.lock) =="
(python3 scripts/uv_lock_para_requirements.py req-lock.tmp 2>/dev/null || python scripts/uv_lock_para_requirements.py req-lock.tmp)
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/w:ro" python:3.12-slim \
  sh -c "pip install -q --no-cache-dir pip-audit >/dev/null 2>&1 && pip-audit -r /w/req-lock.tmp --no-deps --disable-pip"

echo "== Frontend (npm audit) =="
docker build -q --target build -t inspire-web-build app/frontend >/dev/null
docker run --rm inspire-web-build npm audit
echo "Nenhuma vulnerabilidade conhecida."
