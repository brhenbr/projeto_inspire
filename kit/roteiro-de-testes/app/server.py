"""Roteiro de Testes: servidor HTTP + SQLite, só com a biblioteca padrão do Python.

Variáveis de ambiente:
  DB_PATH      arquivo SQLite (padrão /data/roteiro.db)
  CASOS_DIR    pasta com os roteiros .json (padrão /casos)
  HOST, PORT   onde escutar (padrão 0.0.0.0:8000; quem publica a porta decide quem acessa)
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

STATIC_DIR = Path(__file__).parent / "static"
STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
RESULTS = ("passou", "falhou", "nao_executou")
MAX_BODY = 64 * 1024
LIMITS = {"testador": 80, "comentario": 2000, "mensagem_erro": 2000}
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roteiro TEXT NOT NULL,
    versao_roteiro TEXT NOT NULL,
    testador TEXT NOT NULL,
    iniciada_em TEXT NOT NULL,
    ultima_atividade_em TEXT NOT NULL,
    finalizada_em TEXT
);
CREATE TABLE IF NOT EXISTS resposta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id INTEGER NOT NULL REFERENCES sessao (id) ON DELETE CASCADE,
    caso_id TEXT NOT NULL,
    resultado TEXT NOT NULL CHECK (resultado IN ('passou', 'falhou', 'nao_executou')),
    comentario TEXT,
    mensagem_erro TEXT,
    respondida_em TEXT NOT NULL,
    UNIQUE (sessao_id, caso_id)
);
"""


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    """Acesso ao SQLite. Uma conexão por operação; SQL sempre parametrizado."""

    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def run(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._lock, self._connect() as conn:
            return conn.execute(sql, params).fetchall()


class Roteiros:
    """Lê os roteiros da pasta de casos (recarrega quando o arquivo muda)."""

    def __init__(self, folder: str) -> None:
        self.folder = Path(folder)
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def validate(data: Any, file: str) -> dict[str, Any]:
        if not isinstance(data, dict) or not ID_PATTERN.match(str(data.get("roteiro", ""))):
            raise ValueError(f"{file}: 'roteiro' ausente ou inválido")
        for key in ("titulo", "versao"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f"{file}: '{key}' ausente")
        casos = data.get("casos")
        if not isinstance(casos, list) or not casos:
            raise ValueError(f"{file}: 'casos' deve ser uma lista não vazia")
        seen: set[str] = set()
        for c in casos:
            if not isinstance(c, dict) or not ID_PATTERN.match(str(c.get("id", ""))):
                raise ValueError(f"{file}: caso sem 'id' válido")
            if c["id"] in seen:
                raise ValueError(f"{file}: id repetido {c['id']}")
            seen.add(c["id"])
            if not isinstance(c.get("titulo"), str) or not isinstance(c.get("passos"), list):
                raise ValueError(f"{file}: caso {c['id']} precisa de 'titulo' e 'passos'")
        return data

    def all(self) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for path in sorted(self.folder.glob("*.json")):
            mtime = path.stat().st_mtime
            cached = self._cache.get(str(path))
            if cached is None or cached[0] != mtime:
                try:
                    data = self.validate(json.loads(path.read_text(encoding="utf-8")), path.name)
                except (ValueError, OSError) as exc:
                    print(f"[roteiro-de-testes] ignorando {path.name}: {exc}", flush=True)
                    continue
                self._cache[str(path)] = (mtime, data)
            found[self._cache[str(path)][1]["roteiro"]] = self._cache[str(path)][1]
        return found

    def get(self, roteiro: str) -> dict[str, Any]:
        data = self.all().get(roteiro)
        if data is None:
            raise ApiError(404, "Roteiro não encontrado")
        return data


class App:
    def __init__(self, store: Store, roteiros: Roteiros) -> None:
        self.store, self.roteiros = store, roteiros

    # ---------------------------------------------------------------- sessões
    def list_roteiros(self) -> list[dict[str, Any]]:
        return [
            {"roteiro": r["roteiro"], "titulo": r["titulo"], "versao": r["versao"], "descricao": r.get("descricao", ""), "total": len(r["casos"])}
            for r in self.roteiros.all().values()
        ]

    @staticmethod
    def clean(value: Any, field: str, *, required: bool = False) -> str:
        text = " ".join(str(value or "").split()) if field == "testador" else str(value or "").strip()
        if required and not text:
            raise ApiError(422, f"Informe {'o nome' if field == 'testador' else field}")
        if len(text) > LIMITS[field]:
            raise ApiError(422, f"O campo {field} aceita no máximo {LIMITS[field]} caracteres")
        return text

    def start(self, body: dict[str, Any]) -> dict[str, Any]:
        roteiro = self.roteiros.get(str(body.get("roteiro", "")))
        name = self.clean(body.get("testador"), "testador", required=True)
        rows = self.store.run(
            "SELECT id FROM sessao WHERE roteiro = ? AND lower(testador) = lower(?) AND finalizada_em IS NULL "
            "ORDER BY id DESC LIMIT 1",
            (roteiro["roteiro"], name),
        )
        resumed = bool(rows)
        if rows:
            session_id = rows[0]["id"]
        else:
            stamp = now()
            self.store.run(
                "INSERT INTO sessao (roteiro, versao_roteiro, testador, iniciada_em, ultima_atividade_em) VALUES (?, ?, ?, ?, ?)",
                (roteiro["roteiro"], roteiro["versao"], name, stamp, stamp),
            )
            session_id = self.store.run("SELECT max(id) AS id FROM sessao")[0]["id"]
        return {**self.session(session_id), "retomada": resumed}

    def session(self, session_id: int) -> dict[str, Any]:
        rows = self.store.run("SELECT * FROM sessao WHERE id = ?", (session_id,))
        if not rows:
            raise ApiError(404, "Sessão não encontrada")
        s = dict(rows[0])
        roteiro = self.roteiros.get(s["roteiro"])
        answers = {
            r["caso_id"]: {k: r[k] for k in ("resultado", "comentario", "mensagem_erro", "respondida_em")}
            for r in self.store.run("SELECT * FROM resposta WHERE sessao_id = ?", (session_id,))
        }
        return {
            "sessao": s,
            "roteiro": roteiro,
            "respostas": answers,
            "roteiro_atualizado": roteiro["versao"] != s["versao_roteiro"],
        }

    def answer(self, session_id: int, case_id: str, body: dict[str, Any]) -> dict[str, Any]:
        rows = self.store.run("SELECT roteiro, finalizada_em FROM sessao WHERE id = ?", (session_id,))
        if not rows:
            raise ApiError(404, "Sessão não encontrada")
        roteiro = self.roteiros.get(rows[0]["roteiro"])
        if case_id not in {c["id"] for c in roteiro["casos"]}:
            raise ApiError(404, "Caso não encontrado neste roteiro")
        result = body.get("resultado")
        if result not in RESULTS:
            raise ApiError(422, "Resultado inválido (use passou, falhou ou nao_executou)")
        comment = self.clean(body.get("comentario"), "comentario")
        error = self.clean(body.get("mensagem_erro"), "mensagem_erro")
        if result == "falhou" and not error:
            raise ApiError(422, "Em \"Falhou\", descreva a mensagem de erro ou o que aconteceu")
        if result != "falhou":
            error = ""  # só falha tem erro
        stamp = now()
        self.store.run(
            "INSERT INTO resposta (sessao_id, caso_id, resultado, comentario, mensagem_erro, respondida_em) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (sessao_id, caso_id) DO UPDATE SET resultado = excluded.resultado, "
            "comentario = excluded.comentario, mensagem_erro = excluded.mensagem_erro, respondida_em = excluded.respondida_em",
            (session_id, case_id, result, comment, error, stamp),
        )
        self.store.run("UPDATE sessao SET ultima_atividade_em = ? WHERE id = ?", (stamp, session_id))
        return self.session(session_id)

    def finish(self, session_id: int) -> dict[str, Any]:
        self.session(session_id)
        self.store.run("UPDATE sessao SET finalizada_em = ? WHERE id = ? AND finalizada_em IS NULL", (now(), session_id))
        return self.session(session_id)

    # ---------------------------------------------------------------- resultados
    def results(self) -> dict[str, Any]:
        sessions = [dict(r) for r in self.store.run("SELECT * FROM sessao ORDER BY id")]
        answers = [dict(r) for r in self.store.run("SELECT * FROM resposta ORDER BY sessao_id, id")]
        titles = {c["id"]: c["titulo"] for r in self.roteiros.all().values() for c in r["casos"]}
        for a in answers:
            a["caso_titulo"] = titles.get(a["caso_id"], "")
        return {"sessoes": sessions, "respostas": answers}

    def results_csv(self) -> bytes:
        data = self.results()
        by_id = {s["id"]: s for s in data["sessoes"]}
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\r\n")
        writer.writerow(["roteiro", "versao_roteiro", "testador", "caso_id", "caso_titulo", "resultado", "mensagem_erro", "comentario", "respondida_em"])
        for a in data["respostas"]:
            s = by_id[a["sessao_id"]]
            cells = [s["roteiro"], s["versao_roteiro"], s["testador"], a["caso_id"], a["caso_titulo"], a["resultado"], a["mensagem_erro"], a["comentario"], a["respondida_em"]]
            writer.writerow(["'" + c if isinstance(c, str) and c.startswith(FORMULA_PREFIXES) else c for c in cells])
        return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "RoteiroDeTestes"

        def log_message(self, fmt: str, *args: Any) -> None:  # sem IP/corpo nos logs
            print(f"[roteiro-de-testes] {self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}", flush=True)

        def _send(self, status: int, body: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload: Any) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError(413, "Corpo grande demais")
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except ValueError as exc:
                raise ApiError(400, "JSON inválido") from exc
            if not isinstance(data, dict):
                raise ApiError(400, "Esperava um objeto JSON")
            return data

        def _route(self, method: str) -> None:
            url = urlparse(self.path)
            path = unquote(url.path)
            if method == "GET" and path in STATIC_FILES:
                name = STATIC_FILES[path]
                self._send(200, (STATIC_DIR / name).read_bytes(), CONTENT_TYPES[Path(name).suffix])
                return
            if not path.startswith("/api/"):
                raise ApiError(404, "Não encontrado")
            parts = path[5:].strip("/").split("/")
            if method == "GET" and parts == ["roteiros"]:
                self._json(200, app.list_roteiros())
            elif method == "POST" and parts == ["sessoes"]:
                self._json(200, app.start(self._body()))
            elif method == "GET" and len(parts) == 2 and parts[0] == "sessoes" and parts[1].isdigit():
                self._json(200, app.session(int(parts[1])))
            elif method == "PUT" and len(parts) == 4 and parts[0] == "sessoes" and parts[1].isdigit() and parts[2] == "respostas":
                self._json(200, app.answer(int(parts[1]), parts[3], self._body()))
            elif method == "POST" and len(parts) == 3 and parts[0] == "sessoes" and parts[1].isdigit() and parts[2] == "finalizar":
                self._json(200, app.finish(int(parts[1])))
            elif method == "GET" and parts in (["resultados"], ["resultados.csv"]):
                if parts == ["resultados"]:
                    self._json(200, app.results())
                else:
                    self._send(200, app.results_csv(), "text/csv; charset=utf-8", {"Content-Disposition": 'attachment; filename="resultados.csv"'})
            else:
                raise ApiError(404, "Não encontrado")

        def _handle(self, method: str) -> None:
            try:
                self._route(method)
            except ApiError as exc:
                self._json(exc.status, {"detail": exc.message})
            except Exception as exc:  # noqa: BLE001 - nunca derruba o servidor nem vaza detalhes
                print(f"[roteiro-de-testes] erro interno: {type(exc).__name__}: {exc}", flush=True)
                self._json(500, {"detail": "Erro interno"})

        def do_GET(self) -> None:  # noqa: N802
            self._handle("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._handle("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._handle("PUT")

    return Handler


def create_server(host: str, port: int, db_path: str, casos_dir: str) -> ThreadingHTTPServer:
    app = App(Store(db_path), Roteiros(casos_dir))
    return ThreadingHTTPServer((host, port), make_handler(app))


def main() -> None:
    server = create_server(
        os.environ.get("HOST", "0.0.0.0"),  # noqa: S104 - o contêiner precisa escutar; quem publica a porta decide o acesso
        int(os.environ.get("PORT", "8000")),
        os.environ.get("DB_PATH", "/data/roteiro.db"),
        os.environ.get("CASOS_DIR", "/casos"),
    )
    print(f"[roteiro-de-testes] no ar em :{server.server_address[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
