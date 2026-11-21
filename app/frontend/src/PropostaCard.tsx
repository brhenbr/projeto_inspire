import { useState } from "react";
import { Link } from "react-router-dom";

import { api, type LlmProposta } from "./api";
import { CAMPOS, ESTADOS_PROPOSTA, fmtValue } from "./format";
import { useAction } from "./hooks";
import { Badge, ErrorBox } from "./ui";

const asEditable = (v: unknown): string => (Array.isArray(v) ? v.join(", ") : v === null || v === undefined ? "" : String(v));

function fromEditable(campo: string, text: string): unknown {
  if (campo === "tags" || campo === "temas") return text.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
  return text.trim();
}

export default function PropostaCard({ p, onDone, selected, onSelect }: {
  p: LlmProposta;
  onDone: () => void;
  selected?: boolean;
  onSelect?: (checked: boolean) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(asEditable(p.valor_proposto));
  const acao = useAction();
  const pendente = p.estado === "pendente";

  async function decidir(decisao: "aprovar" | "editar" | "rejeitar") {
    const body = decisao === "editar" ? { decisao, valor: fromEditable(p.campo, text) } : { decisao };
    const r = await acao.run(() => api.post(`/llm/propostas/${p.id}/decidir`, body));
    if (r !== undefined) {
      setEditing(false);
      onDone();
    } else {
      onDone(); // o erro (ex.: proposta desatualizada) já está na tela; recarrega o estado
    }
  }

  return (
    <article className="resultado" aria-label={`Proposta ${p.id}`}>
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>
          {onSelect && pendente && (
            <input type="checkbox" aria-label={`Selecionar proposta ${p.id}`} checked={!!selected} onChange={(e) => onSelect(e.target.checked)} style={{ marginRight: 8 }} />
          )}
          <Link to={`/conjuntos/${p.conjunto_id}`}>{p.conjunto_titulo ?? p.conjunto_id}</Link>
        </h3>
        <div className="linha">
          <Badge tone="azul">{CAMPOS[p.campo] ?? p.campo}</Badge>
          <Badge tone={pendente ? "medio" : p.estado === "aprovada" || p.estado === "editada" ? "bom" : p.estado === "erro" || p.estado === "desatualizada" ? "ruim" : "neutro"}>
            {ESTADOS_PROPOSTA[p.estado] ?? p.estado}
          </Badge>
          <Badge title="Quem gerou a sugestão">{p.provedor}{p.modelo ? ` · ${p.modelo}` : ""}{p.externo ? " · EXTERNO" : p.provedor === "simulado" ? " · simulado" : " · local"}</Badge>
        </div>
      </div>
      {p.erro ? (
        <p className="erro" role="note">{p.erro}</p>
      ) : (
        <div className="comparar" style={{ marginTop: 10 }}>
          <div><strong>Valor atual</strong><div className="diff-antes">{fmtValue(p.valor_original)}</div></div>
          <div><strong>Sugestão</strong><div className="diff-depois">{fmtValue(p.valor_final ?? p.valor_proposto)}</div></div>
        </div>
      )}
      <ErrorBox error={acao.error} />
      {pendente && !p.erro && (
        <div className="linha" style={{ marginTop: 10 }}>
          {editing ? (
            <>
              <textarea aria-label={`Valor editado da proposta ${p.id}`} value={text} onChange={(e) => setText(e.target.value)} />
              <button className="botao" type="button" disabled={acao.pending} onClick={() => decidir("editar")}>Salvar edição e aplicar</button>
              <button className="botao botao-sec" type="button" onClick={() => setEditing(false)}>Cancelar</button>
            </>
          ) : (
            <>
              <button className="botao" type="button" disabled={acao.pending} onClick={() => decidir("aprovar")}>Aprovar</button>
              <button className="botao botao-sec" type="button" onClick={() => setEditing(true)}>Editar</button>
              <button className="botao botao-perigo" type="button" disabled={acao.pending} onClick={() => decidir("rejeitar")}>Rejeitar</button>
            </>
          )}
        </div>
      )}
    </article>
  );
}
