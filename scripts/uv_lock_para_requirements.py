"""Converte app/backend/uv.lock em um requirements.txt (nome==versão) para o pip-audit. Uso: python uv_lock_para_requirements.py SAIDA"""

import pathlib
import sys
import tomllib

lock = tomllib.loads(pathlib.Path("app/backend/uv.lock").read_text(encoding="utf-8"))
pacotes = [p for p in lock["package"] if p.get("source", {}).get("registry")]
pathlib.Path(sys.argv[1]).write_text("".join(f"{p['name']}=={p['version']}\n" for p in pacotes), encoding="utf-8")
print(len(pacotes), "pacotes fixados no uv.lock")
