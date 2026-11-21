import { useState } from "react";

import { api, type LlmEstado, type Regra, type Saude } from "../api";
import { fmtDate } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Card, ErrorBox, Loading } from "../ui";

type Recalculo = { em_andamento: boolean; iniciado_em: string | null; finalizado_em: string | null; pontuados: number | null; erro: string | null };

export default function ConfiguracoesPage() {
  const regras = useApi(() => api.get<Regra[]>("/qualidade/regras"), []);
  const recalc = useApi(() => api.get<Recalculo>("/qualidade/recalculo"), [], 2000);
  const saude = useApi(() => api.get<Saude>("/saude"), []);
  const llm = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const [edicoes, setEdicoes] = useState<Record<string, { peso?: number; ativa?: boolean }>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const acao = useAction();

  const alterado = Object.keys(edicoes).length > 0;
  async function salvar() {
    for (const [chave, v] of Object.entries(edicoes)) {
      const r = await acao.run(() => api.put(`/qualidade/regras/${chave}`, v));
      if (r === undefined) return;
    }
    setEdicoes({});
    setMsg("Regras salvas. Clique em “Recalcular notas” para aplicar aos conjuntos.");
    regras.reload();
  }
  async function recalcular() {
    const r = await acao.run(() => api.post<Recalculo>("/qualidade/recalcular"));
    if (r) { setMsg("Recálculo iniciado."); recalc.reload(); }
  }
  const porDimensao = (regras.data ?? []).reduce<Record<string, Regra[]>>((acc, r) => { (acc[r.dimensao] ??= []).push(r); return acc; }, {});

  return (
    <main className="pagina">
      <h1>Configurações</h1>
      <p className="subtitulo">Regras de qualidade dos metadados (DQV, FAIR e DMBOK), com pesos ajustáveis.</p>
      {msg && <div className="ok" role="status">{msg}</div>}
      <ErrorBox error={acao.error} />
      {regras.loading && <Loading />}
      <ErrorBox error={regras.error} onRetry={regras.reload} />

      <Card
        title="Regras de qualidade"
        actions={
          <>
            <button className="botao" type="button" disabled={!alterado || acao.pending} onClick={salvar}>Salvar alterações</button>
            <button className="botao botao-sec" type="button" disabled={recalc.data?.em_andamento || acao.pending} onClick={recalcular}>Recalcular notas</button>
          </>
        }
      >
        {recalc.data?.em_andamento && <div className="info" role="status">Recalculando as notas…</div>}
        {recalc.data && !recalc.data.em_andamento && recalc.data.finalizado_em && (
          <p className="subtitulo">Último recálculo: {fmtDate(recalc.data.finalizado_em, true)}{recalc.data.pontuados !== null ? ` · ${recalc.data.pontuados} conjuntos` : ""}{recalc.data.erro ? ` · erro: ${recalc.data.erro}` : ""}</p>
        )}
        {Object.entries(porDimensao).map(([dim, lista]) => (
          <div key={dim}>
            <h3>{dim}</h3>
            <table>
              <thead><tr><th>Ativa</th><th>Regra</th><th>Descrição</th><th>Fonte</th><th className="num">Peso</th></tr></thead>
              <tbody>
                {lista.map((r) => {
                  const ed = edicoes[r.chave] ?? {};
                  const ativa = ed.ativa ?? r.ativa;
                  const peso = ed.peso ?? r.peso;
                  return (
                    <tr key={r.chave}>
                      <td><input type="checkbox" aria-label={`Ativar ${r.nome}`} checked={ativa} onChange={(ev) => setEdicoes({ ...edicoes, [r.chave]: { ...ed, ativa: ev.target.checked } })} /></td>
                      <td><code>{r.chave}</code> {r.nome}</td>
                      <td>{r.descricao}</td>
                      <td className="subtitulo">{r.fonte}</td>
                      <td className="num"><input type="number" min={0} max={10} step={0.5} style={{ width: 70 }} aria-label={`Peso de ${r.nome}`} value={peso} onChange={(ev) => setEdicoes({ ...edicoes, [r.chave]: { ...ed, peso: Number(ev.target.value) } })} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </Card>

      <Card title="Sobre o sistema">
        <ul>
          <li>Versão: {saude.data?.versao ?? "—"} · API: {saude.data?.status === "ok" ? "funcionando" : "com problemas"} · Banco: {saude.data?.banco === "ok" ? "funcionando" : "indisponível"}</li>
          <li>LLM: {llm.data?.habilitado ? <>{llm.data.simulado ? "modo simulado" : llm.data.externo ? "provedor externo" : "provedor local"} <Badge>{llm.data.provedor}</Badge></> : "desligado"}</li>
          <li>Dados pessoais de contato dos responsáveis dos conjuntos não são armazenados.</li>
        </ul>
      </Card>
    </main>
  );
}
