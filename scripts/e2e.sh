#!/usr/bin/env bash
# Testes ponta a ponta: sobe a pilha descartável (banco novo, portal falso, API, worker, web) e roda o Playwright.
# Uso (na raiz do repositório):  bash scripts/e2e.sh
# Relatório HTML: app/e2e/reports/html/index.html
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p app/e2e/reports
docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from playwright
code=$?
docker compose -f docker-compose.e2e.yml down -v --remove-orphans >/dev/null 2>&1
exit $code
