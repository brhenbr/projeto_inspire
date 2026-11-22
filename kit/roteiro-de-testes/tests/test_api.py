"""Testes da API do Roteiro de Testes (só biblioteca padrão). Rodar: python -m unittest discover -s tests"""

import csv
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import server  # noqa: E402

EXEMPLO = Path(__file__).resolve().parents[1] / "casos-exemplo"


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.httpd = server.create_server("127.0.0.1", 0, str(Path(self.tmp.name) / "t.db"), str(EXEMPLO))
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, headers=None, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:
                payload = r.read()
                return r.status, (payload if raw else json.loads(payload)), r.headers
        except urllib.error.HTTPError as e:
            payload = e.read()
            return e.code, (payload if raw else json.loads(payload)), e.headers

    def start(self, name="Ana"):
        return self.call("POST", "/api/sessoes", {"roteiro": "exemplo", "testador": name})[1]


class TestSessoes(Base):
    def test_lista_roteiros_e_inicia_sessao(self):
        status, roteiros, _ = self.call("GET", "/api/roteiros")
        self.assertEqual((status, roteiros[0]["roteiro"], roteiros[0]["total"]), (200, "exemplo", 3))
        s = self.start("  Ana   Souza ")
        self.assertEqual(s["sessao"]["testador"], "Ana Souza")  # espaços normalizados
        self.assertFalse(s["retomada"])
        self.assertEqual(len(s["roteiro"]["casos"]), 3)

    def test_mesmo_nome_retoma_a_sessao_aberta_sem_diferenciar_maiusculas(self):
        a = self.start("Ana")
        self.call("PUT", f"/api/sessoes/{a['sessao']['id']}/respostas/EX-01", {"resultado": "passou"})
        b = self.start("ANA")
        self.assertTrue(b["retomada"])
        self.assertEqual(b["sessao"]["id"], a["sessao"]["id"])
        self.assertIn("EX-01", b["respostas"])

    def test_sessao_finalizada_nao_e_retomada(self):
        a = self.start("Ana")
        self.call("POST", f"/api/sessoes/{a['sessao']['id']}/finalizar")
        b = self.start("Ana")
        self.assertFalse(b["retomada"])
        self.assertNotEqual(b["sessao"]["id"], a["sessao"]["id"])

    def test_validacoes_de_nome_e_roteiro(self):
        self.assertEqual(self.call("POST", "/api/sessoes", {"roteiro": "exemplo", "testador": "  "})[0], 422)
        self.assertEqual(self.call("POST", "/api/sessoes", {"roteiro": "exemplo", "testador": "x" * 81})[0], 422)
        self.assertEqual(self.call("POST", "/api/sessoes", {"roteiro": "nao-existe", "testador": "Ana"})[0], 404)
        self.assertEqual(self.call("GET", "/api/sessoes/999")[0], 404)


class TestRespostas(Base):
    def test_passou_falhou_e_nao_executou(self):
        sid = self.start()["sessao"]["id"]
        ok = self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "passou", "comentario": "rápido"})
        self.assertEqual(ok[0], 200)
        self.assertEqual(ok[1]["respostas"]["EX-01"]["comentario"], "rápido")
        falha = self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-02", {"resultado": "falhou", "mensagem_erro": "HTTP 500"})
        self.assertEqual(falha[1]["respostas"]["EX-02"]["mensagem_erro"], "HTTP 500")
        pulou = self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-03", {"resultado": "nao_executou"})
        self.assertEqual(pulou[1]["respostas"]["EX-03"]["resultado"], "nao_executou")

    def test_falhou_exige_mensagem_de_erro(self):
        sid = self.start()["sessao"]["id"]
        status, body, _ = self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "falhou", "mensagem_erro": "  "})
        self.assertEqual(status, 422)
        self.assertIn("mensagem de erro", body["detail"])

    def test_responder_de_novo_substitui_e_limpa_o_erro_se_passou(self):
        sid = self.start()["sessao"]["id"]
        self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "falhou", "mensagem_erro": "x"})
        r = self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "passou", "mensagem_erro": "sobrou"})[1]
        self.assertEqual(len(r["respostas"]), 1)
        self.assertEqual((r["respostas"]["EX-01"]["resultado"], r["respostas"]["EX-01"]["mensagem_erro"]), ("passou", ""))

    def test_entradas_invalidas(self):
        sid = self.start()["sessao"]["id"]
        self.assertEqual(self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "talvez"})[0], 422)
        self.assertEqual(self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-99", {"resultado": "passou"})[0], 404)
        self.assertEqual(self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "passou", "comentario": "x" * 2001})[0], 422)
        self.assertEqual(self.call("PUT", "/api/sessoes/999/respostas/EX-01", {"resultado": "passou"})[0], 404)

    def test_sql_injection_e_html_viram_texto_puro(self):
        sid = self.start("Robert'); DROP TABLE sessao;--")["sessao"]["id"]
        r = self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "passou", "comentario": "<script>alert(1)</script>"})[1]
        self.assertEqual(r["respostas"]["EX-01"]["comentario"], "<script>alert(1)</script>")  # guardado como texto
        self.assertEqual(self.call("GET", f"/api/sessoes/{sid}")[0], 200)  # a tabela continua lá


class TestResultados(Base):
    def populate(self):
        sid = self.start("=cmd|' /C calc'!A0")["sessao"]["id"]
        self.call("PUT", f"/api/sessoes/{sid}/respostas/EX-01", {"resultado": "falhou", "mensagem_erro": "+erro", "comentario": "@x"})

    def test_resultados_abrem_direto_sem_senha(self):
        status, data, _ = self.call("GET", "/api/resultados")
        self.assertEqual((status, data), (200, {"sessoes": [], "respostas": []}))
        self.populate()
        self.assertEqual(len(self.call("GET", "/api/resultados")[1]["respostas"]), 1)

    def test_csv_protege_contra_formulas(self):
        self.populate()
        status, body, headers = self.call("GET", "/api/resultados.csv", raw=True)
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/csv"))
        self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["testador"].startswith("'="))
        self.assertTrue(rows[0]["mensagem_erro"].startswith("'+"))
        self.assertTrue(rows[0]["comentario"].startswith("'@"))


class TestEstaticosEHeaders(Base):
    def test_pagina_e_cabecalhos_de_seguranca(self):
        status, body, headers = self.call("GET", "/", raw=True)
        self.assertEqual(status, 200)
        self.assertIn(b"Roteiro de Testes", body)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_nao_serve_arquivos_fora_da_lista_nem_sobe_diretorios(self):
        self.assertEqual(self.call("GET", "/server.py", raw=True)[0], 404)
        self.assertEqual(self.call("GET", "/../app/server.py", raw=True)[0], 404)
        self.assertEqual(self.call("GET", "/api/nada")[0], 404)


class TestRoteirosInvalidos(unittest.TestCase):
    def test_validacao_do_arquivo_de_casos(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "bom.json").write_text(json.dumps({"roteiro": "bom", "titulo": "B", "versao": "1", "casos": [{"id": "A", "titulo": "t", "passos": ["x"]}]}), encoding="utf-8")
            (Path(d) / "repetido.json").write_text(json.dumps({"roteiro": "rep", "titulo": "R", "versao": "1", "casos": [{"id": "A", "titulo": "t", "passos": []}, {"id": "A", "titulo": "u", "passos": []}]}), encoding="utf-8")
            (Path(d) / "quebrado.json").write_text("{nao é json", encoding="utf-8")
            self.assertEqual(list(server.Roteiros(d).all()), ["bom"])  # os inválidos são ignorados, sem derrubar o servidor


if __name__ == "__main__":
    unittest.main()
