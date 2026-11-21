"""Curadoria assistida por LLM: tarefas, execuções, propostas e decisão humana (ADR-0004, ADR-0011)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import Engine, text

from inspire.api.deps import get_db
from inspire.api.routes.curadoria import Author
from inspire.config import Settings, get_settings
from inspire.curation.service import CurationError
from inspire.discovery.search import Filters, SearchService
from inspire.llm import providers, service, tasks

router = APIRouter(prefix="/llm", tags=["llm"])
Db = Annotated[Engine, Depends(get_db)]
Cfg = Annotated[Settings, Depends(get_settings)]


class ExecucaoPedido(BaseModel):
    tarefa: str
    ids: list[str] | None = None
    filtros: dict[str, Any] | None = None
    instrucoes: str | None = Field(default=None, max_length=tasks.MAX_INSTRUCTIONS)


class DecisaoPedido(BaseModel):
    decisao: str
    valor: Any = None


class LotePedido(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=1000)
    decisao: str


@router.get("/estado")
def estado(cfg: Cfg) -> dict[str, Any]:
    """Estado do recurso, para a tela mostrar o aviso de provedor externo ou de modo simulado."""
    return {**providers.describe(cfg), "limite_por_execucao": service.MAX_DATASETS_PER_RUN}


@router.get("/tarefas")
def tarefas(db: Db) -> list[dict[str, Any]]:
    tasks.seed_tasks(db)
    return [
        {
            "chave": t.chave,
            "nome": t.nome,
            "descricao": t.descricao,
            "campo_alvo": t.campo_alvo,
            "versao": t.versao,
        }
        for t in tasks.TASKS
    ]


@router.post("/execucoes", status_code=status.HTTP_202_ACCEPTED)
def criar_execucao(pedido: ExecucaoPedido, db: Db, cfg: Cfg, autor: Author) -> Any:
    if bool(pedido.ids) == bool(pedido.filtros):
        raise CurationError("Informe 'ids' ou 'filtros' (apenas um dos dois)")
    ids = pedido.ids or SearchService(db).ids(
        Filters.from_dict(pedido.filtros or {}), limit=service.MAX_DATASETS_PER_RUN + 1
    )
    try:
        execution_id = service.create_execution(
            db, cfg, pedido.tarefa, ids, instructions=pedido.instrucoes, requested_by=autor
        )
    except providers.LlmDisabledError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except service.ConflictError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    return _execution(db, execution_id)


def _execution(db: Engine, execution_id: int) -> dict[str, Any]:
    with db.connect() as conn:
        row = conn.execute(
            text(
                "SELECT e.id, e.tarefa_chave, e.tarefa_versao, e.estado, jsonb_array_length(e.conjuntos) AS conjuntos, "
                "e.parametros, e.provedor, e.modelo, e.externo, e.solicitada_por, e.criada_em, e.iniciada_em, "
                "e.finalizada_em, e.totais, e.erro, e.cancelar_solicitado AS cancelamento_solicitado, "
                "(SELECT count(*) FROM curadoria.llm_proposta p WHERE p.execucao_id = e.id AND p.estado = 'pendente') AS pendentes "
                "FROM curadoria.llm_execucao e WHERE e.id = :i"
            ),
            {"i": execution_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return dict(row._mapping)


@router.get("/execucoes")
def listar_execucoes(
    db: Db, limite: Annotated[int, Query(ge=1, le=100)] = 20
) -> list[dict[str, Any]]:
    with db.connect() as conn:
        ids = [
            r.id
            for r in conn.execute(
                text("SELECT id FROM curadoria.llm_execucao ORDER BY id DESC LIMIT :n"),
                {"n": limite},
            )
        ]
    return [_execution(db, i) for i in ids]


@router.get("/execucoes/{execucao_id}")
def detalhar_execucao(execucao_id: int, db: Db) -> dict[str, Any]:
    return _execution(db, execucao_id)


@router.post("/execucoes/{execucao_id}/cancelar")
def cancelar_execucao(execucao_id: int, db: Db) -> dict[str, str]:
    result = service.cancel_execution(db, execucao_id)
    if result is None:
        raise HTTPException(status_code=409, detail="A execução não está ativa")
    return {"resultado": result}


@router.get("/propostas")
def listar_propostas(
    db: Db,
    estado: str | None = None,
    execucao_id: int | None = None,
    conjunto_id: str | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """Propostas com o valor original ao lado, para revisão."""
    where, params = ["true"], {}
    for col, key, value in (
        ("p.estado", "estado", estado),
        ("p.execucao_id", "execucao", execucao_id),
        ("p.conjunto_id", "conjunto", conjunto_id),
    ):
        if value is not None:
            where.append(f"{col} = :{key}")
            params[key] = value
    clause = " AND ".join(where)
    with db.connect() as conn:
        total = conn.execute(
            text(f"SELECT count(*) FROM curadoria.llm_proposta p WHERE {clause}"), params
        ).scalar_one()
        rows = conn.execute(
            text(
                "SELECT p.id, p.execucao_id, p.conjunto_id, c.titulo AS conjunto_titulo, p.campo, p.valor_original, "
                "p.valor_proposto, p.valor_final, p.estado, p.erro, p.criada_em, p.decidida_em, p.decidida_por, "
                "e.provedor, e.modelo, e.externo, e.tarefa_chave FROM curadoria.llm_proposta p "
                "JOIN curadoria.llm_execucao e ON e.id = p.execucao_id "
                "LEFT JOIN analitico.conjunto_busca c ON c.id = p.conjunto_id "
                f"WHERE {clause} ORDER BY p.id DESC LIMIT :n OFFSET :o"
            ),
            {**params, "n": tamanho, "o": (pagina - 1) * tamanho},
        ).all()
    return {
        "total": total,
        "pagina": pagina,
        "tamanho": tamanho,
        "itens": [dict(r._mapping) for r in rows],
    }


@router.get("/propostas/{proposta_id}")
def detalhar_proposta(proposta_id: int, db: Db) -> dict[str, Any]:
    """Inclui o prompt completo e a resposta bruta (rastreabilidade exigida pelo GuIA)."""
    with db.connect() as conn:
        row = conn.execute(
            text(
                "SELECT p.*, e.provedor, e.modelo, e.externo, e.tarefa_chave, e.tarefa_versao "
                "FROM curadoria.llm_proposta p JOIN curadoria.llm_execucao e ON e.id = p.execucao_id WHERE p.id = :i"
            ),
            {"i": proposta_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return dict(row._mapping)


@router.post("/propostas/{proposta_id}/decidir")
def decidir(proposta_id: int, pedido: DecisaoPedido, db: Db, autor: Author) -> Any:
    try:
        return service.decide(
            db, proposta_id, pedido.decisao, author=autor, edited_value=pedido.valor
        )
    except service.ConflictError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})


@router.post("/propostas/decidir-em-lote")
def decidir_em_lote(pedido: LotePedido, db: Db, autor: Author) -> dict[str, int]:
    return service.decide_bulk(db, pedido.ids, pedido.decisao, author=autor)
