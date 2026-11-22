#!/usr/bin/env bash
# Valida os roteiros de teste (docs/07-manual/casos/*.json) com o mesmo validador da ferramenta de testes.
set -euo pipefail
cd "$(dirname "$0")/.."
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/w:ro" -w /w python:3.12-slim python -I -c "
import json, sys, pathlib
sys.path.insert(0, 'kit/roteiro-de-testes/app')
import server
ok = True
for p in sorted(pathlib.Path('docs/07-manual/casos').glob('*.json')):
    try:
        d = server.Roteiros.validate(json.loads(p.read_text(encoding='utf-8')), p.name)
        print(f'ok: {p.name} ({len(d[\"casos\"])} casos)')
    except Exception as e:
        ok = False; print(f'ERRO: {e}')
sys.exit(0 if ok else 1)
"
