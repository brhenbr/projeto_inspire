import pytest

from inspire.extraction.errors import PersonalDataError
from inspire.extraction.privacy import (
    assert_no_personal_data,
    find_email_like,
    strip_personal_data,
)


def detalhe() -> dict:  # type: ignore[type-arg]
    return {
        "id": "abc",
        "titulo": "Planos de saúde",
        "responsavel": "Fulana de Tal",
        "emailResponsavel": "fulana@orgao.gov.br",
        "recursos": [{"id": "r1", "link": "https://orgao.gov.br/a.csv"}],
        "tags": [{"name": "ANS"}],
    }


def test_remove_nome_e_email_do_responsavel() -> None:
    limpo = strip_personal_data(detalhe())

    assert "responsavel" not in limpo
    assert "emailResponsavel" not in limpo
    assert "Fulana" not in str(limpo)
    assert "fulana@orgao.gov.br" not in str(limpo)


def test_guarda_apenas_que_os_contatos_existiam() -> None:
    limpo = strip_personal_data(detalhe())

    assert limpo["temResponsavel"] is True
    assert limpo["temEmailResponsavel"] is True


def test_marca_como_ausente_quando_vem_vazio_ou_nulo() -> None:
    d = detalhe()
    d["responsavel"] = ""
    d["emailResponsavel"] = None

    limpo = strip_personal_data(d)

    assert limpo["temResponsavel"] is False
    assert limpo["temEmailResponsavel"] is False


def test_nao_altera_o_original_e_preserva_o_resto() -> None:
    original = detalhe()

    limpo = strip_personal_data(original)

    assert original["responsavel"] == "Fulana de Tal"
    assert limpo["titulo"] == "Planos de saúde"
    assert limpo["recursos"] == original["recursos"]


def test_remove_campos_pessoais_aninhados_e_com_outra_grafia() -> None:
    d = detalhe()
    d["recursos"][0]["Maintainer_Email"] = "x@y.gov.br"
    d["extras"] = [{"maintainer": "Fulano"}]

    limpo = strip_personal_data(d)

    assert "x@y.gov.br" not in str(limpo)
    assert "Fulano" not in str(limpo)


def test_o_resultado_passa_na_barreira_final() -> None:
    assert_no_personal_data(strip_personal_data(detalhe()))


@pytest.mark.parametrize(
    "payload",
    [
        {"responsavel": "Alguém"},
        {"emailResponsavel": "a@b.gov.br"},
        {"recursos": [{"maintainerEmail": "a@b.gov.br"}]},
        [{"x": {"Responsavel": "Alguém"}}],
    ],
)
def test_barreira_final_barra_qualquer_campo_pessoal(payload: object) -> None:
    with pytest.raises(PersonalDataError):
        assert_no_personal_data(payload)


def test_conta_emails_em_texto_livre_sem_altera_los() -> None:
    d = {"descricao": "Dúvidas: dados@orgao.gov.br ou outra@orgao.gov.br", "titulo": "ok"}

    assert find_email_like(d) == 2
    assert "dados@orgao.gov.br" in d["descricao"]
