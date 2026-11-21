#!/usr/bin/env bash
# Testes ponta a ponta: sobe a pilha descartável (banco novo, portal falso, API, worker, web) e roda o Playwright.
# Uso (na raiz do repositório):  bash scripts/e2e.sh
# Relatório HTML: app/e2e/reports/html/index.html
set -uo pipefail
cd "$(dirname "$0")/.."
C="docker compose -f docker-compose.e2e.yml"
mkdir -p app/e2e/reports
$C down -v --remove-orphans >/dev/null 2>&1
if ! $C up -d --build --wait db migrate fake-portal api worker web; then
  echo "A pilha E2E não subiu."; $C logs --tail 40; $C down -v --remove-orphans >/dev/null 2>&1; exit 1
fi
$C build playwright || { echo "Falha ao construir a imagem dos testes."; $C down -v --remove-orphans >/dev/null 2>&1; exit 1; }
$C run --rm playwright
code=$?
if [ $code -ne 0 ]; then echo "--- logs do worker (últimas linhas)"; $C logs --tail 30 worker; fi
$C down -v --remove-orphans >/dev/null 2>&1
exit $code
