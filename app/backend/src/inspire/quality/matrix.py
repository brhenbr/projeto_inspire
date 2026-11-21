"""Gera a matriz de qualidade (US-023) a partir das próprias regras, para a documentação nunca divergir do código."""

from __future__ import annotations

from collections import defaultdict

from inspire.quality.rules import GRACE, OPEN_FORMATS, OPEN_LICENSES, PERIOD_DAYS, RULES


def render_markdown() -> str:
    by_dim = defaultdict(list)
    for r in RULES:
        by_dim[r.dimension].append(r)
    lines = [
        "# Matriz de qualidade dos metadados",
        "",
        "> Gerado por `python -m inspire.cli matriz-qualidade` a partir do código. **Não edite à mão**; "
        "para mudar pesos use a tela de configurações, e para mudar regras altere `quality/rules.py`.",
        "",
        "**Em palavras simples:** cada conjunto recebe uma nota de 0 a 100 conforme cumpre uma lista de "
        "verificações simples (tem descrição? informa a licença? os dados estão atualizados? há formato aberto?). "
        "Cada verificação tem um peso. Quando falta informação para julgar uma verificação, ela fica de fora da "
        "conta em vez de punir o conjunto. Os pesos abaixo são um ponto de partida e podem ser ajustados.",
        "",
        "Decisão e alternativas: [ADR-0009](../03-decisoes/0009-modelo-de-qualidade.md). Padrões de referência "
        "definidos pelo projeto: **DCAT-BR**, **DQV** e princípios **FAIR**; na dúvida, **DMBOK**.",
        "",
        "## Como a nota é calculada",
        "- `nota = 100 * (soma dos pesos das regras aprovadas) / (soma dos pesos das regras avaliáveis e ativas)`.",
        "- A nota por dimensão usa a mesma conta restrita às regras da dimensão.",
        "- A nota usa os valores **efetivos** (já com a curadoria): melhorar um metadado sobe a nota.",
        "- Conjuntos removidos do portal ou sem detalhe disponível não recebem nota.",
        "",
    ]
    for dim, rules in by_dim.items():
        lines += [f"## {dim}", "", "| Regra | Verificação | Peso | Fonte |", "|---|---|---|---|"]
        lines += [
            f"| `{r.key}` {r.name} | {r.description} | {r.weight:g} | {r.source} |" for r in rules
        ]
        lines.append("")
    lines += [
        "## Parâmetros das regras",
        f"- **Formatos abertos reconhecidos:** {', '.join(sorted(OPEN_FORMATS))}.",
        f"- **Licenças reconhecidas como abertas:** {', '.join(sorted(OPEN_LICENSES))}.",
        f"- **Folga de atualidade:** {int((GRACE - 1) * 100)}% sobre o intervalo da periodicidade. Intervalos (dias): "
        + ", ".join(f"{k.title()} {v}" for k, v in PERIOD_DAYS.items())
        + ".",
        "",
        "## Limites conhecidos",
        "- Regras binárias são grosseiras (uma descrição com 99 caracteres reprova); gradação é possível no futuro.",
        "- **Disponibilidade real dos links** (o link responde?) não é verificada: fica para a fase 2 (EP-08). "
        "Hoje só se verifica se o link é um endereço http(s) bem formado.",
        "- A mensuração de aderência ao DCAT-BR (propriedades obrigatórias e recomendadas) entra com o épico EP-11; "
        "a especificação oficial v1.0 do Catálogo Nacional de Dados deve ser lida e mapeada antes (US-100).",
        "- Os pesos não foram validados com o cliente nem com o CPQD.",
        "",
    ]
    return "\n".join(lines)
