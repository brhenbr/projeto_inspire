"""Interpretação de linguagem natural em filtros da busca (ADR-0016).

O LLM NÃO busca nem responde sobre os dados: ele só traduz o texto do usuário em filtros que a busca existente
executa. Por isso: (1) só o texto do usuário e o vocabulário público (temas, formatos, UFs) vão ao provedor,
nunca dados do catálogo curado nem contatos; (2) a saída é validada contra o vocabulário e o que não existe é
descartado e informado; (3) o usuário vê e pode editar os filtros usados.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Engine, text

from inspire.discovery.search import Filters
from inspire.llm.providers import LlmError, LlmProvider, LlmRequest

MAX_TEXT = 500
TASK = "interpretar-pergunta"
ESFERAS = ("federal", "estadual", "municipal")
PERIODICIDADES = (
    "DIARIA",
    "SEMANAL",
    "QUINZENAL",
    "MENSAL",
    "TRIMESTRAL",
    "QUADRIMESTRAL",
    "SEMESTRAL",
    "ANUAL",
    "SOB_DEMANDA",
    "OUTRAS",
)
UFS = {
    "AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas", "BA": "bahia", "CE": "ceara",
    "DF": "distrito federal", "ES": "espirito santo", "GO": "goias", "MA": "maranhao",
    "MT": "mato grosso", "MS": "mato grosso do sul", "MG": "minas gerais", "PA": "para",
    "PB": "paraiba", "PR": "parana", "PE": "pernambuco", "PI": "piaui", "RJ": "rio de janeiro",
    "RN": "rio grande do norte", "RS": "rio grande do sul", "RO": "rondonia", "RR": "roraima",
    "SC": "santa catarina", "SP": "sao paulo", "SE": "sergipe", "TO": "tocantins",
}  # fmt: skip
GENERIC = frozenset(
    ["dados", "dado", "conjunto", "conjuntos", "base", "bases", "banco", "informacao", "informacoes", "politica", "politicas", "estudo", "estudos", "sociais", "social", "governo", "federal", "publico", "publica", "brasil", "brasileiro", "registro", "registros"]
)  # fmt: skip
SYSTEM = (
    "Você traduz pedidos em português sobre dados abertos do governo brasileiro em filtros de busca. "
    "Responda SOMENTE com um objeto JSON, sem texto fora dele. Use apenas os valores permitidos informados; "
    "omita o que o pedido não menciona. Não invente."
)
USER = """Pedido do usuário: {pergunta}

Campos possíveis do JSON:
- "q": só termos específicos do assunto que NÃO estejam cobertos pelos outros campos (não repita o tema, o órgão nem o estado; não use palavras genéricas como "dados", "conjunto", "base", "política", "estudo", "informação"; só um termo concreto); omita se não houver
- "tema": um ou mais slugs de tema separados por vírgula (basta casar um deles), entre: {temas}. Use só se o pedido citar o assunto; não deduza tema a partir do nome do órgão
- "formato": um formato de arquivo, entre: {formatos}
- "esfera": {esferas} (só se o pedido disser explicitamente)
- "uf": sigla de estado (ex.: SP)
- "organizacao": nome ou sigla do órgão publicador, se citado
- "periodicidade": entre: {periodicidades}
- "nota_min": número de 0 a 100, só se pedirem qualidade mínima
- "nome": título curto (até 6 palavras) que resuma o pedido, para nomear uma coleção
- "explicacao": uma frase curta em português dizendo como entendeu o pedido
"""


@dataclass
class Interpretation:
    filtros: dict[str, Any]
    explicacao: str
    ignorados: list[str] = field(default_factory=list)
    organizacao: dict[str, str] | None = None
    resposta_bruta: str = ""
    nome: str = ""


def normalize(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value.lower())
    return "".join(c for c in plain if not unicodedata.combining(c))


def vocabulary(engine: Engine) -> dict[str, Any]:
    """Valores públicos que o modelo pode usar; leva poucos centavos de tokens e nada de dados sensíveis."""
    with engine.connect() as conn:
        themes = [
            {"slug": r.slug, "titulo": r.titulo}
            for r in conn.execute(text("SELECT slug, titulo FROM catalogo.tema ORDER BY slug"))
        ]
        formats = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT f FROM (SELECT unnest(formatos) AS f, count(*) AS n FROM analitico.conjunto_busca "
                    "GROUP BY 1 ORDER BY 2 DESC LIMIT 25) t ORDER BY n DESC"
                )
            )
        ]
    return {"temas": themes, "formatos": formats}


def build_request(question: str, vocab: dict[str, Any]) -> LlmRequest:
    user = USER.format(
        pergunta=question,
        temas=", ".join(t["slug"] for t in vocab["temas"]),
        formatos=", ".join(vocab["formatos"]),
        esferas=" | ".join(ESFERAS),
        periodicidades=", ".join(PERIODICIDADES),
    )
    return LlmRequest(system=SYSTEM, user=user, task=TASK, context={"pergunta": question, **vocab})


def simulate(context: dict[str, Any]) -> dict[str, Any]:
    """Modo simulado (sem IA): reconhece temas, formatos, esfera e UF citados e usa o resto como palavras-chave."""
    from inspire.llm.providers import STOPWORDS

    question = normalize(str(context.get("pergunta") or ""))
    words = re.findall(r"[a-z0-9]+", question)
    out: dict[str, Any] = {}
    used: set[str] = set()
    found_themes = []
    for theme in context.get("temas") or []:
        title = normalize(theme["titulo"])
        if title in question or theme["slug"].replace("-", " ") in question:
            found_themes.append(theme["slug"])
            used.update(re.findall(r"[a-z0-9]+", title))
    if found_themes:
        out["tema"] = ",".join(found_themes)
    for fmt in context.get("formatos") or []:
        if normalize(fmt) in words:
            out["formato"] = fmt.upper()
            used.add(normalize(fmt))
            break
    for esfera in ESFERAS:
        if esfera in words:
            out["esfera"] = esfera
            used.add(esfera)
    for uf, name in sorted(UFS.items(), key=lambda kv: -len(kv[1])):
        if re.search(rf"\b{name}\b", question):
            out["uf"] = uf
            used.update(name.split())
            break
    keywords = [w for w in words if len(w) >= 5 and w not in used and w not in STOPWORDS]
    if keywords:
        out["q"] = " ".join(keywords[:3])
    out["nome"] = " ".join(words[:6]).capitalize()
    out["explicacao"] = "Interpretação simulada por regras simples (sem IA)."
    return out


def parse_json(raw: str) -> dict[str, Any]:
    body = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("A resposta do modelo não trouxe um objeto JSON")
    data = json.loads(body[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("A resposta do modelo não é um objeto JSON")
    return data


def _resolve_organization(engine: Engine, name: str) -> dict[str, str] | None:
    """Casa o nome citado com uma organização real (sem acento; a maior em número de conjuntos)."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT slug, titulo FROM catalogo.organizacao "
                "WHERE public.f_unaccent(lower(titulo)) LIKE '%' || public.f_unaccent(lower(:n)) || '%' "
                "ORDER BY qtd_declarada DESC LIMIT 1"
            ),
            {"n": name[:120]},
        ).first()
    return {"slug": row.slug, "titulo": row.titulo} if row else None


def validate(engine: Engine, raw: dict[str, Any], vocab: dict[str, Any]) -> Interpretation:
    """Mantém só o que existe no vocabulário; o resto vai para `ignorados` (o usuário é avisado)."""
    filters: dict[str, Any] = {}
    ignored: list[str] = []
    themes = {t["slug"] for t in vocab["temas"]}
    formats = {f.upper() for f in vocab["formatos"]}

    def pick(key: str, allowed: set[str] | tuple[str, ...], transform: Any = str) -> None:
        value = raw.get(key)
        if value in (None, ""):
            return
        value = transform(value)
        if value in allowed:
            filters[key] = value
        else:
            ignored.append(f"{key}: “{raw.get(key)}” não existe no catálogo")

    wanted = [t.strip().lower() for t in re.split(r"[,;]", str(raw.get("tema") or "")) if t.strip()]
    valid = [t for t in dict.fromkeys(wanted) if t in themes]
    if valid:
        filters["tema"] = ",".join(valid)
    ignored += [
        f"tema: “{t}” não existe no catálogo" for t in dict.fromkeys(wanted) if t not in themes
    ]
    pick("formato", formats, lambda v: str(v).strip().upper().lstrip("."))
    pick("esfera", set(ESFERAS), lambda v: str(v).strip().lower())
    pick("uf", set(UFS), lambda v: str(v).strip().upper())
    pick("periodicidade", set(PERIODICIDADES), lambda v: str(v).strip().upper())
    terms = re.sub(r"[,;]", " ", str(raw.get("q") or "")).split()  # vírgula não é parte do termo
    q = " ".join(t for t in terms if normalize(t) not in GENERIC)[
        :200
    ]  # genérica só restringe à toa
    if q and not re.fullmatch(r"\W*", q):
        filters["q"] = q
    organization = None
    if name := str(raw.get("organizacao") or "").strip():
        organization = _resolve_organization(engine, name)
        if organization:
            filters["organizacao"] = organization["slug"]
        else:
            ignored.append(f"organizacao: “{name}” não encontrada")
    try:
        if raw.get("nota_min") not in (None, ""):
            filters["nota_min"] = max(0.0, min(100.0, float(raw["nota_min"])))
    except (TypeError, ValueError):
        ignored.append("nota_min: valor inválido")
    name = " ".join(str(raw.get("nome") or "").split())[:80].strip(" .:;,-")
    return Interpretation(
        nome=name,
        filtros=filters,
        explicacao=str(raw.get("explicacao") or "").strip()[:300],
        ignorados=ignored,
        organizacao=organization,
    )


def interpret(engine: Engine, provider: LlmProvider, question: str) -> Interpretation:
    question = " ".join(question.split())[:MAX_TEXT]
    if not question:
        raise ValueError("Escreva uma pergunta ou um pedido")
    vocab = vocabulary(engine)
    response = provider.complete(build_request(question, vocab))
    try:
        result = validate(engine, parse_json(response.text), vocab)
    except (ValueError, json.JSONDecodeError) as exc:
        raise LlmError(f"Não consegui entender a resposta do modelo ({exc})") from exc
    result.resposta_bruta = response.text[:2000]
    if not result.filtros:
        result.explicacao = (
            result.explicacao or "Não identifiquei filtros; mostrando todo o catálogo."
        )
    return result


# Filtros que o modelo costuma inferir sem o usuário ter pedido; são soltos primeiro quando não há resultado.
RELAX_ORDER = ("periodicidade", "esfera", "nota_min", "formato", "tema", "uf", "organizacao", "q")


def search_relaxed(
    engine: Engine, filters: dict[str, Any], *, size: int
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Busca; se vier vazia, solta um filtro por vez (na ordem acima) e informa quais foram soltos."""
    from inspire.discovery.search import SearchService

    current = dict(filters)
    removed: list[str] = []
    service = SearchService(engine)
    while True:
        found = service.search(Filters.from_dict(current), size=size)
        if found["total"] > 0 or not current:
            return found, current, removed
        key = next((k for k in RELAX_ORDER if k in current), None)
        if key is None:
            return found, current, removed
        removed.append(key)
        del current[key]


def to_filters(interpretation: Interpretation) -> Filters:
    return Filters.from_dict(interpretation.filtros)
