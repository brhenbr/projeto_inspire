#!/usr/bin/env bash
# Sobe a página de testes (kit/roteiro-de-testes) já com os casos do manual deste produto.
#   bash scripts/testes-de-aceitacao.sh          sobe em http://127.0.0.1:8090
#   bash scripts/testes-de-aceitacao.sh parar    derruba (os resultados ficam guardados no volume)
set -euo pipefail
cd "$(dirname "$0")/../kit/roteiro-de-testes"
export CASOS_DIR_HOST="$(cd ../../docs/07-manual/casos && pwd -W 2>/dev/null || pwd)"
if [ "${1:-}" = "parar" ]; then docker compose down; exit 0; fi
docker compose up -d --build
echo "Página de testes: http://127.0.0.1:${ROTEIRO_PORT:-8090}  (sistema: http://127.0.0.1:8080)"
