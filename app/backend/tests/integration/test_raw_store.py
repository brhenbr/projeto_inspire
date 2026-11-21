import threading

import pytest
from sqlalchemy import text

from inspire.db import get_engine
from inspire.extraction.errors import ActiveRunExistsError, PersonalDataError
from inspire.extraction.raw_store import RawStore, SaveOutcome

pytestmark = pytest.mark.integration

DOC = {"id": "abc", "titulo": "Planos de saúde", "temResponsavel": True}


def count(table: str) -> int:
    with get_engine().connect() as conn:
        return int(conn.execute(text(f"SELECT count(*) FROM raw.{table}")).scalar_one())


def test_primeiro_documento_e_novo(store: RawStore) -> None:
    run = store.create_run("completa")

    result = store.save(run, "conjunto", "abc", DOC)

    assert result.outcome is SaveOutcome.NEW
    assert count("documento") == 1
    assert store.latest("conjunto", "abc") == DOC


def test_mesmo_conteudo_nao_grava_de_novo_mas_e_marcado_como_visto(store: RawStore) -> None:
    run1 = store.create_run("completa")
    store.save(run1, "conjunto", "abc", DOC)
    store.finish_run(run1, "concluida")

    run2 = store.create_run("incremental")
    result = store.save(
        run2, "conjunto", "abc", dict(reversed(DOC.items()))
    )  # outra ordem de chaves

    assert result.outcome is SaveOutcome.UNCHANGED
    assert count("documento") == 1
    assert count("visto") == 2  # visto nas duas execuções


def test_conteudo_diferente_gera_nova_versao_e_a_mais_recente_vale(store: RawStore) -> None:
    run1 = store.create_run("completa")
    store.save(run1, "conjunto", "abc", DOC)
    store.finish_run(run1, "concluida")

    run2 = store.create_run("incremental")
    result = store.save(run2, "conjunto", "abc", {**DOC, "titulo": "Planos de saúde 2026"})

    assert result.outcome is SaveOutcome.CHANGED
    assert count("documento") == 2
    assert store.latest("conjunto", "abc")["titulo"] == "Planos de saúde 2026"  # type: ignore[index]


def test_voltar_a_um_conteudo_antigo_conta_como_alterado(store: RawStore) -> None:
    for kind, titulo in (("completa", "A"), ("incremental", "B"), ("incremental", "A")):
        run = store.create_run(kind)
        result = store.save(run, "conjunto", "abc", {"titulo": titulo})
        store.finish_run(run, "concluida")

    assert result.outcome is SaveOutcome.CHANGED
    assert count("documento") == 3


def test_documentos_de_chaves_e_tipos_diferentes_sao_independentes(store: RawStore) -> None:
    run = store.create_run("completa")

    a = store.save(run, "conjunto", "1", DOC)
    b = store.save(run, "conjunto", "2", DOC)
    c = store.save(run, "organizacao", "1", DOC)

    assert {a.outcome, b.outcome, c.outcome} == {SaveOutcome.NEW}
    assert count("documento") == 3


def test_o_banco_recusa_dados_pessoais(store: RawStore) -> None:
    run = store.create_run("completa")

    with pytest.raises(PersonalDataError):
        store.save(run, "conjunto", "abc", {**DOC, "emailResponsavel": "a@b.gov.br"})

    assert count("documento") == 0


def test_so_uma_execucao_ativa_por_vez(store: RawStore) -> None:
    store.create_run("completa")

    with pytest.raises(ActiveRunExistsError):
        store.create_run("incremental")


def test_depois_de_terminar_pode_criar_outra(store: RawStore) -> None:
    first = store.create_run("completa")
    store.finish_run(first, "concluida")

    assert store.create_run("incremental") != first


def test_pedidos_simultaneos_criam_uma_unica_execucao(store: RawStore) -> None:
    resultados: list[object] = []
    barreira = threading.Barrier(8)

    def pedir() -> None:
        barreira.wait()
        try:
            resultados.append(store.create_run("incremental"))
        except ActiveRunExistsError as exc:
            resultados.append(exc)

    threads = [threading.Thread(target=pedir) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    criadas = [r for r in resultados if isinstance(r, int)]
    recusadas = [r for r in resultados if isinstance(r, ActiveRunExistsError)]
    assert len(criadas) == 1
    assert len(recusadas) == 7
    assert count("execucao") == 1
