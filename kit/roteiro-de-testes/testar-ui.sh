#!/usr/bin/env bash
# Teste de fumaça da interface em um navegador real (Playwright em contêiner descartável).
# Pré-requisito: a ferramenta no ar com RESULTS_PIN=pin-local-teste (docker compose up -d --build).
set -euo pipefail
cd "$(dirname "$0")"
MSYS_NO_PATHCONV=1 docker run --rm --add-host host.docker.internal:host-gateway \
  -v "$(pwd -W 2>/dev/null || pwd)/e2e:/w:ro" -e RESULTS_PIN="${RESULTS_PIN:-pin-local-teste}" \
  mcr.microsoft.com/playwright:v1.65.1-noble \
  sh -c "mkdir -p /tmp/t && cd /tmp/t && cp /w/smoke.mjs . && npm init -y >/dev/null && npm i --silent playwright@1.65.1 && node smoke.mjs"
