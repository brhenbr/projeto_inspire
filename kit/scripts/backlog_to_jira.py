"""Converte um backlog em JSON para CSV importável no Jira e para Markdown.

Uso:
    python -I backlog_to_jira.py backlog.json saida_dir

Formato do JSON: lista de itens com id, tipo (Epic/Story/Task/Spike...), titulo, descricao,
prioridade, labels (lista) e, opcionalmente, pai (id do épico).
Sem dependências além da biblioteca padrão.
"""
import csv
import json
import sys
from pathlib import Path

PRIORIDADES = ["Highest", "High", "Medium", "Low", "Lowest"]
# Jira não tem o tipo "Spike" por padrão; mapeamos para Task e marcamos com label.
TIPO_JIRA = {"Spike": "Task"}


def main(origem: str, destino: str) -> None:
    itens = json.loads(Path(origem).read_text(encoding="utf-8"))
    ids = [i["id"] for i in itens]
    assert len(ids) == len(set(ids)), "ids duplicados"
    for i in itens:
        assert i.get("prioridade", "Medium") in PRIORIDADES, i["id"]
        assert i.get("pai") is None or i["pai"] in ids, f"pai inexistente em {i['id']}"

    out = Path(destino)
    out.mkdir(parents=True, exist_ok=True)
    max_labels = max(len(i.get("labels", [])) for i in itens)

    with open(out / "backlog-jira.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Issue Id", "Issue Type", "Summary", "Description", "Priority"]
                   + ["Labels"] * max_labels + ["Epic Name", "Parent"])
        for i in itens:
            labels = list(i.get("labels", []))
            if i["tipo"] == "Spike":
                labels.append("spike")
            labels += [""] * (max_labels - len(labels))
            tipo = TIPO_JIRA.get(i["tipo"], i["tipo"])
            w.writerow([i["id"], tipo, i["titulo"], i.get("descricao", ""),
                        i.get("prioridade", "Medium")] + labels[:max_labels]
                       + [i["titulo"] if tipo == "Epic" else "", i.get("pai", "")])

    linhas = ["# Backlog", "", "Gerado por `kit/scripts/backlog_to_jira.py` a partir de `backlog.json`. "
              "Não edite este arquivo à mão.", ""]
    for ep in (i for i in itens if i["tipo"] == "Epic"):
        linhas += [f"## {ep['id']} — {ep['titulo']}", "",
                   f"*{ep['prioridade']} · {', '.join(ep.get('labels', []))}*", "", ep.get("descricao", ""), ""]
        for it in (i for i in itens if i.get("pai") == ep["id"]):
            marca = f" ✔ {it['status']}" if it.get("status") else ""
            linhas.append(f"- **{it['id']}** ({it['tipo']}, {it['prioridade']}, "
                          f"{', '.join(it.get('labels', []))}) — {it['titulo']}{marca}")
        linhas.append("")
    (out / "backlog.md").write_text("\n".join(linhas), encoding="utf-8")
    print(f"{len(itens)} itens ({sum(i['tipo']=='Epic' for i in itens)} épicos) -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
