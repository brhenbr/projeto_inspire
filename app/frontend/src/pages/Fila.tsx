import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, type Busca } from "../api";
import { ESTADOS_CURADORIA, fmtNum } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Card, Empty, ErrorBox, Loading, Nota, Pagination } from "../ui";

export default function FilaPage() {
  const [sp, setSp] = useSearchParams();
  const page = Number(sp.get("pagina") ?? 1);
  const estado = sp.get("estado_curadoria") ?? "pendente";
  const dados = useApi(
    () => api.get<Busca>("/curadoria/fila", { ...Object.fromEntries(sp.entries()), estado_curadoria: estado, pagina: page, tamanho: 20 }),
    [sp.toString()],
  );
  const [sel, setSel] = useState<string[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const acao = useAction();

  function set(chave: string, valor: string) {
    const n = new URLSearchParams(sp);
    if (valor) n.set(chave, valor); else n.delete(chave);
    n.delete("pagina");
    setSp(n);
    setSel([]);
  }
  async function marcar(novo: string) {
    const r = await acao.run(() => api.post<{ alterados: number }>("/curadoria/status-em-lote", { ids: sel, estado: novo }));
    if (r) { setMsg(`${fmtNum(r.alterados)} conjunto(s) marcado(s) como “${ESTADOS_CURADORIA[novo]}”.`); setSel([]); dados.reload(); }
  }
  const d = dados.data;

  return (
    <main className="pagina">
      <h1>Fila de curadoria</h1>
      <p className="subtitulo">Conjuntos para curar, do mais prioritário ao menos: pior qualidade e mais usados vêm primeiro.</p>
      <div className="linha" style={{ marginBottom: 12 }}>
        <label>Mostrar{" "}
          <select value={estado} onChange={(e) => set("estado_curadoria", e.target.value)}>
            {Object.entries(ESTADOS_CURADORIA).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <input type="text" aria-label="Filtrar por organização (identificador)" placeholder="organização (ex.: ipea)" defaultValue={sp.get("organizacao") ?? ""} onBlur={(e) => set("organizacao", e.target.value.trim())} />
        {sp.get("organizacao") && <Badge tone="azul">organização: {sp.get("organizacao")}</Badge>}
      </div>
      {msg && <div className="ok" role="status">{msg}</div>}
      <ErrorBox error={acao.error} />
      {dados.loading && <Loading />}
      <ErrorBox error={dados.error} onRetry={dados.reload} />
      {d && (
        <Card
          title={`${fmtNum(d.total)} conjunto(s)`}
          actions={sel.length > 0 && (
            <>
              <span>{sel.length} selecionado(s):</span>
              <button className="botao botao-peq" type="button" disabled={acao.pending} onClick={() => marcar("em_revisao")}>Em revisão</button>
              <button className="botao botao-peq" type="button" disabled={acao.pending} onClick={() => marcar("aprovado")}>Aprovar</button>
              <button className="botao botao-sec botao-peq" type="button" disabled={acao.pending} onClick={() => marcar("rejeitado")}>Rejeitar</button>
            </>
          )}
        >
          {d.itens.length === 0 ? <Empty>Nada nesta fila.</Empty> : (
            <table>
              <thead>
                <tr>
                  <th><input type="checkbox" aria-label="Selecionar todos desta página" checked={sel.length === d.itens.length} onChange={(e) => setSel(e.target.checked ? d.itens.map((i) => i.id) : [])} /></th>
                  <th>Conjunto</th><th>Organização</th><th>Qualidade</th><th className="num">Prioridade</th>
                </tr>
              </thead>
              <tbody>
                {d.itens.map((c) => (
                  <tr key={c.id}>
                    <td><input type="checkbox" aria-label={`Selecionar ${c.titulo}`} checked={sel.includes(c.id)} onChange={(e) => setSel(e.target.checked ? [...sel, c.id] : sel.filter((x) => x !== c.id))} /></td>
                    <td><Link to={`/conjuntos/${c.id}`}>{c.titulo}</Link></td>
                    <td>{c.organizacao_titulo ?? "—"}</td>
                    <td><Nota value={c.nota_qualidade} /></td>
                    <td className="num">{c.prioridade === null ? "—" : fmtNum(c.prioridade)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Pagination page={d.pagina} total={d.total} size={d.tamanho} onChange={(p) => { const n = new URLSearchParams(sp); n.set("pagina", String(p)); setSp(n); setSel([]); }} />
        </Card>
      )}
    </main>
  );
}
