"""Exportação em DCAT-BR (JSON-LD) com a qualidade em DQV (ADR-0015).

Usa os valores EFETIVOS (curados quando houver) do catálogo espelhado. O contato do responsável do conjunto
(dcat:contactPoint) NÃO é exportado: nome e e-mail são dados pessoais e nem existem no banco (ADR-0002).
Mapeamento de campos: docs/02-arquitetura/mapeamento-dcat-br.md.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, text

from inspire.discovery.catalog import PORTAL_DATASET_URL
from inspire.discovery.search import Filters, SearchService

CHUNK = 500
NS = "https://inspire.exemplo.invalid/ns/"  # prefixo próprio das medidas de qualidade (sem host real)
CONTEXT: dict[str, str] = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "dqv": "http://www.w3.org/ns/dqv#",
    "prov": "http://www.w3.org/ns/prov#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "inspire": NS,
}
LICENSES = {
    "cc-by": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "creative commons atribuição": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-zero": "https://creativecommons.org/publicdomain/zero/1.0/",
    "creative commons cczero": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
    "odc-odbl": "https://opendatacommons.org/licenses/odbl/1-0/",
    "odc-pddl": "https://opendatacommons.org/licenses/pddl/1-0/",
    "odc-by": "https://opendatacommons.org/licenses/by/1-0/",
    "gfdl": "https://www.gnu.org/licenses/fdl-1.3.html",
    "uk-ogl": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
}
FREQUENCIES = {
    "DIARIA": "daily",
    "SEMANAL": "weekly",
    "QUINZENAL": "biweekly",
    "MENSAL": "monthly",
    "TRIMESTRAL": "quarterly",
    "SEMESTRAL": "semiannual",
    "ANUAL": "annual",
}
ACCESS_PUBLIC = "http://publications.europa.eu/resource/authority/access-right/PUBLIC"
SQL = text(
    """
    SELECT b.id, b.titulo, b.descricao, b.organizacao_slug, b.organizacao_titulo, b.temas, b.tags, b.licenca,
           b.periodicidade, b.estado_curadoria, b.curado, b.nota_qualidade, b.metadados_atualizados_em,
           c.slug, c.versao, c.catalogado_em, c.cobertura_temporal_inicio, c.cobertura_temporal_fim,
           c.cobertura_espacial, c.dados_abertos, q.dimensoes
    FROM analitico.conjunto_busca b
    JOIN catalogo.conjunto c ON c.id = b.id
    LEFT JOIN analitico.qualidade_conjunto q ON q.conjunto_id = b.id
    WHERE b.id = ANY(:ids) ORDER BY b.id
    """
)
SQL_RESOURCES = text(
    """
    SELECT conjunto_id, id, titulo, descricao, formato, link, tamanho
    FROM catalogo.recurso WHERE conjunto_id = ANY(:ids) ORDER BY conjunto_id, ordem NULLS LAST, id
    """
)


def _slug(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _date(value: Any) -> str | None:
    return value.date().isoformat() if value is not None else None


def _br_date(value: str | None) -> str | None:
    """'01/01/2017' ou '01/01/2017 10:00:00' vira '2017-01-01'; o que não for data fica de fora."""
    if not value:
        return None
    day = value.strip().split(" ")[0].split("/")
    if len(day) == 3 and all(p.isdigit() for p in day):
        return f"{day[2]}-{day[1].zfill(2)}-{day[0].zfill(2)}"
    return None


def _license(value: str | None) -> Any:
    if not value or value == "notspecified":
        return None
    uri = LICENSES.get(value.strip().lower())
    return {"@id": uri} if uri else value


def _distribution(r: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"@type": "dcat:Distribution"}
    if r.link:
        out["dcat:accessURL"] = {"@id": r.link}
    if r.titulo:
        out["dct:title"] = r.titulo
    if r.descricao:
        out["dct:description"] = r.descricao
    if r.formato:
        out["dct:format"] = r.formato
    if r.tamanho:  # 0 = desconhecido no portal
        out["dcat:byteSize"] = {"@type": "xsd:decimal", "@value": str(r.tamanho)}
    return out


def _dataset(r: Any, resources: list[Any]) -> dict[str, Any]:
    uri = f"{PORTAL_DATASET_URL}{r.slug}" if r.slug else f"urn:inspire:conjunto:{r.id}"
    d: dict[str, Any] = {
        "@id": uri,
        "@type": "dcat:Dataset",
        "dct:identifier": r.id,
        "dct:title": r.titulo,
        "dct:language": "pt-BR",
        "dct:accessRights": {"@id": ACCESS_PUBLIC},
        "inspire:statusCuradoria": r.estado_curadoria,
        "inspire:curado": bool(r.curado),
    }
    if r.descricao:
        d["dct:description"] = r.descricao
    if r.tags:
        d["dcat:keyword"] = list(r.tags)
    if r.temas:
        d["dcat:theme"] = [{"@type": "skos:Concept", "skos:notation": t} for t in r.temas]
    if r.organizacao_slug:
        d["dct:publisher"] = {
            "@type": "foaf:Organization",
            "foaf:name": r.organizacao_titulo or r.organizacao_slug,
            "dct:identifier": r.organizacao_slug,
        }
    if (lic := _license(r.licenca)) is not None:
        d["dct:license"] = lic
    if r.periodicidade in FREQUENCIES:
        d["dct:accrualPeriodicity"] = {
            "@id": f"http://purl.org/cld/freq/{FREQUENCIES[r.periodicidade]}"
        }
    elif r.periodicidade:
        d["dct:accrualPeriodicity"] = r.periodicidade
    if r.slug:
        d["dcat:landingPage"] = {"@id": uri}
        d["prov:wasDerivedFrom"] = {"@id": uri}
    if (issued := _date(r.catalogado_em)) is not None:
        d["dct:issued"] = {"@type": "xsd:date", "@value": issued}
    if (modified := _date(r.metadados_atualizados_em)) is not None:
        d["dct:modified"] = {"@type": "xsd:date", "@value": modified}
    if r.versao:
        d["dcat:version"] = r.versao
    if r.cobertura_espacial:
        d["dct:spatial"] = {"@type": "dct:Location", "skos:prefLabel": r.cobertura_espacial}
    start, end = _br_date(r.cobertura_temporal_inicio), _br_date(r.cobertura_temporal_fim)
    if start or end:
        period: dict[str, Any] = {"@type": "dct:PeriodOfTime"}
        if start:
            period["dcat:startDate"] = {"@type": "xsd:date", "@value": start}
        if end:
            period["dcat:endDate"] = {"@type": "xsd:date", "@value": end}
        d["dct:temporal"] = period
    if resources:
        d["dcat:distribution"] = [_distribution(x) for x in resources]
    measures = _measures(r, uri)
    if measures:
        d["dqv:hasQualityMeasurement"] = measures
    return d


def _measures(r: Any, uri: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if r.nota_qualidade is not None:
        out.append(_measure("nota", float(r.nota_qualidade), uri))
    for name, value in (r.dimensoes or {}).items():
        out.append(_measure(_slug(name), float(value), uri))
    return out


def _measure(metric: str, value: float, computed_on: str) -> dict[str, Any]:
    return {
        "@type": "dqv:QualityMeasurement",
        "dqv:isMeasurementOf": {"@id": f"{NS}metrica/{metric}"},
        "dqv:computedOn": {"@id": computed_on},
        "dqv:value": {"@type": "xsd:decimal", "@value": f"{value:.1f}"},
    }


def _metrics(engine: Engine) -> list[dict[str, Any]]:
    """Nota geral e uma métrica por dimensão (lidas das regras), descritas uma vez no início do grafo."""
    with engine.connect() as conn:
        dimensions = [
            r[0]
            for r in conn.execute(
                text("SELECT DISTINCT dimensao FROM analitico.regra_qualidade ORDER BY 1")
            )
        ]
    names = {"nota": "Nota de qualidade (0 a 100)", **{_slug(d): d for d in dimensions}}
    return [
        {
            "@id": f"{NS}metrica/{key}",
            "@type": "dqv:Metric",
            "skos:prefLabel": label,
            "dqv:expectedDataType": {"@id": "http://www.w3.org/2001/XMLSchema#decimal"},
        }
        for key, label in names.items()
    ]


def build_catalog(
    engine: Engine, filters: Filters, *, title: str, limit: int = 100000
) -> Iterator[bytes]:
    """JSON-LD em fluxo: contexto, catálogo e métricas, depois um conjunto por vez."""
    ids = SearchService(engine).ids(filters, limit=limit)
    head: dict[str, Any] = {
        "@id": "urn:inspire:catalogo",
        "@type": "dcat:Catalog",
        "dct:title": title,
        "dct:description": (
            "Espelho curado dos metadados do dados.gov.br, exportado em DCAT-BR com qualidade em DQV."
        ),
        "dct:conformsTo": {
            "@id": "https://www.gov.br/governodigital/pt-br/infraestrutura-nacional-de-dados/catalogo-nacional-de-dados/materiais-de-apoio/vocabulario-padrao-dcat-br-v1.0"
        },
        "inspire:totalConjuntos": len(ids),
    }
    yield (
        b'{"@context":'
        + json.dumps(CONTEXT).encode()
        + b',"@graph":['
        + json.dumps(head, ensure_ascii=False).encode("utf-8")
    )
    for metric in _metrics(engine):
        yield b"," + json.dumps(metric, ensure_ascii=False).encode("utf-8")
    for start in range(0, len(ids), CHUNK):
        chunk = ids[start : start + CHUNK]
        with engine.connect() as conn:
            by_dataset: dict[str, list[Any]] = {}
            for res in conn.execute(SQL_RESOURCES, {"ids": chunk}):
                by_dataset.setdefault(res.conjunto_id, []).append(res)
            for r in conn.execute(SQL, {"ids": chunk}):
                node = _dataset(r, by_dataset.get(r.id, []))
                yield b"," + json.dumps(node, ensure_ascii=False).encode("utf-8")
    yield b"]}"
