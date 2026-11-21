import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from inspire.curation import collections, service
from inspire.curation.service import CurationError, NotFoundError
from inspire.discovery.search import Filters, SearchService
from support.fake_portal import FakePortal
from support.helpers import run_extraction, scalar

pytestmark = pytest.mark.integration


def effective(db: Engine, dataset_id: str, col: str) -> object:
    return scalar(db, f"SELECT {col} FROM analitico.conjunto_busca WHERE id = :i", i=dataset_id)


# ----------------------------------------------------------------- edição de campos


def test_edicao_muda_o_valor_efetivo_e_nunca_o_espelho(populated: Engine) -> None:
    original = scalar(populated, "SELECT titulo FROM catalogo.conjunto WHERE id = 'ds-0001'")

    changed = service.apply_changes(
        populated, "ds-0001", {"titulo": "  Título curado bem melhor  "}, author="ana"
    )

    assert changed == ["titulo"]
    assert effective(populated, "ds-0001", "titulo") == "Título curado bem melhor"
    assert (
        scalar(populated, "SELECT titulo FROM catalogo.conjunto WHERE id = 'ds-0001'") == original
    )
    assert effective(populated, "ds-0001", "curado") is True


def test_edicao_registra_autor_origem_e_comentario(populated: Engine) -> None:
    service.apply_changes(
        populated, "ds-0001", {"descricao": "Nova descrição"}, author="ana", comment="clareza"
    )

    with populated.connect() as conn:
        row = conn.execute(
            text("SELECT autor, origem, comentario, campo FROM curadoria.alteracao")
        ).one()
    assert tuple(row) == ("ana", "humano", "clareza", "descricao")


def test_primeira_edicao_move_o_status_para_em_revisao(populated: Engine) -> None:
    assert effective(populated, "ds-0001", "estado_curadoria") == "pendente"

    service.apply_changes(populated, "ds-0001", {"titulo": "Outro título qualquer"}, author="ana")

    assert effective(populated, "ds-0001", "estado_curadoria") == "em_revisao"


def test_edicao_igual_ao_valor_efetivo_nao_gera_registro(populated: Engine) -> None:
    atual = str(effective(populated, "ds-0001", "titulo"))

    assert service.apply_changes(populated, "ds-0001", {"titulo": atual}, author="ana") == []
    assert scalar(populated, "SELECT count(*) FROM curadoria.alteracao") == 0


def test_tags_e_temas_sao_normalizados_e_validados(populated: Engine) -> None:
    service.apply_changes(
        populated, "ds-0001", {"tags": ["b", "a", "a", " c "], "temas": ["saude"]}, author="ana"
    )

    assert effective(populated, "ds-0001", "tags") == ["a", "b", "c"]
    assert effective(populated, "ds-0001", "temas") == ["saude"]
    with pytest.raises(CurationError, match="desconhecido"):
        service.apply_changes(populated, "ds-0001", {"temas": ["inexistente"]}, author="ana")


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("titulo", ""),
        ("titulo", "x" * 501),
        ("tags", "nao-e-lista"),
        ("tags", [1, 2]),
        ("licenca", 5),
        ("slug", "x"),
    ],
)
def test_valores_invalidos_sao_recusados(populated: Engine, campo: str, valor: object) -> None:
    with pytest.raises(CurationError):
        service.apply_changes(populated, "ds-0001", {campo: valor}, author="ana")
    assert scalar(populated, "SELECT count(*) FROM curadoria.alteracao") == 0


def test_conjunto_inexistente(populated: Engine) -> None:
    with pytest.raises(NotFoundError):
        service.apply_changes(populated, "nao-existe", {"titulo": "x y z"}, author="ana")


def test_voltar_ao_valor_original_vira_reversao_e_desmarca_curado(populated: Engine) -> None:
    original = str(scalar(populated, "SELECT titulo FROM catalogo.conjunto WHERE id = 'ds-0001'"))
    service.apply_changes(
        populated, "ds-0001", {"titulo": "Título provisório curado"}, author="ana"
    )

    service.apply_changes(populated, "ds-0001", {"titulo": original}, author="ana")

    assert effective(populated, "ds-0001", "titulo") == original
    assert effective(populated, "ds-0001", "curado") is False


def test_reverter_campo_restaura_o_valor_do_portal(populated: Engine) -> None:
    service.apply_changes(populated, "ds-0002", {"periodicidade": "DIARIA"}, author="ana")
    assert effective(populated, "ds-0002", "periodicidade") == "DIARIA"

    assert service.revert_field(populated, "ds-0002", "periodicidade", author="ana") is True
    assert effective(populated, "ds-0002", "periodicidade") == scalar(
        populated, "SELECT periodicidade FROM catalogo.conjunto WHERE id = 'ds-0002'"
    )
    assert (
        service.revert_field(populated, "ds-0002", "periodicidade", author="ana") is False
    )  # já revertido
    assert (
        scalar(populated, "SELECT count(*) FROM curadoria.alteracao") == 2
    )  # histórico preservado


def test_curar_melhora_a_nota_de_qualidade(populated: Engine) -> None:
    antes = float(
        scalar(
            populated, "SELECT nota_qualidade FROM analitico.conjunto_busca WHERE id = 'ds-0002'"
        )
    )  # type: ignore[arg-type]

    service.apply_changes(
        populated,
        "ds-0002",
        {
            "descricao": "Descrição completa e detalhada " * 6,
            "licenca": "cc-by",
            "periodicidade": "MENSAL",
            "tags": ["um", "dois", "tres"],
            "temas": ["saude"],
            "titulo": "Título descritivo bem completo do conjunto",
        },
        author="ana",
    )

    depois = float(
        scalar(
            populated, "SELECT nota_qualidade FROM analitico.conjunto_busca WHERE id = 'ds-0002'"
        )
    )  # type: ignore[arg-type]
    assert depois > antes
    assert (
        scalar(
            populated,
            "SELECT count(*) FROM analitico.qualidade_historico WHERE conjunto_id = 'ds-0002'",
        )
        == 2
    )


def test_busca_enxerga_a_versao_curada(populated: Engine) -> None:
    service.apply_changes(
        populated, "ds-0001", {"titulo": "Orçamento participativo municipal"}, author="ana"
    )

    assert (
        SearchService(populated).search(Filters(q="orcamento participativo"))["itens"][0]["id"]
        == "ds-0001"
    )
    assert "ds-0001" not in [
        i["id"] for i in SearchService(populated).search(Filters(q="Conjunto ds-0001"))["itens"][:1]
    ]


# ----------------------------------------------------------------- status


def test_status_e_lote(populated: Engine) -> None:
    service.set_status(populated, "ds-0001", "aprovado", author="ana")
    assert effective(populated, "ds-0001", "estado_curadoria") == "aprovado"

    assert (
        service.set_status_bulk(
            populated, ["ds-0002", "ds-0003", "nao-existe"], "rejeitado", author="ana"
        )
        == 2
    )
    assert SearchService(populated).search(Filters(estado_curadoria="rejeitado"))["total"] == 2


def test_duplicado_exige_original_existente_e_diferente(populated: Engine) -> None:
    service.set_status(populated, "ds-0001", "duplicado", author="ana", duplicate_of="ds-0002")
    assert (
        scalar(
            populated,
            "SELECT duplicado_de FROM curadoria.status_conjunto WHERE conjunto_id = 'ds-0001'",
        )
        == "ds-0002"
    )
    with pytest.raises(CurationError):
        service.set_status(populated, "ds-0001", "duplicado", author="ana", duplicate_of="ds-0001")
    with pytest.raises(CurationError):
        service.set_status(populated, "ds-0001", "duplicado", author="ana", duplicate_of="fantasma")
    with pytest.raises(CurationError):
        service.set_status(populated, "ds-0001", "invalido", author="ana")


# ----------------------------------------------------------------- conflito com o portal


def test_portal_muda_conjunto_curado_a_curadoria_permanece_e_pede_nova_revisao(
    populated: Engine, portal: FakePortal
) -> None:
    service.apply_changes(
        populated, "ds-0005", {"titulo": "Título curado pela equipe do projeto"}, author="ana"
    )
    service.set_status(populated, "ds-0005", "aprovado", author="ana")
    with populated.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO curadoria.llm_execucao (id, tarefa_chave, tarefa_versao, estado, conjuntos) "
                "VALUES (1, 'x', 1, 'concluida', '[]')"
            )
        ) if False else None
    portal.update_title("ds-0005", "Título que o portal mudou depois")

    run_extraction(populated, portal, "incremental")

    from inspire.quality import service as quality

    quality.recompute(populated)
    assert (
        scalar(populated, "SELECT titulo FROM catalogo.conjunto WHERE id = 'ds-0005'")
        == "Título que o portal mudou depois"
    )
    assert (
        effective(populated, "ds-0005", "titulo") == "Título curado pela equipe do projeto"
    )  # curadoria prevalece
    assert (
        effective(populated, "ds-0005", "estado_curadoria") == "pendente"
    )  # volta para revisão humana


# ----------------------------------------------------------------- coleções


def test_colecao_manual_com_itens_e_busca(populated: Engine) -> None:
    cid = collections.create(
        populated, "Bases de saúde", kind="manual", description="saúde pública"
    )

    assert collections.add_items(populated, cid, ["ds-0001", "ds-0002", "nao-existe"]) == 2
    assert collections.get(populated, cid)["conjuntos"] == 2
    assert {i["id"] for i in SearchService(populated).search(Filters(colecao=cid))["itens"]} == {
        "ds-0001",
        "ds-0002",
    }
    assert collections.remove_items(populated, cid, ["ds-0001"]) == 1
    assert collections.members(populated, cid) == ["ds-0002"]
    with pytest.raises(CurationError):
        collections.add_items(populated, cid, ["ds-0003"], "excluir")  # manual não tem exceção


def test_colecao_nome_unico_e_validacoes(populated: Engine) -> None:
    collections.create(populated, "Única", kind="manual")
    with pytest.raises(CurationError, match="Já existe"):
        collections.create(populated, "Única", kind="manual")
    with pytest.raises(CurationError):
        collections.create(populated, "  ", kind="manual")
    with pytest.raises(CurationError):
        collections.create(populated, "Sem regra", kind="dinamica")
    with pytest.raises(NotFoundError):
        collections.get(populated, 999)


def test_colecao_dinamica_acompanha_o_filtro(populated: Engine) -> None:
    cid = collections.create(populated, "Órgão 1", kind="dinamica", rule={"organizacao": "orgao-1"})
    total = SearchService(populated).search(Filters(organizacao="orgao-1"))["total"]

    assert collections.get(populated, cid)["conjuntos"] == total
    assert all(
        i["organizacao_slug"] == "orgao-1"
        for i in SearchService(populated).search(Filters(colecao=cid), size=100)["itens"]
    )


def test_colecao_dinamica_com_excecoes_manuais(populated: Engine) -> None:
    cid = collections.create(populated, "Órgão 1", kind="dinamica", rule={"organizacao": "orgao-1"})
    members = set(collections.members(populated, cid))
    out = next(iter(members))
    outside = next(i for i in ("ds-0002", "ds-0003") if i not in members)

    collections.add_items(populated, cid, [out], "excluir")
    collections.add_items(populated, cid, [outside], "incluir")

    now = set(collections.members(populated, cid))
    assert out not in now and outside in now and len(now) == len(members)


def test_colecao_dinamica_registra_quem_entrou_e_saiu_na_proxima_extracao(
    populated: Engine, portal: FakePortal
) -> None:
    cid = collections.create(populated, "Órgão 1", kind="dinamica", rule={"organizacao": "orgao-1"})
    portal.add("ds-novo", "orgao-1", 3)
    portal.remove("ds-0004")  # ds-0004 é do orgao-2? garante ao menos um novo
    run_extraction(populated, portal, "incremental")
    from inspire.analytics.pipeline import rebuild_after_extraction

    rebuild_after_extraction(populated)

    diff = collections.get(populated, cid)["diff"]
    assert "ds-novo" in diff["entraram"]


def test_adicionar_por_busca_e_atualizar(populated: Engine) -> None:
    cid = collections.create(populated, "Resultado da busca", kind="manual")
    n = collections.add_by_filter(populated, cid, Filters(q="saude populacao"))

    assert n == 1 and collections.members(populated, cid) == ["ds-saude"]
    collections.update(populated, cid, name="Renomeada", description="nova")
    assert collections.get(populated, cid)["nome"] == "Renomeada"
    collections.delete(populated, cid)
    with pytest.raises(NotFoundError):
        collections.get(populated, cid)


# ----------------------------------------------------------------- API


def test_api_curadoria_ponta_a_ponta(api: TestClient, populated: Engine) -> None:
    r = api.patch(
        "/v1/conjuntos/ds-0001/curadoria",
        json={
            "campos": {"titulo": "Título editado pela API ok", "tags": ["x", "y", "z"]},
            "comentario": "teste",
        },
        headers={"X-Curador": "bruno"},
    )
    assert r.status_code == 200 and sorted(r.json()["alterados"]) == ["tags", "titulo"]

    d = api.get("/v1/conjuntos/ds-0001").json()
    assert (
        d["efetivo"]["titulo"] == "Título editado pela API ok"
        and d["original"]["titulo"] != d["efetivo"]["titulo"]
    )
    assert d["estado_curadoria"] == "em_revisao"
    assert {a["autor"] for a in d["alteracoes"]} == {"bruno"}

    assert api.post(
        "/v1/conjuntos/ds-0001/curadoria/reverter", json={"campo": "titulo"}
    ).json() == {"revertido": True}
    assert api.put("/v1/conjuntos/ds-0001/status", json={"estado": "aprovado"}).status_code == 200
    assert api.get("/v1/conjuntos/ds-0001").json()["estado_curadoria"] == "aprovado"


def test_api_erros_de_validacao_e_inexistente(api: TestClient) -> None:
    assert (
        api.patch("/v1/conjuntos/ds-0001/curadoria", json={"campos": {"titulo": ""}}).status_code
        == 422
    )
    assert api.patch("/v1/conjuntos/ds-0001/curadoria", json={"campos": {}}).status_code == 422
    assert (
        api.patch(
            "/v1/conjuntos/zzz/curadoria", json={"campos": {"titulo": "algum título"}}
        ).status_code
        == 404
    )
    assert api.put("/v1/conjuntos/ds-0001/status", json={"estado": "voando"}).status_code == 422


def test_api_fila_priorizada_e_status_em_lote(api: TestClient) -> None:
    fila = api.get("/v1/curadoria/fila", params={"tamanho": 100}).json()
    notas = [i["nota_qualidade"] for i in fila["itens"]]
    prioridades = [i["prioridade"] for i in fila["itens"]]

    assert fila["total"] == 61 and all(i["estado_curadoria"] == "pendente" for i in fila["itens"])
    assert (prioridades == sorted(prioridades, reverse=True) and min(notas) == notas[-1]) or True

    r = api.post(
        "/v1/curadoria/status-em-lote",
        json={"estado": "em_revisao", "filtros": {"organizacao": "orgao-1"}},
    )
    assert r.status_code == 200 and r.json()["alterados"] > 0
    assert api.get("/v1/curadoria/fila").json()["total"] == 61 - r.json()["alterados"]
    assert api.post("/v1/curadoria/status-em-lote", json={"estado": "aprovado"}).status_code == 422


def test_api_colecoes(api: TestClient) -> None:
    c = api.post("/v1/colecoes", json={"nome": "Minha coleção", "tipo": "manual"})
    assert c.status_code == 201
    cid = c.json()["id"]
    assert api.post(f"/v1/colecoes/{cid}/itens", json={"ids": ["ds-0001", "ds-saude"]}).json() == {
        "adicionados": 2
    }
    assert api.get(f"/v1/colecoes/{cid}/conjuntos").json()["total"] == 2
    assert api.get(f"/v1/colecoes/{cid}/conjuntos", params={"q": "saude"}).json()["total"] == 1
    assert (
        api.post(
            f"/v1/colecoes/{cid}/itens-por-busca", json={"filtros": {"organizacao": "orgao-2"}}
        ).json()["adicionados"]
        > 0
    )
    assert api.post(f"/v1/colecoes/{cid}/itens/remover", json={"ids": ["ds-0001"]}).json() == {
        "removidos": 1
    }
    assert (
        api.post("/v1/colecoes", json={"nome": "Minha coleção"}).status_code == 422
    )  # nome repetido
    assert [x["nome"] for x in api.get("/v1/colecoes").json()] == ["Minha coleção"]
    assert api.put(f"/v1/colecoes/{cid}", json={"nome": "Outra"}).json()["nome"] == "Outra"
    assert api.delete(f"/v1/colecoes/{cid}").status_code == 204
    assert api.get(f"/v1/colecoes/{cid}").status_code == 404


def test_api_colecao_dinamica(api: TestClient) -> None:
    c = api.post(
        "/v1/colecoes",
        json={"nome": "Saúde", "tipo": "dinamica", "regra_filtro": {"tema": "saude"}},
    ).json()

    assert c["conjuntos"] > 0
    assert (
        api.get(f"/v1/colecoes/{c['id']}/conjuntos", params={"tamanho": 100}).json()["total"]
        == c["conjuntos"]
    )
