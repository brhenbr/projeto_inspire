"""Hash determinístico de documentos, para detectar mudanças entre extrações."""

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """JSON canônico: chaves ordenadas, sem espaços, sem escapar acentos."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
