#!/usr/bin/env bash
# Pacote de teste: leva a base já extraída para outra máquina, sem refazer a extração (~90 min).
#
#   bash scripts/pacote-de-teste.sh gerar [arquivo]      gera o pacote (padrão: pacote/inspire-base-AAAAMMDD.dump)
#   bash scripts/pacote-de-teste.sh carregar <arquivo>   substitui a base desta máquina pelo conteúdo do pacote
#
# O que vai no pacote: catálogo espelhado, qualidade e pesos, histórico de extrações. O que NÃO vai: curadoria feita
# (alterações, status, coleções, propostas de LLM), para cada testador começar do zero; chaves de API (ficam no .env de
# cada um); contatos de responsáveis (já são removidos na extração).
# Variáveis: DB_NAME (padrão inspire), NO_RESTART=1 (não reinicia a API ao carregar; usado em verificações).
set -euo pipefail
cd "$(dirname "$0")/.."
DB="${DB_NAME:-inspire}"
C="docker compose"

gerar() {
  local out="${1:-pacote/inspire-base-$(date +%Y%m%d).dump}"
  mkdir -p "$(dirname "$out")"
  $C exec -T db pg_dump -U inspire -d "$DB" -Fc --no-owner --exclude-table-data='curadoria.*' > "$out"
  (cd "$(dirname "$out")" && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
  echo "Pacote gerado: $out ($(du -h "$out" | cut -f1))"
  echo "Envie junto o arquivo .sha256; quem receber confere a integridade ao carregar."
}

carregar() {
  local file="${1:?Informe o arquivo do pacote}"
  [ -f "$file" ] || { echo "Arquivo não encontrado: $file"; exit 1; }
  if [ -f "$file.sha256" ]; then
    (cd "$(dirname "$file")" && sha256sum -c "$(basename "$file").sha256") || { echo "O pacote está corrompido ou foi alterado."; exit 1; }
  else
    echo "Aviso: sem arquivo .sha256; a integridade do pacote não foi conferida."
  fi
  $C up -d db >/dev/null
  [ "${NO_RESTART:-0}" = "1" ] || $C stop api worker >/dev/null 2>&1 || true
  $C exec -T db psql -U inspire -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE)" -c "CREATE DATABASE \"$DB\" OWNER inspire" >/dev/null
  $C exec -T db pg_restore -U inspire -d "$DB" --no-owner --exit-on-error < "$file"
  echo "Base carregada em '$DB'."
  if [ "${NO_RESTART:-0}" != "1" ]; then
    $C up -d --build
    echo "Sistema no ar em http://127.0.0.1:8080"
  fi
}

case "${1:-}" in
  gerar) gerar "${2:-}" ;;
  carregar) carregar "${2:-}" ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
