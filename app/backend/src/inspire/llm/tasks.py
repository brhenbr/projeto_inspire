"""Contexto público, tarefas parametrizáveis e validação da saída do modelo (ADR-0004, ADR-0011)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine, text

# ADR-0004, item 3: SÓ estes campos podem ir a um provedor. Contatos de responsáveis jamais.
PUBLIC_FIELDS = (
    "titulo",
    "descricao",
    "tags",
    "temas",
    "organizacao",
    "formatos",
    "licenca",
    "periodicidade",
)
CONTEXT_EXTRAS = (
    "temas_disponiveis",
)  # lista pública de temas do catálogo, só para a tarefa de tema
MAX_DESCRIPTION_CONTEXT = 4000
MAX_INSTRUCTIONS = 500


class PrivacyViolationError(Exception):
    """O contexto de um prompt continha algo fora da lista de campos públicos."""


@dataclass(frozen=True)
class TaskDef:
    chave: str
    nome: str
    descricao: str
    campo_alvo: str
    prompt_sistema: str
    prompt_usuario: str
    versao: int = 1


_SYSTEM = (
    "Você é um(a) curador(a) de metadados de dados abertos do governo brasileiro. Escreva em português do "
    "Brasil, com linguagem clara e objetiva, sem inventar fatos que não estejam nos metadados fornecidos. "
    "Responda SOMENTE com um objeto JSON válido, sem texto antes ou depois."
)
_CONTEXT = (
    "Metadados atuais do conjunto de dados:\n"
    "- Título: {titulo}\n- Organização: {organizacao}\n- Temas: {temas}\n- Palavras-chave: {tags}\n"
    "- Formatos dos recursos: {formatos}\n- Licença: {licenca}\n- Periodicidade: {periodicidade}\n"
    "- Descrição atual: {descricao}\n"
)

TASKS: tuple[TaskDef, ...] = (
    TaskDef(
        "melhorar-descricao",
        "Melhorar a descrição",
        "Reescreve a descrição para ficar completa e clara (mínimo de 100 caracteres), sem inventar fatos.",
        "descricao",
        _SYSTEM,
        _CONTEXT + '\nReescreva a descrição em 2 a 4 frases. Responda: {{"descricao": "<texto>"}}',
    ),
    TaskDef(
        "sugerir-tags",
        "Sugerir palavras-chave",
        "Sugere de 3 a 8 palavras-chave que ajudem a encontrar o conjunto, mantendo as existentes.",
        "tags",
        _SYSTEM,
        _CONTEXT + '\nSugira de 3 a 8 palavras-chave curtas. Responda: {{"tags": ["...", "..."]}}',
    ),
    TaskDef(
        "sugerir-tema",
        "Sugerir tema",
        "Escolhe, entre os temas oficiais do catálogo, os que melhor descrevem o conjunto.",
        "temas",
        _SYSTEM,
        _CONTEXT + "- Temas disponíveis (use somente estes identificadores): {temas_disponiveis}\n"
        '\nEscolha 1 a 3 temas. Responda: {{"temas": ["<identificador>"]}}',
    ),
)
TASKS_BY_KEY = {t.chave: t for t in TASKS}


def seed_tasks(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO curadoria.llm_tarefa (chave, nome, descricao, campo_alvo, prompt_sistema, prompt_usuario, versao) "
                "VALUES (:k, :n, :d, :c, :s, :u, :v) ON CONFLICT (chave) DO UPDATE SET nome = EXCLUDED.nome, "
                "descricao = EXCLUDED.descricao, campo_alvo = EXCLUDED.campo_alvo, prompt_sistema = EXCLUDED.prompt_sistema, "
                "prompt_usuario = EXCLUDED.prompt_usuario, versao = EXCLUDED.versao"
            ),
            [
                {
                    "k": t.chave,
                    "n": t.nome,
                    "d": t.descricao,
                    "c": t.campo_alvo,
                    "s": t.prompt_sistema,
                    "u": t.prompt_usuario,
                    "v": t.versao,
                }
                for t in TASKS
            ],
        )


def theme_options(engine: Engine) -> list[dict[str, str]]:
    with engine.connect() as conn:
        return [
            {"slug": r.slug, "titulo": r.titulo}
            for r in conn.execute(text("SELECT slug, titulo FROM catalogo.tema ORDER BY slug"))
        ]


def build_context(engine: Engine, dataset_id: str) -> dict[str, Any] | None:
    """Monta o contexto do prompt a partir de uma lista FIXA de campos públicos (valores efetivos)."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT titulo, descricao, tags, temas, organizacao_titulo, formatos, licenca, periodicidade "
                "FROM analitico.conjunto_busca WHERE id = :id AND NOT removido AND NOT sem_detalhe"
            ),
            {"id": dataset_id},
        ).first()
    if row is None:
        return None
    return {
        "titulo": row.titulo,
        "descricao": (row.descricao or "")[:MAX_DESCRIPTION_CONTEXT],
        "tags": list(row.tags),
        "temas": list(row.temas),
        "organizacao": row.organizacao_titulo,
        "formatos": list(row.formatos),
        "licenca": row.licenca,
        "periodicidade": row.periodicidade,
    }


def assert_public(context: dict[str, Any]) -> None:
    """Barreira final antes de qualquer envio: o contexto só pode ter campos públicos."""
    extra = set(context) - set(PUBLIC_FIELDS) - set(CONTEXT_EXTRAS)
    if extra:
        raise PrivacyViolationError(f"Campos fora da lista pública: {sorted(extra)}")


def _fmt(value: Any) -> str:
    if value in (None, "", []):
        return "(não informado)"
    return ", ".join(map(str, value)) if isinstance(value, list) else str(value)


def render(
    task: TaskDef, context: dict[str, Any], instructions: str | None = None
) -> tuple[str, str]:
    assert_public(context)
    shown = {k: _fmt(v) for k, v in context.items() if k != "temas_disponiveis"}
    shown["temas_disponiveis"] = ", ".join(
        f"{t['slug']} ({t['titulo']})" for t in context.get("temas_disponiveis", [])
    )
    user = task.prompt_usuario.format(**shown)
    if instructions and instructions.strip():
        user += (
            "\nInstruções adicionais do curador: " + instructions.strip()[:MAX_INSTRUCTIONS] + "\n"
        )
    return task.prompt_sistema, user


def extract_json(raw: str) -> dict[str, Any]:
    """Aceita JSON puro ou dentro de cercas de código; recusa qualquer outra coisa."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("A resposta do modelo não contém um objeto JSON")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("JSON inválido na resposta do modelo") from exc
    if not isinstance(data, dict):
        raise ValueError("A resposta do modelo não é um objeto JSON")
    return data


NO_INFO = re.compile(
    r"(descri[cç][aã]o|informa[cç][oõ]es)[^.]{0,40}\bn[aã]o\b[^.]{0,30}(informad|dispon[ií]ve|fornecid)"
    r"|\bn[aã]o (h[aá]|foram?|foi)\b[^.]{0,30}(informa[cç]|detalhes)",
    re.IGNORECASE,
)


def parse_output(task_key: str, raw: str, context: dict[str, Any], valid_themes: set[str]) -> Any:
    """Valida a saída do modelo (não confiável) e devolve o valor proposto para o campo-alvo."""
    data = extract_json(raw)
    if task_key == "melhorar-descricao":
        value = data.get("descricao")
        if not isinstance(value, str) or not 40 <= len(value.strip()) <= 2000:
            raise ValueError("Descrição ausente ou fora do tamanho esperado (40 a 2000 caracteres)")
        if NO_INFO.search(value):
            raise ValueError("O modelo disse que faltam informações em vez de descrever o conjunto")
        return value.strip()
    if task_key == "sugerir-tags":
        tags = data.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise ValueError("'tags' deve ser uma lista de textos")
        cleaned = {t.strip() for t in tags if t.strip() and len(t.strip()) <= 60}
        if not cleaned:
            raise ValueError("Nenhuma palavra-chave utilizável")
        return sorted(cleaned | set(context.get("tags") or []))[:50]
    if task_key == "sugerir-tema":
        themes = data.get("temas")
        if (
            not isinstance(themes, list)
            or not themes
            or not all(isinstance(t, str) for t in themes)
        ):
            raise ValueError("'temas' deve ser uma lista não vazia de identificadores")
        unknown = [t for t in themes if t not in valid_themes]
        if unknown:
            raise ValueError(f"Tema(s) fora da lista oficial: {', '.join(unknown)}")
        return sorted(set(themes))
    raise ValueError(f"Tarefa desconhecida: {task_key}")
