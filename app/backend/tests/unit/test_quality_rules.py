from datetime import UTC, datetime, timedelta

from inspire.quality.rules import RULES, RULES_BY_KEY, Facts
from inspire.quality.service import evaluate

NOW = datetime(2026, 11, 21, tzinfo=UTC)
LONG = "d" * 120


def good() -> Facts:
    return Facts(
        id="1",
        titulo="Execução orçamentária da União por órgão",
        slug="execucao-orcamentaria",
        descricao=LONG,
        licenca="cc-by",
        periodicidade="MENSAL",
        tags=["orçamento", "união", "despesa"],
        temas=["economia"],
        cobertura_temporal_inicio="01/01/2020",
        tem_responsavel=True,
        dados_abertos=True,
        atualizado_portal="Atualizado",
        dados_atualizados_em=NOW - timedelta(days=10),
        recursos=[
            {
                "formato": "CSV",
                "link": "https://x.gov.br/dados.csv",
                "titulo": "Dados",
                "descricao": "Planilha",
            }
        ],
    )


def outcome(key: str, facts: Facts):  # type: ignore[no-untyped-def]
    return RULES_BY_KEY[key].check(facts, NOW)


def test_conjunto_exemplar_tira_nota_maxima() -> None:
    result = evaluate(good(), NOW)

    assert result.score == 100.0
    assert all(d["passou"] is not False for d in result.details)


def test_conjunto_vazio_tira_nota_baixa_e_explica_por_que() -> None:
    result = evaluate(Facts(id="2", titulo="abc"), NOW)

    assert result.score < 25
    failed = {d["regra"] for d in result.details if d["passou"] is False}
    assert {"COMP-01", "COMP-02", "COMP-03", "COMP-04", "ACC-01"} <= failed
    assert all(d["mensagem"] for d in result.details if d["passou"] is False)


def test_titulo_parecido_com_identificador_reprova() -> None:
    f = good()
    f.titulo = "execucao_orcamentaria_2024"
    assert outcome("COMP-01", f).passed is False


def test_descricao_curta_reprova_e_a_mensagem_diz_o_tamanho() -> None:
    f = good()
    f.descricao = "curta"
    r = outcome("COMP-02", f)
    assert r.passed is False and "5 caracteres" in r.message


def test_tags_exige_ao_menos_tres() -> None:
    f = good()
    f.tags = ["a", "b"]
    assert outcome("COMP-05", f).passed is False


def test_atualidade_respeita_a_periodicidade_com_folga() -> None:
    f = good()
    f.periodicidade = "MENSAL"
    f.dados_atualizados_em = NOW - timedelta(days=40)  # dentro de 31*1.5
    assert outcome("TIME-01", f).passed is True
    f.dados_atualizados_em = NOW - timedelta(days=60)
    assert outcome("TIME-01", f).passed is False


def test_atualidade_nao_e_avaliavel_sem_periodicidade_conhecida_ou_sem_data() -> None:
    f = good()
    f.periodicidade = None
    assert outcome("TIME-01", f).evaluable is False
    f.periodicidade = "SOB DEMANDA"
    assert outcome("TIME-01", f).evaluable is False
    f.periodicidade = "ANUAL"
    f.dados_atualizados_em = None
    assert outcome("TIME-01", f).evaluable is False


def test_periodicidade_com_acento_e_normalizada() -> None:
    f = good()
    f.periodicidade = "Diária"
    f.dados_atualizados_em = NOW - timedelta(hours=5)
    assert outcome("TIME-01", f).passed is True


def test_formato_aberto_ignora_maiusculas_e_reprova_proprietarios() -> None:
    f = good()
    f.recursos = [{"formato": "csv", "link": "https://a.gov.br/x"}]
    assert outcome("OPEN-01", f).passed is True
    f.recursos = [
        {"formato": "XLSX", "link": "https://a.gov.br/x"},
        {"formato": "PDF", "link": "https://a.gov.br/y"},
    ]
    assert outcome("OPEN-01", f).passed is False


def test_links_invalidos_reprovam() -> None:
    f = good()
    f.recursos = [{"formato": "CSV", "link": "ftp://x"}, {"formato": "CSV", "link": ""}]
    r = outcome("ACC-02", f)
    assert r.passed is False and "2 recurso" in r.message


def test_formato_inconsistente_com_a_extensao_do_link() -> None:
    f = good()
    f.recursos = [{"formato": "CSV", "link": "https://x.gov.br/arquivo.pdf"}]
    assert outcome("CONS-01", f).passed is False
    f.recursos = [{"formato": "CSV", "link": "https://x.gov.br/arquivo.csv?download=1"}]
    assert outcome("CONS-01", f).passed is True
    f.recursos = [{"formato": "CSV", "link": "https://x.gov.br/api/dados"}]
    assert outcome("CONS-01", f).evaluable is False


def test_licenca_aberta_so_e_avaliada_quando_ha_licenca() -> None:
    f = good()
    f.licenca = None
    assert outcome("CONF-01", f).evaluable is False
    f.licenca = "proprietaria"
    assert outcome("CONF-01", f).passed is False


def test_regra_nao_avaliavel_nao_pesa_na_nota() -> None:
    a = good()
    a.periodicidade = None  # TIME-01 deixa de ser avaliável; COMP-04 reprova
    result = evaluate(a, NOW)
    time = next(d for d in result.details if d["regra"] == "TIME-01")

    assert time["avaliavel"] is False and time["passou"] is None


def test_pesos_e_ativacao_vem_da_configuracao() -> None:
    f = Facts(id="3", titulo="Título descritivo suficientemente longo", descricao=LONG)
    base = evaluate(f, NOW).score
    sem_descricao = {r.key: (r.weight, r.key != "COMP-02") for r in RULES}
    peso_alto = {r.key: (10.0 if r.key == "COMP-02" else r.weight, True) for r in RULES}

    assert evaluate(f, NOW, sem_descricao).score < base  # a regra que passava saiu da conta
    assert evaluate(f, NOW, peso_alto).score > base


def test_nota_por_dimensao_e_calculada() -> None:
    result = evaluate(good(), NOW)

    assert result.dimensions["Completude"] == 100.0
    assert set(result.dimensions) >= {
        "Completude",
        "Atualidade",
        "Acessibilidade",
        "Processabilidade",
    }


def test_toda_regra_tem_dimensao_fonte_e_chave_unica() -> None:
    assert len({r.key for r in RULES}) == len(RULES)
    assert all(r.dimension and r.source and r.framework and r.weight > 0 for r in RULES)
