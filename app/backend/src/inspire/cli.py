"""Linha de comando (US-007). Usa as MESMAS regras da API (ADR-0006).

Exemplos (dentro do contêiner):
    python -m inspire.cli extrair --tipo incremental
    python -m inspire.cli estado
"""

import argparse
import json
import sys

from inspire.api.deps import get_policy
from inspire.db import get_engine
from inspire.extraction import control


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inspire")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extrair", help="enfileira uma extração (o worker a executa)")
    ex.add_argument("--tipo", choices=["incremental", "completa"], default="incremental")
    ex.add_argument("--forcar", action="store_true", help="ignora o intervalo mínimo")
    sub.add_parser("estado", help="mostra o que pode ser pedido agora")
    sub.add_parser("reconstruir", help="reconstrói o modelo de leitura e recalcula a qualidade")
    sub.add_parser("matriz-qualidade", help="imprime a matriz de qualidade em Markdown")
    args = parser.parse_args(argv)

    if args.cmd == "matriz-qualidade":
        from inspire.quality.matrix import render_markdown

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        print(render_markdown())
        return 0
    if args.cmd == "reconstruir":
        from inspire.analytics.pipeline import rebuild_after_extraction

        rebuild_after_extraction(get_engine())
        print("modelo de leitura e qualidade reconstruídos")
        return 0
    engine, policy = get_engine(), get_policy()
    if args.cmd == "estado":
        out = {
            k: control.evaluate(engine, k, policy=policy).__dict__
            for k in ("incremental", "completa")
        }
        print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
        return 0
    decision = control.request_extraction(
        engine, args.tipo, forced=args.forcar, requested_by="cli", policy=policy
    )
    print(json.dumps(decision.__dict__, default=str, ensure_ascii=False))
    return 0 if decision.status != "too_soon" else 3


if __name__ == "__main__":
    sys.exit(main())
