import { api } from "./api";
import { useApi } from "./hooks";
import { Badge } from "./ui";

export type Filtros = Record<string, string | number | boolean>;
export const ROTULOS: Record<string, string> = {
  q: "Palavras", tema: "Tema", formato: "Formato", esfera: "Esfera", uf: "UF", organizacao: "Órgão",
  periodicidade: "Periodicidade", nota_min: "Nota mínima", licenca: "Licença",
};

/** Etiquetas dos filtros: um chip por tema (com o nome do tema) e, se `onChange` existir, um × em cada uma. */
export function FiltroChips({ filtros, organizacao, onChange, rotulo = "Filtros" }: {
  filtros: Filtros;
  organizacao?: { slug: string; titulo: string } | null;
  onChange?: (novos: Filtros) => void;
  rotulo?: string;
}) {
  const temas = useApi(() => api.get<{ slug: string; titulo: string }[]>("/temas"), []);
  const tituloTema = (slug: string) => temas.data?.find((t) => t.slug === slug)?.titulo ?? slug;
  const chips: { chave: string; valor?: string; texto: string }[] = [];
  for (const [k, v] of Object.entries(filtros)) {
    if (k === "tema") {
      for (const slug of String(v).split(",").filter(Boolean)) chips.push({ chave: k, valor: slug, texto: `Tema: ${tituloTema(slug)}` });
    } else {
      const texto = k === "organizacao" && organizacao?.slug === v ? organizacao.titulo : String(v);
      chips.push({ chave: k, texto: `${ROTULOS[k] ?? k}: ${texto}` });
    }
  }
  function remover(chave: string, valor?: string) {
    const novos = { ...filtros };
    if (chave === "tema" && valor) {
      const restantes = String(novos.tema).split(",").filter((s) => s && s !== valor);
      if (restantes.length) novos.tema = restantes.join(","); else delete novos.tema;
    } else delete novos[chave];
    onChange?.(novos);
  }
  return (
    <div className="chips" aria-label={rotulo}>
      {chips.length === 0 && <Badge>nenhum filtro</Badge>}
      {chips.map((c) => (
        <Badge key={`${c.chave}:${c.valor ?? ""}`} tone="azul">
          {c.texto}
          {onChange && <button type="button" className="chip-x" aria-label={`Remover ${c.texto}`} onClick={() => remover(c.chave, c.valor)}>×</button>}
        </Badge>
      ))}
    </div>
  );
}
