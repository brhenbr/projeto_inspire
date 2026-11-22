#!/usr/bin/env bash
# Roda os testes da ferramenta em um contêiner descartável (nada é instalado no computador).
set -euo pipefail
cd "$(dirname "$0")"
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/w:ro" -w /w python:3.12-slim \
  sh -c "PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v"
