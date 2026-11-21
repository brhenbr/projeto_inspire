import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from inspire.analytics.read_model import refresh_read_model
from inspire.discovery.search import Filters, SearchService
from inspire.quality import service as quality
from support.helpers import scalar

pytestmark = pytest.mark.integration


def test_modelo_de_leitura_tem_uma_linha_por_conjunto(populated: Engine) -> None:
    assert scalar(populated, "SELECT count(*) FROM analitico.conjunto_busca") == 61
    assert (
        scalar(
            populated,
            "SELECT count(*) FROM analitico.conjunto_busca WHERE nota_qualidade IS NOT NULL",
        )
        == 61
    )


def test_busca_ignora_acentos_e_variacoes(populated: Engine) -> None:
    s = SearchService(populated)

    for query in (
        "saude populacao",
        "Saúde População",
        "SAUDE da populacao brasileira",
        "populações",
    ):
        found = s.search(Filters(q=query))
        assert found["total"] >= 1, query
        assert found["itens"][0]["id"] == "ds-saude", query
        assert found["aproximada"] is False


def test_busca_acha_pelo_conteudo_da_descricao(populated: Engine) -> None:
    found = SearchService(populated).search(Filters(q="mortalidade hospitalar"))

    assert [i["id"] for i in found["itens"]] == ["ds-saude"]


def test_titulo_pesa_mais_que_a_descricao(populated: Engine) -> None:
    with populated.begin() as conn:
        from sqlalchemy import text

        conn.execute(
            text(
                "UPDATE catalogo.conjunto SET descricao = 'população brasileira saúde' WHERE id = 'ds-0001'"
            )
        )
    refresh_read_model(populated, ["ds-0001"])

    found = SearchService(populated).search(Filters(q="saúde população"))

    assert found["itens"][0]["id"] == "ds-saude"


def test_erro_de_digitacao_cai_na_busca_aproximada(populated: Engine) -> None:
    found = SearchService(populated).search(Filters(q="Saude da Populacoa Brasileria"))

    assert found["aproximada"] is True
    assert found["itens"][0]["id"] == "ds-saude"


def test_busca_sem_resultado_devolve_lista_vazia(populated: Engine) -> None:
    found = SearchService(populated).search(Filters(q="xyzzyqwerty"))

    assert found["total"] == 0 and found["itens"] == []


def test_sem_texto_lista_tudo_paginado(populated: Engine) -> None:
    s = SearchService(populated)

    p1 = s.search(Filters(), page=1, size=25)
    p3 = s.search(Filters(), page=3, size=25)

    assert p1["total"] == 61 and len(p1["itens"]) == 25 and len(p3["itens"]) == 11
    assert not {i["id"] for i in p1["itens"]} & {i["id"] for i in p3["itens"]}


def test_filtros_combinam(populated: Engine) -> None:
    s = SearchService(populated)
    org = s.search(Filters(organizacao="orgao-1"))["total"]
    org_csv = s.search(Filters(organizacao="orgao-1", formato="csv"))["total"]
    org_tema = s.search(Filters(organizacao="orgao-1", tema="saude"))["total"]

    assert 0 < org_csv <= org and 0 < org_tema <= org
    assert s.search(Filters(esfera="federal"))["total"] == 61
    assert s.search(Filters(esfera="municipal"))["total"] == 0
    assert s.search(Filters(tag="Tag 1", organizacao="orgao-2"))["total"] >= 0


def test_facetas_contam_sem_o_proprio_filtro(populated: Engine) -> None:
    f = SearchService(populated).search(Filters(organizacao="orgao-1"))

    orgs = {x["valor"]: x["n"] for x in f["facetas"]["organizacao"]}
    assert set(orgs) == {
        "orgao-1",
        "orgao-2",
        "orgao-3",
    }  # a faceta de organização ignora o filtro de organização
    assert sum(x["n"] for x in f["facetas"]["esfera"]) == f["total"]  # as outras respeitam
    assert f["facetas"]["organizacao"][0]["rotulo"].startswith("Órgão")


def test_ordenacao_por_nota_e_por_titulo(populated: Engine) -> None:
    s = SearchService(populated)

    by_score = [i["nota_qualidade"] for i in s.search(Filters(), size=100, sort="nota")["itens"]]
    by_title = [i["titulo"] for i in s.search(Filters(), size=100, sort="titulo")["itens"]]

    assert by_score == sorted(by_score, reverse=True)
    assert by_title == sorted(by_title)


def test_filtro_por_faixa_de_nota(populated: Engine) -> None:
    s = SearchService(populated)
    alta = s.search(Filters(nota_min=70))
    assert all(i["nota_qualidade"] >= 70 for i in alta["itens"])
    assert alta["total"] + s.search(Filters(nota_max=69.9))["total"] == 61


def test_removidos_ficam_fora_por_padrao(populated: Engine) -> None:
    from sqlalchemy import text

    with populated.begin() as conn:
        conn.execute(text("UPDATE catalogo.conjunto SET removido_em = now() WHERE id = 'ds-0001'"))
    refresh_read_model(populated, ["ds-0001"])
    s = SearchService(populated)

    assert s.search(Filters())["total"] == 60
    assert s.search(Filters(incluir_removidos=True))["total"] == 61


def test_busca_resiste_a_texto_malicioso(populated: Engine) -> None:
    s = SearchService(populated)

    for q in (
        "'; DROP TABLE analitico.conjunto_busca; --",
        "a' OR '1'='1",
        '"""',
        "& | ! ( )",
        "%%%___",
    ):
        s.search(Filters(q=q))
    assert scalar(populated, "SELECT count(*) FROM analitico.conjunto_busca") == 61


# ----------------------------------------------------------------- API


def test_api_busca_com_filtros_e_facetas(api: TestClient) -> None:
    r = api.get("/v1/conjuntos", params={"q": "saude", "organizacao": "orgao-1", "tamanho": 5})

    assert r.status_code == 200
    body = r.json()
    assert body["itens"][0]["id"] == "ds-saude" and "facetas" in body and body["tamanho"] == 5


def test_api_ordem_invalida_e_422(api: TestClient) -> None:
    assert api.get("/v1/conjuntos", params={"ordem": "aleatoria"}).status_code == 422


def test_api_detalhe_do_conjunto(api: TestClient) -> None:
    r = api.get("/v1/conjuntos/ds-saude")

    assert r.status_code == 200
    d = r.json()
    assert d["efetivo"]["titulo"] == "Saúde da População Brasileira"
    assert (
        d["organizacao"]["titulo"].startswith("Órgão") and d["organizacao"]["esfera"] == "federal"
    )
    assert len(d["recursos"]) == 2 and d["qualidade"]["nota"] >= 0 and d["qualidade"]["detalhes"]
    assert d["link_portal"].endswith("/conjuntos-dados/conjunto-ds-saude")
    assert d["historico"][0]["evento"] == "novo"
    assert api.get("/v1/conjuntos/nao-existe").status_code == 404


def test_api_nunca_expoe_contatos_pessoais(api: TestClient) -> None:
    corpo = (
        api.get("/v1/conjuntos/ds-0004").text
        + api.get("/v1/conjuntos", params={"tamanho": 100}).text
    )

    assert (
        "@orgao-" not in corpo and "Responsável " not in corpo and "emailResponsavel" not in corpo
    )


def test_api_organizacoes(api: TestClient) -> None:
    lista = api.get("/v1/organizacoes").json()
    assert lista["total"] == 3 and sum(o["conjuntos"] for o in lista["itens"]) == 61

    d = api.get("/v1/organizacoes/orgao-1").json()
    assert d["resumo"]["conjuntos"] > 0 and d["regras_que_mais_falham"] and d["dimensoes"]
    assert api.get("/v1/organizacoes/xx").status_code == 404
    assert api.get("/v1/organizacoes", params={"q": "orgao-2"}).json()["total"] == 1


def test_api_painel(api: TestClient) -> None:
    p = api.get("/v1/painel").json()

    assert p["totais"]["conjuntos"] == 61 and p["totais"]["organizacoes"] == 3
    assert sum(x["n"] for x in p["qualidade_faixas"]) == 61 and len(p["qualidade_faixas"]) == 5
    assert p["ultima_extracao"]["estado"] == "concluida"
    assert {x["valor"] for x in p["por_formato"]} >= {"CSV", "JSON", "PDF"}


def test_api_regras_de_qualidade_sao_editaveis_e_recalculam(
    api: TestClient, populated: Engine
) -> None:
    regras = api.get("/v1/qualidade/regras").json()
    assert len(regras) >= 15 and all(r["fonte"] for r in regras)
    antes = scalar(populated, "SELECT round(avg(nota), 2) FROM analitico.qualidade_conjunto")

    assert api.put("/v1/qualidade/regras/COMP-02", json={"ativa": False}).json()["ativa"] is False
    assert api.put("/v1/qualidade/regras/NAO-EXISTE", json={"peso": 1}).status_code == 404
    assert api.post("/v1/qualidade/recalcular").status_code == 202

    estado = api.get("/v1/qualidade/recalculo").json()
    assert estado["em_andamento"] is False and estado["pontuados"] == 61
    assert (
        scalar(populated, "SELECT round(avg(nota), 2) FROM analitico.qualidade_conjunto") != antes
    )


def test_api_peso_invalido_e_recusado(api: TestClient) -> None:
    assert api.put("/v1/qualidade/regras/COMP-02", json={"peso": -1}).status_code == 422


def test_recalculo_guarda_historico_so_quando_a_nota_muda(populated: Engine) -> None:
    antes = scalar(populated, "SELECT count(*) FROM analitico.qualidade_historico")
    quality.recompute(populated)  # nada mudou
    assert scalar(populated, "SELECT count(*) FROM analitico.qualidade_historico") == antes


def test_api_temas(api: TestClient) -> None:
    temas = api.get("/v1/temas").json()

    assert {t["slug"] for t in temas} == {"saude", "educacao", "trabalho"}
    assert sum(t["conjuntos"] for t in temas) == 61
