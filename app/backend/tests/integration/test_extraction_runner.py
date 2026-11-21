import pytest
from sqlalchemy import Engine, text

from inspire.extraction.raw_store import RawStore
from inspire.extraction.runner import ExtractionRunner
from support.fake_portal import FakePortal
from support.helpers import make_client, run_extraction, scalar

pytestmark = pytest.mark.integration


def totals(db: Engine, run_id: int) -> dict:  # type: ignore[type-arg]
    return dict(scalar(db, "SELECT totais FROM raw.execucao WHERE id = :r", r=run_id))  # type: ignore[call-overload]


def test_extracao_completa_espelha_o_catalogo(db: Engine) -> None:
    portal = FakePortal(n_datasets=40, n_orgs=3)

    run_id, state = run_extraction(db, portal)

    assert state == "concluida"
    t = totals(db, run_id)
    assert t["listados"] == 40 and t["esperados"] == 40 and t["cobertura"] == 1.0
    assert t["novos"] == 40 and t["alterados"] == 0 and t["inalterados"] == 0
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto") == 40
    assert scalar(db, "SELECT count(*) FROM catalogo.recurso") == 80
    assert scalar(db, "SELECT count(*) FROM catalogo.organizacao") == 3
    assert scalar(db, "SELECT count(*) FROM catalogo.tema") == 3
    assert (
        scalar(db, "SELECT count(*) FROM catalogo.conjunto_historico WHERE evento = 'novo'") == 40
    )
    assert scalar(db, "SELECT esfera FROM catalogo.organizacao WHERE slug = 'orgao-1'") == "federal"


def test_dados_pessoais_nunca_chegam_ao_banco(db: Engine) -> None:
    run_extraction(db, FakePortal(n_datasets=20))

    assert (
        scalar(db, "SELECT count(*) FROM raw.documento WHERE payload::text ILIKE '%@orgao-%'") == 0
    )
    assert scalar(db, "SELECT count(*) FROM raw.documento WHERE payload ? 'responsavel'") == 0
    assert scalar(db, "SELECT count(*) FROM raw.documento WHERE payload ? 'emailResponsavel'") == 0
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto WHERE tem_responsavel") == 20


def test_normaliza_datas_e_campos_do_portal(db: Engine) -> None:
    run_extraction(db, FakePortal(n_datasets=3, n_orgs=1))

    with db.connect() as conn:
        row = conn.execute(
            text(
                "SELECT metadados_atualizados_em, dados_abertos, periodicidade, licenca FROM catalogo.conjunto WHERE id = 'ds-0001'"
            )
        ).one()
    assert row.metadados_atualizados_em.year == 2024 and row.metadados_atualizados_em.month == 5
    assert row.dados_abertos is True
    assert row.periodicidade == "MENSAL"


def test_segunda_extracao_incremental_sem_mudancas_nao_busca_nenhum_detalhe(db: Engine) -> None:
    portal = FakePortal(n_datasets=40)
    run_extraction(db, portal, "completa")
    details_before = portal.calls["detail"]

    run_id, state = run_extraction(db, portal, "incremental")

    assert state == "concluida"
    assert portal.calls["detail"] == details_before
    t = totals(db, run_id)
    assert t["detalhes_evitados"] == 40
    assert t["novos"] == 0 and t["alterados"] == 0


def test_incremental_busca_so_o_que_mudou(db: Engine) -> None:
    portal = FakePortal(n_datasets=40)
    run_extraction(db, portal, "completa")
    details_before = portal.calls["detail"]
    portal.update_title("ds-0005", "Título novo")
    portal.add("ds-9999", "orgao-1")

    run_id, state = run_extraction(db, portal, "incremental")

    assert state == "concluida"
    assert portal.calls["detail"] - details_before == 2
    t = totals(db, run_id)
    assert t["novos"] == 1 and t["alterados"] == 1
    assert scalar(db, "SELECT titulo FROM catalogo.conjunto WHERE id = 'ds-0005'") == "Título novo"
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto") == 41


def test_extracao_completa_rebusca_tudo_mas_nao_cria_eventos_se_nada_mudou(db: Engine) -> None:
    portal = FakePortal(n_datasets=20)
    run_extraction(db, portal, "completa")

    run_id, _ = run_extraction(db, portal, "completa")

    t = totals(db, run_id)
    assert t["inalterados"] == 20 and t["novos"] == 0 and t["alterados"] == 0
    assert (
        scalar(db, "SELECT count(*) FROM raw.documento WHERE tipo = 'conjunto'") == 20
    )  # sem versões novas


def test_conjunto_que_some_do_portal_e_marcado_como_removido(db: Engine) -> None:
    portal = FakePortal(n_datasets=40)
    run_extraction(db, portal)
    portal.remove("ds-0010")

    run_id, state = run_extraction(db, portal, "incremental")

    assert state == "concluida"
    assert totals(db, run_id)["removidos"] == 1
    assert (
        scalar(db, "SELECT removido_em IS NOT NULL FROM catalogo.conjunto WHERE id = 'ds-0010'")
        is True
    )
    assert (
        scalar(db, "SELECT count(*) FROM catalogo.conjunto_historico WHERE evento = 'removido'")
        == 1
    )


def test_conjunto_removido_que_volta_e_reaparecido(db: Engine) -> None:
    portal = FakePortal(n_datasets=20)
    run_extraction(db, portal)
    removed = dict(portal.datasets["ds-0002"])
    portal.remove("ds-0002")
    run_extraction(db, portal, "incremental")
    portal.datasets["ds-0002"] = removed

    run_id, _ = run_extraction(db, portal, "incremental")

    assert totals(db, run_id)["reaparecidos"] == 1
    assert (
        scalar(db, "SELECT removido_em IS NULL FROM catalogo.conjunto WHERE id = 'ds-0002'") is True
    )


def test_listagem_incompleta_nao_marca_remocoes(db: Engine) -> None:
    """Se a listagem trouxe bem menos que o declarado, é falha da coleta, não remoção de verdade."""
    portal = FakePortal(n_datasets=40)
    run_extraction(db, portal)
    portal.hidden_from_listing = {f"ds-{i:04d}" for i in range(1, 21)}  # metade some da listagem
    # a organização continua declarando 40 (o fake calcula pelos datasets existentes)

    run_id, state = run_extraction(db, portal, "incremental")

    assert state == "concluida_com_divergencias"
    t = totals(db, run_id)
    assert t["remocao_aplicada"] is False and t["removidos"] == 0
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto WHERE removido_em IS NOT NULL") == 0
    assert t["divergencias_por_organizacao"]


def test_detalhe_que_devolve_400_e_registrado_sem_derrubar_a_extracao(db: Engine) -> None:
    portal = FakePortal(n_datasets=20, bad_ids={"ds-0003"})

    run_id, state = run_extraction(db, portal)

    assert state == "concluida_com_divergencias"
    t = totals(db, run_id)
    assert t["sem_detalhe"] == 1
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto") == 20
    assert scalar(db, "SELECT sem_detalhe FROM catalogo.conjunto WHERE id = 'ds-0003'") is True
    assert (
        scalar(db, "SELECT motivo FROM raw.fila_detalhe WHERE conjunto_id = 'ds-0003'")
        == "HTTP 400"
    )


def test_portal_com_respostas_vazias_intermitentes_nao_perde_dados(db: Engine) -> None:
    portal = FakePortal(n_datasets=45, flaky_every=3)

    run_id, state = run_extraction(db, portal)

    assert state == "concluida"
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto") == 45
    assert totals(db, run_id)["listados"] == 45


def test_chave_recusada_termina_como_falhou_com_o_motivo(db: Engine) -> None:
    portal = FakePortal(n_datasets=5)
    run_id = RawStore(db).create_run("completa")
    with make_client(portal, key="chave-errada") as client:
        state = ExtractionRunner(db, client).run(run_id)

    assert state == "falhou"
    assert (
        "chave" in str(scalar(db, "SELECT erro FROM raw.execucao WHERE id = :r", r=run_id)).lower()
    )


def test_cancelamento_solicitado_encerra_a_execucao(db: Engine) -> None:
    portal = FakePortal(n_datasets=30)
    run_id = RawStore(db).create_run("completa")
    with db.begin() as conn:
        conn.execute(
            text("UPDATE raw.execucao SET cancelar_solicitado = true WHERE id = :r"), {"r": run_id}
        )

    with make_client(portal) as client:
        state = ExtractionRunner(db, client).run(run_id)

    assert state == "cancelada"
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto") == 0


def test_execucao_interrompida_e_retomada_sem_refazer_a_listagem(db: Engine) -> None:
    portal = FakePortal(n_datasets=40)
    run_id = RawStore(db).create_run("completa")
    with make_client(portal) as client:
        runner = ExtractionRunner(db, client, concurrency=2)
        runner._load(run_id)
        runner._phase_dimensions(run_id, {})
        expected = runner._phase_organizations(run_id)
        runner._phase_listing(run_id, "completa", expected)
        # simula queda: processou só um lote parcial
        with db.connect() as conn:
            first = conn.execute(
                text("SELECT conjunto_id, resumo FROM raw.fila_detalhe LIMIT 5")
            ).all()
        for item in first:
            runner._process_item(run_id, item.conjunto_id, dict(item.resumo))
    list_calls = portal.calls["list"]

    with make_client(portal) as client:
        state = ExtractionRunner(db, client, concurrency=2).run(run_id)

    assert state == "concluida"
    assert portal.calls["list"] == list_calls  # não listou de novo
    assert scalar(db, "SELECT count(*) FROM catalogo.conjunto") == 40
