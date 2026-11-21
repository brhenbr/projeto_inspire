import csv
import io
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from inspire.curation import collections, service
from inspire.discovery.search import Filters
from inspire.export import service as export
from inspire.quality.matrix import render_markdown

pytestmark = pytest.mark.integration


def parse_csv(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def test_csv_traz_original_curado_e_status(api: TestClient, populated: Engine) -> None:
    service.apply_changes(
        populated, "ds-0001", {"titulo": "Título curado para exportação"}, author="ana"
    )

    r = api.get("/v1/exportacao/conjuntos", params={"saida": "csv"})

    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert (
        "attachment" in r.headers["content-disposition"]
        and ".csv" in r.headers["content-disposition"]
    )
    rows = {x["id"]: x for x in parse_csv(r.content)}
    assert len(rows) == 61
    assert (
        rows["ds-0001"]["titulo"] == "Título curado para exportação"
        and rows["ds-0001"]["titulo_original"] == "Conjunto ds-0001"
    )
    assert (
        rows["ds-0001"]["curado"] == "True" and rows["ds-0001"]["estado_curadoria"] == "em_revisao"
    )
    assert rows["ds-0002"]["curado"] == "False" and float(rows["ds-0002"]["nota_qualidade"]) >= 0
    assert "|" in rows["ds-0002"]["tags"] and rows["ds-0002"]["link_portal"].endswith(
        "conjunto-ds-0002"
    )


def test_csv_tem_bom_para_o_excel_e_acentos(api: TestClient) -> None:
    r = api.get("/v1/exportacao/conjuntos", params={"q": "saude populacao"})

    assert r.content.startswith(
        b"\xef\xbb\xbf"
    ) and "Saúde da População Brasileira" in r.content.decode("utf-8")


def test_exportacao_respeita_filtros(api: TestClient) -> None:
    todos = len(parse_csv(api.get("/v1/exportacao/conjuntos").content))
    org = parse_csv(api.get("/v1/exportacao/conjuntos", params={"organizacao": "orgao-1"}).content)

    assert 0 < len(org) < todos and {x["organizacao_slug"] for x in org} == {"orgao-1"}


def test_json_e_lista_de_objetos_com_arrays(api: TestClient) -> None:
    r = api.get("/v1/exportacao/conjuntos", params={"saida": "json"})

    data = r.json()
    assert r.headers["content-type"] == "application/json" and len(data) == 61
    assert isinstance(data[0]["tags"], list) and isinstance(data[0]["curado"], bool)
    assert set(data[0]) == set(export.FIELDS)


def test_json_vazio_continua_valido(api: TestClient) -> None:
    assert (
        api.get("/v1/exportacao/conjuntos", params={"saida": "json", "q": "xyzzyqwerty"}).json()
        == []
    )


def test_exportar_colecao(api: TestClient, populated: Engine) -> None:
    cid = collections.create(populated, "Para exportar", kind="manual")
    collections.add_items(populated, cid, ["ds-0001", "ds-saude"])

    rows = parse_csv(api.get(f"/v1/exportacao/colecoes/{cid}").content)

    assert {x["id"] for x in rows} == {"ds-0001", "ds-saude"}
    assert api.get("/v1/exportacao/colecoes/999").status_code == 404


def test_saida_nao_confunde_com_o_filtro_de_formato_do_recurso(api: TestClient) -> None:
    """Regressão: 'formato=json' (saída) filtrava os conjuntos por recurso JSON e perdia 20 de 61."""
    todos = len(api.get("/v1/exportacao/conjuntos", params={"saida": "json"}).json())
    so_csv = api.get("/v1/exportacao/conjuntos", params={"saida": "json", "formato": "CSV"}).json()

    assert todos == 61 and 0 < len(so_csv) < 61
    assert (
        len(parse_csv(api.get("/v1/exportacao/conjuntos", params={"saida": "csv"}).content)) == 61
    )


def test_saida_invalida_e_recusada(api: TestClient) -> None:
    assert api.get("/v1/exportacao/conjuntos", params={"saida": "xml"}).status_code == 422


def test_celulas_que_parecem_formula_sao_neutralizadas(populated: Engine) -> None:
    service.apply_changes(
        populated, "ds-0001", {"titulo": '=HYPERLINK("http://mal.com","clique")'}, author="ana"
    )
    service.apply_changes(populated, "ds-0002", {"titulo": "+cmd|' /C calc'!A0"}, author="ana")
    service.apply_changes(populated, "ds-0003", {"titulo": "@SUM(1+1)"}, author="ana")

    rows = {
        x["id"]: x for x in parse_csv(b"".join(export.to_csv(export.rows(populated, Filters()))))
    }

    for ident in ("ds-0001", "ds-0002", "ds-0003"):
        assert rows[ident]["titulo"].startswith("'")


def test_exportacao_nunca_traz_contatos(api: TestClient) -> None:
    corpo = (
        api.get("/v1/exportacao/conjuntos").text
        + api.get("/v1/exportacao/conjuntos", params={"saida": "json"}).text
    )

    assert "@orgao-" not in corpo and "Responsável " not in corpo


def test_valor_seguro_para_tipos_variados() -> None:
    assert (
        export._safe(None) == ""
        and export._safe(["a", "b"]) == "a | b"
        and export._safe(12.5) == "12.5"
    )
    assert export._safe("normal") == "normal" and export._safe("-5") == "'-5"


def test_matriz_de_qualidade_lista_todas_as_regras_e_dimensoes() -> None:
    from inspire.quality.rules import RULES

    md = render_markdown()

    assert all(r.key in md for r in RULES)
    assert {"Completude", "Atualidade", "Acessibilidade", "Processabilidade"} <= {
        r.dimension for r in RULES
    }
    assert "Gerado por" in md and "ADR-0009" in md and json.dumps("DCAT-BR")
