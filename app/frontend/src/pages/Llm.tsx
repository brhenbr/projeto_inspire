import { useState } from "react";

import { api, type Busca, type Colecao, type LlmEstado, type LlmExecucao, type LlmProposta, type LlmTarefa } from "../api";
import PropostaCard from "../PropostaCard";
import { fmtDate, fmtNum } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Bar, Card, Empty, ErrorBox, Loading, Pagination } from "../ui";

const ESTADOS_EXEC: Record<string, string> = { enfileirada: "Na fila", em_andamento: "Em andamento", concluida: "Concluída", falhou: "Falhou", cancelada: "Cancelada" };

export default function LlmPage() {
  const estado = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const e = estado.data;
  return (
    <main className="pagina">
      <h1>Sugestões de LLM</h1>
      <p className="subtitulo">Você escolhe a tarefa e os conjuntos; o modelo propõe; <strong>nada muda no catálogo sem a sua aprovação</strong>.</p>
      {estado.loading && <Loading />}
      <ErrorBox error={estado.error} onRetry={estado.reload} />
      {e && !e.habilitado && (
        <Card title="Recurso desligado">
          <p>{e.motivo}</p>
          <p className="subtitulo">Para usar, defina <code>LLM_ENABLED=true</code> (o modo simulado funciona sem chave e sem rede). Veja a documentação (ADR-0011).</p>
        </Card>
      )}
      {e?.habilitado && (
        <>
          <Card title="Provedor em uso">
            <div className="chips">
              <Badge tone={e.externo ? "ruim" : e.simulado ? "medio" : "bom"}>{e.externo ? "Provedor EXTERNO" : e.simulado ? "Modo simulado (sem IA)" : "Provedor local"}</Badge>
              <Badge>{e.provedor}</Badge>
              {e.modelo && <Badge>{e.modelo}</Badge>}
              {e.host && <Badge>{e.host}</Badge>}
            </div>
            <p className="subtitulo">
              {e.externo ? "Os campos públicos do conjunto (título, descrição, palavras-chave, temas, organização, formatos, licença e periodicidade) são enviados a este provedor. Contatos pessoais e a base curada nunca são enviados."
                : e.simulado ? "As sugestões são geradas por regras simples, só para demonstrar o fluxo. Nenhum dado sai desta máquina."
                : "O modelo roda na infraestrutura do projeto."}
            </p>
          </Card>
          <NovaExecucao limite={e.limite_por_execucao} />
          <Execucoes />
          <Revisao />
        </>
      )}
    </main>
  );
}

function NovaExecucao({ limite }: { limite: number }) {
  const tarefas = useApi(() => api.get<LlmTarefa[]>("/llm/tarefas"), []);
  const colecoes = useApi(() => api.get<Colecao[]>("/colecoes"), []);
  const [tarefa, setTarefa] = useState("melhorar-descricao");
  const [fonte, setFonte] = useState("fila");
  const [colecao, setColecao] = useState("");
  const [quantidade, setQuantidade] = useState(5);
  const [instrucoes, setInstrucoes] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const acao = useAction();
  const t = (tarefas.data ?? []).find((x) => x.chave === tarefa);

  async function gerar() {
    const r = await acao.run(async () => {
      const n = Math.max(1, Math.min(quantidade, Math.min(limite, 100)));
      const sel = fonte === "fila"
        ? await api.get<Busca>("/curadoria/fila", { tamanho: n })
        : await api.get<Busca>(`/colecoes/${colecao}/conjuntos`, { tamanho: n });
      if (sel.itens.length === 0) throw new Error("Nenhum conjunto para processar nesta origem.");
      return api.post<LlmExecucao>("/llm/execucoes", { tarefa, ids: sel.itens.map((i) => i.id), instrucoes: instrucoes || null });
    });
    if (r) setMsg(`Execução #${r.id} enfileirada para ${fmtNum(r.conjuntos)} conjunto(s).`);
  }

  return (
    <Card title="Nova execução">
      <ErrorBox error={acao.error} />
      {msg && <div className="ok" role="status">{msg}</div>}
      <div className="grade grade-2">
        <div>
          <label className="campo"><span className="campo-rotulo">Tarefa</span>
            <select value={tarefa} onChange={(ev) => setTarefa(ev.target.value)}>
              {(tarefas.data ?? []).map((x) => <option key={x.chave} value={x.chave}>{x.nome}</option>)}
            </select>
            {t && <span className="campo-dica">{t.descricao}</span>}
          </label>
          <label className="campo"><span className="campo-rotulo">Quais conjuntos</span>
            <select value={fonte} onChange={(ev) => setFonte(ev.target.value)}>
              <option value="fila">Os primeiros da fila de curadoria (mais prioritários)</option>
              <option value="colecao">Os primeiros de uma coleção</option>
            </select>
          </label>
          {fonte === "colecao" && (
            <label className="campo"><span className="campo-rotulo">Coleção</span>
              <select value={colecao} onChange={(ev) => setColecao(ev.target.value)}>
                <option value="">Escolha…</option>
                {(colecoes.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome} ({c.conjuntos})</option>)}
              </select>
            </label>
          )}
        </div>
        <div>
          <label className="campo"><span className="campo-rotulo">Quantos conjuntos</span>
            <input type="number" min={1} max={Math.min(limite, 100)} value={quantidade} onChange={(ev) => setQuantidade(Number(ev.target.value))} />
            <span className="campo-dica">No máximo {Math.min(limite, 100)} por execução.</span>
          </label>
          <label className="campo"><span className="campo-rotulo">Instruções adicionais (opcional)</span>
            <input type="text" value={instrucoes} maxLength={500} onChange={(ev) => setInstrucoes(ev.target.value)} placeholder="Ex.: use linguagem formal e cite o órgão" />
          </label>
        </div>
      </div>
      <button className="botao" type="button" disabled={acao.pending || (fonte === "colecao" && !colecao)} onClick={gerar}>Gerar sugestões</button>
    </Card>
  );
}

function Execucoes() {
  const lista = useApi(() => api.get<LlmExecucao[]>("/llm/execucoes", { limite: 8 }), [], 3000);
  const [erro, setErro] = useState<string | null>(null);
  async function cancelar(id: number) {
    try { await api.post(`/llm/execucoes/${id}/cancelar`); } catch (err) { setErro(err instanceof Error ? err.message : String(err)); }
    lista.reload();
  }
  return (
    <Card title="Execuções">
      <ErrorBox error={erro} />
      {lista.data && (lista.data.length === 0 ? <Empty>Nenhuma execução ainda.</Empty> : (
        <table>
          <thead><tr><th>#</th><th>Tarefa</th><th>Situação</th><th>Progresso</th><th className="num">A revisar</th><th>Quando</th><th /></tr></thead>
          <tbody>
            {lista.data.map((x) => {
              const feitos = Number(x.totais?.processados ?? 0);
              return (
                <tr key={x.id}>
                  <td>{x.id}</td>
                  <td>{x.tarefa_chave}</td>
                  <td><Badge tone={x.estado === "concluida" ? "bom" : x.estado === "falhou" ? "ruim" : "azul"}>{ESTADOS_EXEC[x.estado] ?? x.estado}</Badge>{x.erro && <div className="subtitulo">{x.erro}</div>}</td>
                  <td style={{ minWidth: 140 }}><Bar value={feitos} max={Math.max(1, x.conjuntos)} /><span className="subtitulo">{feitos}/{x.conjuntos}{x.totais?.erros ? ` · ${x.totais.erros} erro(s)` : ""}</span></td>
                  <td className="num">{x.pendentes}</td>
                  <td>{fmtDate(x.criada_em, true)}</td>
                  <td>{(x.estado === "enfileirada" || x.estado === "em_andamento") && <button type="button" className="botao botao-perigo botao-peq" onClick={() => cancelar(x.id)}>Cancelar</button>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ))}
    </Card>
  );
}

function Revisao() {
  const [estado, setEstado] = useState("pendente");
  const [page, setPage] = useState(1);
  const props = useApi(() => api.get<{ total: number; pagina: number; tamanho: number; itens: LlmProposta[] }>("/llm/propostas", { estado, pagina: page, tamanho: 10 }), [estado, page], 4000);
  const [sel, setSel] = useState<number[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const acao = useAction();
  const d = props.data;

  async function lote(decisao: "aprovar" | "rejeitar") {
    const r = await acao.run(() => api.post<{ decididas: number; ignoradas: number }>("/llm/propostas/decidir-em-lote", { ids: sel, decisao }));
    if (r) { setMsg(`${r.decididas} decidida(s), ${r.ignoradas} ignorada(s).`); setSel([]); props.reload(); }
  }

  return (
    <Card
      title="Revisão das propostas"
      actions={
        <>
          <select aria-label="Filtrar propostas" value={estado} onChange={(ev) => { setEstado(ev.target.value); setPage(1); setSel([]); }}>
            <option value="pendente">Aguardando revisão</option>
            <option value="aprovada">Aprovadas</option>
            <option value="editada">Editadas</option>
            <option value="rejeitada">Rejeitadas</option>
            <option value="desatualizada">Desatualizadas</option>
            <option value="erro">Com erro</option>
          </select>
          {sel.length > 0 && (
            <>
              <button className="botao botao-peq" type="button" disabled={acao.pending} onClick={() => lote("aprovar")}>Aprovar {sel.length} selecionada(s)</button>
              <button className="botao botao-perigo botao-peq" type="button" disabled={acao.pending} onClick={() => lote("rejeitar")}>Rejeitar selecionadas</button>
            </>
          )}
        </>
      }
    >
      {msg && <div className="ok" role="status">{msg}</div>}
      <ErrorBox error={acao.error} />
      {props.loading && <Loading />}
      {d && (d.itens.length === 0 ? <Empty>Nenhuma proposta neste estado.</Empty> : (
        <>
          <p className="subtitulo">{fmtNum(d.total)} proposta(s)</p>
          {d.itens.map((p) => (
            <PropostaCard key={p.id} p={p} onDone={props.reload} selected={sel.includes(p.id)} onSelect={(c) => setSel(c ? [...sel, p.id] : sel.filter((x) => x !== p.id))} />
          ))}
          <Pagination page={d.pagina} total={d.total} size={d.tamanho} onChange={setPage} />
        </>
      ))}
    </Card>
  );
}
