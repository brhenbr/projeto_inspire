"""Regras de qualidade de metadados.

Cada regra pertence a uma dimensão e cita sua fonte (ver docs/02-arquitetura/matriz-de-qualidade.md).
Regras podem ser "não avaliáveis" (faltam dados para julgar): elas não entram na nota, mas aparecem no
detalhe. Os pesos vêm do banco (`analitico.regra_qualidade`), então são configuráveis.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

OPEN_FORMATS = frozenset(
    {
        "CSV",
        "TSV",
        "JSON",
        "JSONLD",
        "JSON-LD",
        "XML",
        "RDF",
        "TTL",
        "TURTLE",
        "GEOJSON",
        "API",
        "PARQUET",
        "ODS",
    }
)
OPEN_LICENSES = frozenset(
    {
        "cc-by",
        "cc-by-sa",
        "cc-zero",
        "cc0",
        "odc-by",
        "odc-odbl",
        "odc-pddl",
        "other-open",
        "ogl-uk",
        "gfdl",
    }
)
# Periodicidade declarada -> intervalo esperado entre atualizações (com folga na avaliação).
PERIOD_DAYS = {
    "TEMPO REAL": 1,
    "DIARIA": 1,
    "SEMANAL": 7,
    "QUINZENAL": 15,
    "MENSAL": 31,
    "BIMESTRAL": 62,
    "TRIMESTRAL": 92,
    "QUADRIMESTRAL": 123,
    "SEMESTRAL": 183,
    "ANUAL": 366,
    "BIENAL": 731,
}
GRACE = 1.5
_EXT = re.compile(r"\.([A-Za-z0-9]{2,5})(?:[?#].*)?$")
_EXT_TO_FORMAT = {
    "csv": "CSV",
    "json": "JSON",
    "xml": "XML",
    "pdf": "PDF",
    "xls": "XLS",
    "xlsx": "XLSX",
    "zip": "ZIP",
    "txt": "TXT",
    "doc": "DOC",
    "docx": "DOCX",
    "rdf": "RDF",
    "ods": "ODS",
}


@dataclass
class Facts:
    """Valores EFETIVOS do conjunto (já com a curadoria aplicada) usados pelas regras."""

    id: str
    titulo: str = ""
    slug: str | None = None
    descricao: str | None = None
    licenca: str | None = None
    periodicidade: str | None = None
    tags: list[str] = field(default_factory=list)
    temas: list[str] = field(default_factory=list)
    cobertura_temporal_inicio: str | None = None
    cobertura_temporal_fim: str | None = None
    cobertura_espacial: str | None = None
    tem_responsavel: bool = False
    tem_email_responsavel: bool = False
    dados_abertos: bool | None = None
    atualizado_portal: str | None = None
    dados_atualizados_em: datetime | None = None
    recursos: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class Outcome:
    evaluable: bool
    passed: bool = False
    message: str = ""


@dataclass(frozen=True)
class Rule:
    key: str
    dimension: str
    framework: str
    name: str
    description: str
    weight: float
    source: str
    check: Callable[[Facts, datetime], Outcome]


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip()).encode("ascii", "ignore").decode()
    return text.upper().replace("_", " ")


def _filled(value: str | None) -> bool:
    return bool(value and value.strip())


def _slug_like(title: str) -> bool:
    return " " not in title.strip() and ("-" in title or "_" in title)


def _descriptive_title(f: Facts, _now: datetime) -> Outcome:
    ok = len(f.titulo.strip()) >= 15 and not _slug_like(f.titulo)
    return Outcome(True, ok, "" if ok else "Título curto ou parecido com um identificador")


def _description(f: Facts, _now: datetime) -> Outcome:
    n = len((f.descricao or "").strip())
    return Outcome(True, n >= 100, "" if n >= 100 else f"Descrição com {n} caracteres (mínimo 100)")


def _license_present(f: Facts, _now: datetime) -> Outcome:
    ok = _filled(f.licenca)
    return Outcome(True, ok, "" if ok else "Licença não informada")


def _periodicity_present(f: Facts, _now: datetime) -> Outcome:
    ok = _filled(f.periodicidade)
    return Outcome(True, ok, "" if ok else "Periodicidade não informada")


def _enough_tags(f: Facts, _now: datetime) -> Outcome:
    ok = len(f.tags) >= 3
    return Outcome(True, ok, "" if ok else f"{len(f.tags)} palavra(s)-chave (mínimo 3)")


def _theme(f: Facts, _now: datetime) -> Outcome:
    ok = bool(f.temas)
    return Outcome(True, ok, "" if ok else "Nenhum tema atribuído")


def _coverage(f: Facts, _now: datetime) -> Outcome:
    ok = (
        _filled(f.cobertura_temporal_inicio)
        or _filled(f.cobertura_temporal_fim)
        or _filled(f.cobertura_espacial)
    )
    return Outcome(True, ok, "" if ok else "Sem cobertura temporal nem espacial")


def _contact(f: Facts, _now: datetime) -> Outcome:
    ok = f.tem_responsavel or f.tem_email_responsavel
    return Outcome(True, ok, "" if ok else "Sem ponto de contato do responsável")


def _described_resources(f: Facts, _now: datetime) -> Outcome:
    if not f.recursos:
        return Outcome(False)
    described = sum(1 for r in f.recursos if _filled(r.get("descricao")))
    ok = described / len(f.recursos) >= 0.5
    return Outcome(True, ok, "" if ok else "Menos da metade dos recursos tem descrição")


def _timeliness(f: Facts, now: datetime) -> Outcome:
    days = PERIOD_DAYS.get(_norm(f.periodicidade))
    if days is None or f.dados_atualizados_em is None:
        return Outcome(False)
    limit = timedelta(days=days * GRACE)
    ok = now - f.dados_atualizados_em <= limit
    return Outcome(
        True, ok, "" if ok else "Dados mais antigos que o esperado para a periodicidade declarada"
    )


def _portal_updated(f: Facts, _now: datetime) -> Outcome:
    state = _norm(f.atualizado_portal)
    if state not in {"ATUALIZADO", "DESATUALIZADO"}:
        return Outcome(False)
    return Outcome(
        True,
        state == "ATUALIZADO",
        "" if state == "ATUALIZADO" else "Portal marca como desatualizado",
    )


def _has_resource(f: Facts, _now: datetime) -> Outcome:
    ok = bool(f.recursos)
    return Outcome(True, ok, "" if ok else "Nenhum recurso (arquivo ou API) associado")


def _valid_links(f: Facts, _now: datetime) -> Outcome:
    if not f.recursos:
        return Outcome(False)

    def valid(link: str | None) -> bool:
        parsed = urlparse((link or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    bad = sum(1 for r in f.recursos if not valid(r.get("link")))
    return Outcome(
        True, bad == 0, "" if bad == 0 else f"{bad} recurso(s) com link ausente ou inválido"
    )


def _open_format(f: Facts, _now: datetime) -> Outcome:
    if not f.recursos:
        return Outcome(False)
    ok = any(_norm(r.get("formato")).replace(" ", "") in OPEN_FORMATS for r in f.recursos)
    return Outcome(True, ok, "" if ok else "Nenhum recurso em formato aberto e legível por máquina")


def _open_data(f: Facts, _now: datetime) -> Outcome:
    if f.dados_abertos is None:
        return Outcome(False)
    return Outcome(
        True,
        f.dados_abertos,
        "" if f.dados_abertos else "Portal indica que os dados não são abertos",
    )


def _open_license(f: Facts, _now: datetime) -> Outcome:
    if not _filled(f.licenca):
        return Outcome(False)
    ok = (f.licenca or "").strip().lower() in OPEN_LICENSES
    return Outcome(True, ok, "" if ok else "Licença não reconhecida como aberta")


def _consistent_format(f: Facts, _now: datetime) -> Outcome:
    checked = mismatched = 0
    for r in f.recursos:
        declared = _norm(r.get("formato")).replace(" ", "")
        match = _EXT.search(urlparse(r.get("link") or "").path)
        found = _EXT_TO_FORMAT.get(match.group(1).lower()) if match else None
        if declared and found:
            checked += 1
            mismatched += declared != found
    if not checked:
        return Outcome(False)
    return Outcome(
        True,
        mismatched == 0,
        ""
        if mismatched == 0
        else f"{mismatched} recurso(s) com formato diferente da extensão do link",
    )


def _rule(
    key: str,
    dim: str,
    fw: str,
    name: str,
    desc: str,
    weight: float,
    source: str,
    check: Callable[[Facts, datetime], Outcome],
) -> Rule:
    return Rule(key, dim, fw, name, desc, weight, source, check)


RULES: tuple[Rule, ...] = (
    _rule(
        "COMP-01",
        "Completude",
        "DQV/DMBOK",
        "Título descritivo",
        "O título tem ao menos 15 caracteres e não parece um identificador.",
        1,
        "DMBOK2 (completude e clareza); FAIR F2",
        _descriptive_title,
    ),
    _rule(
        "COMP-02",
        "Completude",
        "DQV/DMBOK",
        "Descrição adequada",
        "A descrição tem ao menos 100 caracteres.",
        3,
        "DMBOK2 (completude); FAIR F2/R1",
        _description,
    ),
    _rule(
        "COMP-03",
        "Completude",
        "FAIR",
        "Licença informada",
        "O conjunto informa a licença de uso.",
        2,
        "FAIR R1.1; DCAT-BR dct:license",
        _license_present,
    ),
    _rule(
        "COMP-04",
        "Completude",
        "DQV",
        "Periodicidade informada",
        "O conjunto informa a periodicidade de atualização.",
        2,
        "DQV (completude); DCAT dct:accrualPeriodicity",
        _periodicity_present,
    ),
    _rule(
        "COMP-05",
        "Completude",
        "FAIR",
        "Palavras-chave suficientes",
        "O conjunto tem ao menos 3 palavras-chave.",
        2,
        "FAIR F2/F4 (descoberta); DCAT dcat:keyword",
        _enough_tags,
    ),
    _rule(
        "COMP-06",
        "Completude",
        "FAIR",
        "Tema atribuído",
        "O conjunto está classificado em ao menos um tema.",
        1,
        "FAIR F4; DCAT dcat:theme",
        _theme,
    ),
    _rule(
        "COMP-07",
        "Completude",
        "DQV",
        "Cobertura informada",
        "O conjunto informa cobertura temporal ou espacial.",
        1,
        "DQV (completude); DCAT dct:temporal/dct:spatial",
        _coverage,
    ),
    _rule(
        "COMP-08",
        "Completude",
        "DCAT-BR",
        "Ponto de contato",
        "O conjunto tem um responsável de contato registrado no portal.",
        1,
        "DCAT-BR dcat:contactPoint",
        _contact,
    ),
    _rule(
        "COMP-09",
        "Compreensibilidade",
        "DQV",
        "Recursos descritos",
        "Ao menos metade dos recursos tem descrição.",
        1,
        "DQV (compreensibilidade); FAIR R1",
        _described_resources,
    ),
    _rule(
        "TIME-01",
        "Atualidade",
        "DQV/DMBOK",
        "Atualizado conforme a periodicidade",
        "A última atualização dos dados está dentro do intervalo esperado (com folga de 50%).",
        3,
        "DMBOK2 (atualidade); DQV timeliness",
        _timeliness,
    ),
    _rule(
        "TIME-02",
        "Atualidade",
        "DQV",
        "Atualizado segundo o portal",
        "O portal classifica o conjunto como atualizado.",
        1,
        "Indicador do próprio portal",
        _portal_updated,
    ),
    _rule(
        "ACC-01",
        "Acessibilidade",
        "FAIR",
        "Possui recurso",
        "O conjunto tem ao menos um recurso associado.",
        3,
        "FAIR A1; DQV availability",
        _has_resource,
    ),
    _rule(
        "ACC-02",
        "Acessibilidade",
        "FAIR",
        "Links válidos",
        "Todos os recursos têm um link http(s) bem formado.",
        2,
        "FAIR A1; DCAT dcat:accessURL (verificação ativa: fase 2)",
        _valid_links,
    ),
    _rule(
        "OPEN-01",
        "Processabilidade",
        "DQV/5 estrelas",
        "Formato aberto",
        "Ao menos um recurso está em formato aberto e legível por máquina.",
        3,
        "5 estrelas de dados abertos; FAIR I1",
        _open_format,
    ),
    _rule(
        "OPEN-02",
        "Processabilidade",
        "Portal",
        "Dados abertos segundo o portal",
        "O portal marca os dados como abertos.",
        1,
        "Indicador do próprio portal",
        _open_data,
    ),
    _rule(
        "CONF-01",
        "Conformidade",
        "FAIR",
        "Licença aberta",
        "A licença informada é reconhecida como aberta.",
        2,
        "FAIR R1.1; Open Definition",
        _open_license,
    ),
    _rule(
        "CONS-01",
        "Consistência",
        "DQV/DMBOK",
        "Formato coerente com o link",
        "O formato declarado bate com a extensão do link.",
        1,
        "DMBOK2 (consistência); DQV consistency",
        _consistent_format,
    ),
)
RULES_BY_KEY = {r.key: r for r in RULES}
