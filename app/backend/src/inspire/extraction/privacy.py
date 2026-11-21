"""Remoção de dados pessoais na ingestão (ADR-0002, item 7; modelo-de-dados.md, seção 2).

Nome e/ou e-mail do responsável pelo conjunto vêm em muitos detalhes do portal. Eles são removidos ANTES de
gravar o bruto e antes de calcular o hash; guarda-se apenas se existiam.

Limite conhecido: campos de texto livre (como a descrição) podem conter e-mails digitados pelo órgão. Eles
não são alterados aqui; ver ``find_email_like`` para medir a ocorrência.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from inspire.extraction.errors import PersonalDataError

# Comparação sem diferenciar maiúsculas/minúsculas nem "_" e "-".
PERSONAL_KEYS = frozenset({"responsavel", "emailresponsavel", "maintainer", "maintaineremail"})

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _norm(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "")


def strip_personal_data(detail: dict[str, Any]) -> dict[str, Any]:
    """Devolve uma cópia sem os contatos pessoais, com marcadores de que existiam."""
    clean = copy.deepcopy(detail)
    had_name = bool(clean.pop("responsavel", None))
    had_email = bool(clean.pop("emailResponsavel", None))
    clean["temResponsavel"] = had_name
    clean["temEmailResponsavel"] = had_email
    _drop_personal_keys(clean)
    return clean


def _drop_personal_keys(node: Any) -> None:
    if isinstance(node, dict):
        for key in [k for k in node if _norm(str(k)) in PERSONAL_KEYS]:
            del node[key]
        for value in node.values():
            _drop_personal_keys(value)
    elif isinstance(node, list):
        for item in node:
            _drop_personal_keys(item)


def assert_no_personal_data(payload: Any) -> None:
    """Barreira final antes de gravar: falha se algum campo pessoal sobreviveu, em qualquer nível."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if _norm(str(key)) in PERSONAL_KEYS:
                raise PersonalDataError(f"Campo pessoal '{key}' não pode ser gravado")
            assert_no_personal_data(value)
    elif isinstance(payload, list):
        for item in payload:
            assert_no_personal_data(item)


def find_email_like(payload: Any) -> int:
    """Conta textos com cara de e-mail em campos livres (para o relatório, sem alterá-los)."""
    if isinstance(payload, str):
        return len(_EMAIL.findall(payload))
    if isinstance(payload, dict):
        return sum(find_email_like(v) for v in payload.values())
    if isinstance(payload, list):
        return sum(find_email_like(v) for v in payload)
    return 0
