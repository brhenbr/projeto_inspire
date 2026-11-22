"""Junta os resultados enviados pelos testadores (CSV de "Baixar meus resultados") em um único SQLite.

Uso:   python consolidar.py consolidado.db  maria.csv  joao.csv  ...
Saída: o arquivo SQLite (mesmas tabelas `sessao` e `resposta` da ferramenta) e um resumo por caso no terminal.

Rodar de novo com o mesmo arquivo de saída acrescenta; o mesmo testador + roteiro + caso é substituído pela resposta mais recente.
Só biblioteca padrão do Python.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

COLUMNS = ("roteiro", "versao_roteiro", "testador", "caso_id", "caso_titulo", "resultado", "mensagem_erro", "comentario", "respondida_em")
RESULTS = {"passou": "Passou", "falhou": "Falhou", "nao_executou": "Não executou"}
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessao (
    id INTEGER PRIMARY KEY AUTOINCREMENT, roteiro TEXT NOT NULL, versao_roteiro TEXT NOT NULL, testador TEXT NOT NULL,
    iniciada_em TEXT NOT NULL, ultima_atividade_em TEXT NOT NULL, finalizada_em TEXT,
    UNIQUE (roteiro, testador)
);
CREATE TABLE IF NOT EXISTS resposta (
    id INTEGER PRIMARY KEY AUTOINCREMENT, sessao_id INTEGER NOT NULL REFERENCES sessao (id) ON DELETE CASCADE,
    caso_id TEXT NOT NULL, caso_titulo TEXT, resultado TEXT NOT NULL CHECK (resultado IN ('passou', 'falhou', 'nao_executou')),
    comentario TEXT, mensagem_erro TEXT, respondida_em TEXT NOT NULL, UNIQUE (sessao_id, caso_id)
);
"""


def unescape(value: str) -> str:
    """Desfaz o apóstrofo que o CSV põe antes de textos que começariam como fórmula de planilha."""
    return value[1:] if len(value) > 1 and value[0] == "'" and value[1] in FORMULA_PREFIXES else value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: faltam as colunas {sorted(missing)} (é um CSV de 'Baixar meus resultados'?)")
        rows = []
        for r in reader:
            if r["resultado"] not in RESULTS:
                raise ValueError(f"{path.name}: resultado inválido '{r['resultado']}'")
            rows.append({k: unescape(r[k] or "") for k in COLUMNS})
        return rows


def merge(db_path: Path, csv_paths: list[Path]) -> int:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    total = 0
    with conn:
        for path in csv_paths:
            for r in read_csv(path):
                conn.execute(
                    "INSERT INTO sessao (roteiro, versao_roteiro, testador, iniciada_em, ultima_atividade_em) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (roteiro, testador) DO UPDATE SET versao_roteiro = excluded.versao_roteiro, "
                    "ultima_atividade_em = max(ultima_atividade_em, excluded.ultima_atividade_em)",
                    (r["roteiro"], r["versao_roteiro"], r["testador"], r["respondida_em"], r["respondida_em"]),
                )
                sid = conn.execute("SELECT id FROM sessao WHERE roteiro = ? AND testador = ?", (r["roteiro"], r["testador"])).fetchone()[0]
                conn.execute(
                    "INSERT INTO resposta (sessao_id, caso_id, caso_titulo, resultado, comentario, mensagem_erro, respondida_em) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (sessao_id, caso_id) DO UPDATE SET caso_titulo = excluded.caso_titulo, "
                    "resultado = excluded.resultado, comentario = excluded.comentario, mensagem_erro = excluded.mensagem_erro, "
                    "respondida_em = excluded.respondida_em WHERE excluded.respondida_em >= resposta.respondida_em",
                    (sid, r["caso_id"], r["caso_titulo"], r["resultado"], r["comentario"], r["mensagem_erro"], r["respondida_em"]),
                )
                total += 1
    conn.close()
    return total


def summary(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    per_case: dict[str, Counter[str]] = defaultdict(Counter)
    titles: dict[str, str] = {}
    for caso, titulo, resultado in conn.execute("SELECT caso_id, caso_titulo, resultado FROM resposta ORDER BY caso_id"):
        per_case[caso][resultado] += 1
        titles[caso] = titulo or ""
    testers = conn.execute("SELECT count(DISTINCT testador) FROM sessao").fetchone()[0]
    lines = [f"{testers} testador(es). Por caso (Passou / Falhou / Não executou):"]
    for caso in sorted(per_case):
        c = per_case[caso]
        flag = "  <-- atenção" if c["falhou"] else ""
        lines.append(f"  {caso} {titles[caso][:48]:48} {c['passou']:>3} / {c['falhou']:>3} / {c['nao_executou']:>3}{flag}")
    conn.close()
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    db, files = Path(argv[1]), [Path(a) for a in argv[2:]]
    try:
        n = merge(db, files)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: {exc}")
        return 2
    print(f"{n} resposta(s) lida(s) de {len(files)} arquivo(s) para {db}\n")
    print(summary(db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
