"""Testes do consolidar.py e do CSV por sessão."""

import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))
import consolidar  # noqa: E402
import server  # noqa: E402

HEADER = "roteiro,versao_roteiro,testador,caso_id,caso_titulo,resultado,mensagem_erro,comentario,respondida_em\r\n"


def write(path: Path, *rows: str) -> Path:
    path.write_text("﻿" + HEADER + "".join(r + "\r\n" for r in rows), encoding="utf-8")
    return path


class TestConsolidar(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_junta_testadores_e_resume_por_caso(self) -> None:
        a = write(self.dir / "ana.csv", "x,1,Ana,C1,Buscar,passou,,ok,2026-11-22T10:00:00", "x,1,Ana,C2,Criar,falhou,HTTP 500,,2026-11-22T10:05:00")
        b = write(self.dir / "bia.csv", "x,1,Bia,C1,Buscar,passou,,,2026-11-22T11:00:00", "x,1,Bia,C2,Criar,falhou,erro 2,confuso,2026-11-22T11:05:00")
        db = self.dir / "c.db"

        self.assertEqual(consolidar.merge(db, [a, b]), 4)

        conn = sqlite3.connect(db)
        self.assertEqual(conn.execute("SELECT count(*) FROM sessao").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT count(*) FROM resposta WHERE resultado = 'falhou'").fetchone()[0], 2)
        text = consolidar.summary(db)
        self.assertIn("2 testador(es)", text)
        self.assertIn("C2", text)
        self.assertIn("atenção", text)

    def test_rodar_de_novo_nao_duplica_e_a_resposta_mais_recente_vence(self) -> None:
        db = self.dir / "c.db"
        consolidar.merge(db, [write(self.dir / "1.csv", "x,1,Ana,C1,Buscar,falhou,erro,,2026-11-22T10:00:00")])
        consolidar.merge(db, [write(self.dir / "2.csv", "x,1,Ana,C1,Buscar,passou,,corrigiram,2026-11-22T12:00:00")])
        consolidar.merge(db, [write(self.dir / "3.csv", "x,1,Ana,C1,Buscar,falhou,antigo,,2026-11-22T09:00:00")])  # mais velho: ignorado

        rows = sqlite3.connect(db).execute("SELECT resultado, comentario FROM resposta").fetchall()
        self.assertEqual(rows, [("passou", "corrigiram")])

    def test_desfaz_o_apostrofo_de_formula_mas_preserva_o_resto(self) -> None:
        self.assertEqual(consolidar.unescape("'=SOMA(A1)"), "=SOMA(A1)")
        self.assertEqual(consolidar.unescape("'olá"), "'olá")  # apóstrofo legítimo
        self.assertEqual(consolidar.unescape("normal"), "normal")

    def test_csv_invalido_da_erro_claro(self) -> None:
        ruim = self.dir / "ruim.csv"
        ruim.write_text("a,b\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "faltam as colunas"):
            consolidar.read_csv(ruim)
        invalido = write(self.dir / "inv.csv", "x,1,Ana,C1,Buscar,talvez,,,2026-11-22T10:00:00")
        with self.assertRaisesRegex(ValueError, "resultado inválido"):
            consolidar.read_csv(invalido)


class TestCsvPorSessao(unittest.TestCase):
    def test_baixar_meus_resultados_traz_so_a_sessao_do_testador(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            httpd = server.create_server("127.0.0.1", 0, str(Path(d) / "t.db"), str(ROOT / "casos-exemplo"))
            base = f"http://127.0.0.1:{httpd.server_address[1]}"
            threading.Thread(target=httpd.serve_forever, daemon=True).start()

            def call(method: str, path: str, body: dict | None = None) -> bytes:
                req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req) as r:
                    return r.read()

            try:
                ids = {}
                for nome in ("Ana", "Bia"):
                    ids[nome] = json.loads(call("POST", "/api/sessoes", {"roteiro": "exemplo", "testador": nome}))["sessao"]["id"]
                    call("PUT", f"/api/sessoes/{ids[nome]}/respostas/EX-01", {"resultado": "passou", "comentario": f"de {nome}"})

                csv_ana = call("GET", f"/api/sessoes/{ids['Ana']}/resultados.csv").decode("utf-8-sig")

                self.assertIn("de Ana", csv_ana)
                self.assertNotIn("de Bia", csv_ana)
                # o arquivo baixado é aceito pelo consolidar
                f = Path(d) / "ana.csv"
                f.write_text(csv_ana, encoding="utf-8")
                self.assertEqual(consolidar.merge(Path(d) / "c.db", [f]), 1)
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
