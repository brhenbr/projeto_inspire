"""Gera uma página HTML única com todos os diagramas Mermaid encontrados nos .md de uma pasta.

Uso:
    python -I gerar_visualizador.py docs docs/diagramas.html

Requer `mermaid.min.js` (licença MIT) em <pasta de saída>/assets/. A página funciona offline:
basta abrir o HTML no navegador. Sem dependências além da biblioteca padrão.
"""
import html
import re
import sys
from pathlib import Path

BLOCO = re.compile(r"```mermaid\s*\n(.*?)\n```", re.S)
TITULO = re.compile(r"^#\s+(.+)$", re.M)


def coletar(raiz: Path):
    for md in sorted(raiz.rglob("*.md")):
        texto = md.read_text(encoding="utf-8")
        blocos = BLOCO.findall(texto)
        if not blocos:
            continue
        m = TITULO.search(texto)
        yield md, (m.group(1) if m else md.stem), blocos


def main(raiz: str, saida: str) -> None:
    raiz_p, saida_p = Path(raiz), Path(saida)
    if not (saida_p.parent / "assets" / "mermaid.min.js").exists():
        sys.exit(f"Falta {saida_p.parent / 'assets' / 'mermaid.min.js'}")
    secoes, indice, total = [], [], 0
    for n, (md, titulo, blocos) in enumerate(coletar(raiz_p)):
        rel = md.relative_to(saida_p.parent).as_posix()
        itens = "".join(
            f'<div class="diagrama"><pre class="mermaid">{html.escape(b)}</pre></div>' for b in blocos
        )
        total += len(blocos)
        indice.append(f'<li><a href="#s{n}">{html.escape(titulo)}</a> ({len(blocos)})</li>')
        secoes.append(
            f'<section id="s{n}"><h2>{html.escape(titulo)}</h2>'
            f'<p class="fonte">Fonte: <a href="{html.escape(rel)}">{html.escape(rel)}</a></p>{itens}</section>'
        )
    pagina = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Diagramas do projeto</title>
<style>
body{{font-family:system-ui,Segoe UI,sans-serif;margin:0;background:#f5f6f8;color:#1c2330}}
header{{background:#08427b;color:#fff;padding:16px 32px}} header h1{{margin:0;font-size:20px}}
main{{max-width:1300px;margin:0 auto;padding:24px 32px}}
nav ul{{columns:2}} section{{margin:32px 0}} .fonte{{color:#667;font-size:13px}}
.diagrama{{background:#fff;border:1px solid #d9dde3;border-radius:8px;padding:16px;margin:16px 0;overflow:auto}}
</style></head><body>
<header><h1>Diagramas do projeto ({total})</h1></header>
<main><nav><ul>{''.join(indice)}</ul></nav>{''.join(secoes)}</main>
<script src="assets/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,securityLevel:"strict",theme:"default",flowchart:{{useMaxWidth:false}}}});</script>
</body></html>"""
    saida_p.write_text(pagina, encoding="utf-8")
    print(f"{total} diagramas de {len(secoes)} arquivos -> {saida_p}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
