import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, type Busca, type Colecao, type LlmEstado, type LlmTarefa } from "../api";
import { ESFERAS, ESTADOS_CURADORIA, fmtDate, fmtNum } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Card, Empty, ErrorBox, EstadoCuradoria, Loading, Nota, Pagination } from "../ui";

const FACETAS: [string, string, (v: string) => string][] = [
  ["organizacao", "Organização", (v) => v],
  ["esfera", "Esfera", (v) => ESFERAS[v] ?? v],
  ["tema", "Tema", (v) => v],
  ["formato", "Formato", (v) => v],
  ["licenca", "Licença", (v) => v],
  ["periodicidade", "Periodicidade", (v) => v],
  ["selo", "Selo do portal", (v) => v],
  ["estado_curadoria", "Curadoria", (v) => ESTADOS_CURADORIA[v] ?? v],
];
const ORDENS: [string, string][] = [
  ["relevancia", "Relevância"],
  ["titulo", "Título (A–Z)"],
  ["nota", "Maior nota"],
  ["nota_asc", "Menor nota"],
  ["prioridade", "Prioridade de curadoria"],
  ["atualizacao", "Atualizados recentemente"],
];
const NAO_FILTRO = new Set(["pagina", "ordem", "tamanho"]);

export function filtrosDaUrl(sp: URLSearchParams): Record<string, string> {
  const out: Record<string, string> = {};
  sp.forEach((v, k) => {
    if (!NAO_FILTRO.has(k) && k !== "colecao") out[k] = v;
  });
  return out;
}

export default function BuscaPage() {
  const [sp, setSp] = useSearchParams();
  const page = Number(sp.get("pagina") ?? 1);
  const ordem = sp.get("ordem") ?? "relevancia";
  const [texto, setTexto] = useState(sp.get("q") ?? "");
  const filtros = filtrosDaUrl(sp);
  const dados = useApi(
    () => api.get<Busca>("/conjuntos", { ...Object.fromEntries(sp.entries()), pagina: page, tamanho: 20, ordem }),
    [sp.toString()],
  );

  function definir(chave: string, valor: string | null) {
    const novo = new URLSearchParams(sp);
    if (valor === null || valor === "") novo.delete(chave);
    else novo.set(chave, valor);
    novo.delete("pagina");
    setSp(novo);
  }
  function alternar(chave: string, valor: string) {
    definir(chave, sp.get(chave) === valor ? null : valor);
  }
  function enviar(e: FormEvent) {
    e.preventDefault();
    definir("q", texto.trim());
  }
  function faixa(valor: string) {
    const novo = new URLSearchParams(sp);
    novo.delete("nota_min");
    novo.delete("nota_max");
    novo.delete("pagina");
    if (valor === "alta") novo.set("nota_min", "70");
    if (valor === "media") {
      novo.set("nota_min", "40");
      novo.set("nota_max", "69.9");
    }
    if (valor === "baixa") novo.set("nota_max", "39.9");
    setSp(novo);
  }
  const faixaAtual = sp.get("nota_min") === "70" ? "alta" : sp.get("nota_min") === "40" ? "media" : sp.get("nota_max") === "39.9" ? "baixa" : "";
  const d = dados.data;
  const ativos = Object.entries(filtros).filter(([k]) => k !== "q");

  return (
    <main className="pagina">
      <h1>Buscar conjuntos de dados</h1>
      <p className="subtitulo">Pesquise no catálogo espelhado, já considerando a curadoria feita.</p>

      <form className="busca-form" role="search" onSubmit={enviar}>
        <input type="search" aria-label="Texto da busca" placeholder="Ex.: saúde população, orçamento, educação básica…" value={texto} onChange={(e) => setTexto(e.target.value)} />
        <button className="botao" type="submit">Buscar</button>
        {(sp.toString() !== "") && (
          <button className="botao botao-sec" type="button" onClick={() => { setTexto(""); setSp(new URLSearchParams()); }}>Limpar</button>
        )}
      </form>

      {ativos.length > 0 && (
        <div className="filtros-ativos" aria-label="Filtros ativos">
          {ativos.map(([k, v]) => (
            <button key={k} type="button" className="filtro-ativo" onClick={() => definir(k, null)} title="Remover filtro">
              {k.replace("_", " ")}: {v} ✕
            </button>
          ))}
        </div>
      )}

      <div className="busca-layout">
        <aside className="facetas" aria-label="Filtros">
          <div className="faceta">
            <h3>Qualidade</h3>
            <select aria-label="Faixa de qualidade" value={faixaAtual} onChange={(e) => faixa(e.target.value)}>
              <option value="">Todas</option>
              <option value="alta">Alta (70 ou mais)</option>
              <option value="media">Média (40 a 69)</option>
              <option value="baixa">Baixa (abaixo de 40)</option>
            </select>
          </div>
          <div className="faceta">
            <h3>Curadoria</h3>
            <select aria-label="Já curado" value={sp.get("curado") ?? ""} onChange={(e) => definir("curado", e.target.value)}>
              <option value="">Todos</option>
              <option value="true">Já curados</option>
              <option value="false">Ainda não curados</option>
            </select>
          </div>
          {d && FACETAS.map(([chave, titulo, rotulo]) => {
            const itens = d.facetas[chave] ?? [];
            if (!itens.length) return null;
            return (
              <div className="faceta" key={chave}>
                <h3>{titulo}</h3>
                <ul>
                  {itens.slice(0, 10).map((f) => (
                    <li key={f.valor}>
                      <button type="button" aria-pressed={sp.get(chave) === f.valor} onClick={() => alternar(chave, f.valor)}>
                        <span>{chave === "organizacao" ? f.rotulo : rotulo(f.valor)}</span>
                        <span className="n">{fmtNum(f.n)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </aside>

        <section aria-label="Resultados">
          {dados.loading && <Loading />}
          <ErrorBox error={dados.error} onRetry={dados.reload} />
          {d && (
            <>
              <div className="linha" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                <strong data-testid="total">{fmtNum(d.total)} conjunto(s)</strong>
                <div className="linha">
                  <label>
                    Ordenar por{" "}
                    <select value={ordem} onChange={(e) => definir("ordem", e.target.value)}>
                      {ORDENS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </label>
                  <a className="botao botao-sec botao-peq" href={api.url("/exportacao/conjuntos", { ...Object.fromEntries(sp.entries()), saida: "csv" })} download>Exportar CSV</a>
                  <a className="botao botao-sec botao-peq" href={api.url("/exportacao/conjuntos", { ...Object.fromEntries(sp.entries()), saida: "json" })} download>Exportar JSON</a>
                </div>
              </div>
              {d.aproximada && <div className="info">Nenhum resultado exato. Mostrando títulos parecidos com “{sp.get("q")}”.</div>}
              {d.itens.length === 0 && <Empty>Nada encontrado. Tente outras palavras ou remova filtros.</Empty>}
              {d.itens.map((c) => (
                <article className="resultado" key={c.id}>
                  <h3><Link to={`/conjuntos/${c.id}`}>{c.titulo}</Link></h3>
                  {c.resumo && <p>{c.resumo.length >= 300 ? `${c.resumo}…` : c.resumo}</p>}
                  <div className="meta">
                    <Nota value={c.nota_qualidade} />
                    <EstadoCuradoria value={c.estado_curadoria} />
                    {c.curado && <Badge tone="azul">Curado</Badge>}
                    {c.sem_detalhe && <Badge tone="ruim" title="O portal não entrega o detalhe deste conjunto">Sem detalhe</Badge>}
                    {c.organizacao_titulo && <span>{c.organizacao_titulo}</span>}
                    {c.formatos.slice(0, 4).map((f) => <Badge key={f}>{f}</Badge>)}
                    <span>{fmtNum(c.qtd_recursos)} recurso(s)</span>
                    <span>Atualizado em {fmtDate(c.metadados_atualizados_em)}</span>
                  </div>
                </article>
              ))}
              <Pagination page={d.pagina} total={d.total} size={d.tamanho} onChange={(p) => { const n = new URLSearchParams(sp); n.set("pagina", String(p)); setSp(n); }} />
              {d.total > 0 && <AcoesEmLote total={d.total} filtros={{ ...filtros }} />}
            </>
          )}
        </section>
      </div>
    </main>
  );
}

function AcoesEmLote({ total, filtros }: { total: number; filtros: Record<string, string> }) {
  const colecoes = useApi(() => api.get<Colecao[]>("/colecoes"), []);
  const tarefas = useApi(() => api.get<LlmTarefa[]>("/llm/tarefas"), []);
  const llm = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const [colecaoId, setColecaoId] = useState("");
  const [nome, setNome] = useState("");
  const [tarefa, setTarefa] = useState("sugerir-tags");
  const [msg, setMsg] = useState<string | null>(null);
  const acao = useAction();
  const manuais = (colecoes.data ?? []).filter((c) => c.tipo === "manual");

  async function adicionar() {
    const r = await acao.run(() => api.post<{ adicionados: number }>(`/colecoes/${colecaoId}/itens-por-busca`, { filtros }));
    if (r) setMsg(`${fmtNum(r.adicionados)} conjunto(s) adicionado(s) à coleção.`);
  }
  async function salvarDinamica() {
    const r = await acao.run(() => api.post<Colecao>("/colecoes", { nome, tipo: "dinamica", regra_filtro: filtros }));
    if (r) { setMsg(`Coleção dinâmica “${r.nome}” criada com ${fmtNum(r.conjuntos)} conjunto(s).`); setNome(""); colecoes.reload(); }
  }
  async function pedirLlm() {
    const r = await acao.run(() => api.post<{ id: number; conjuntos: number }>("/llm/execucoes", { tarefa, filtros }));
    if (r) setMsg(`Execução #${r.id} enfileirada para ${fmtNum(r.conjuntos)} conjunto(s). Acompanhe em “Sugestões”.`);
  }

  return (
    <Card title="Ações sobre todos os resultados desta busca">
      <p className="subtitulo">Vale para os {fmtNum(total)} resultados, não só para esta página.</p>
      {msg && <div className="ok" role="status">{msg}</div>}
      <ErrorBox error={acao.error} />
      <div className="grade grade-2">
        <div>
          <h3>Adicionar a uma coleção manual</h3>
          <div className="linha">
            <select aria-label="Coleção de destino" value={colecaoId} onChange={(e) => setColecaoId(e.target.value)}>
              <option value="">Escolha…</option>
              {manuais.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <button className="botao" type="button" disabled={!colecaoId || acao.pending} onClick={adicionar}>Adicionar</button>
          </div>
          {manuais.length === 0 && <p className="subtitulo">Nenhuma coleção manual ainda. <Link to="/colecoes">Criar</Link></p>}
        </div>
        <div>
          <h3>Salvar esta busca como coleção dinâmica</h3>
          <div className="linha">
            <input type="text" aria-label="Nome da coleção dinâmica" placeholder="Nome da coleção" value={nome} onChange={(e) => setNome(e.target.value)} />
            <button className="botao" type="button" disabled={!nome.trim() || Object.keys(filtros).length === 0 || acao.pending} onClick={salvarDinamica}>Salvar</button>
          </div>
          {Object.keys(filtros).length === 0 && <p className="subtitulo">Aplique ao menos um filtro ou texto.</p>}
        </div>
        {llm.data?.habilitado && (
          <div>
            <h3>Pedir sugestões de LLM</h3>
            <div className="linha">
              <select aria-label="Tarefa de LLM" value={tarefa} onChange={(e) => setTarefa(e.target.value)}>
                {(tarefas.data ?? []).map((t) => <option key={t.chave} value={t.chave}>{t.nome}</option>)}
              </select>
              <button className="botao" type="button" disabled={acao.pending || total > llm.data.limite_por_execucao} onClick={pedirLlm}>Gerar sugestões</button>
            </div>
            {total > llm.data.limite_por_execucao && <p className="subtitulo">Refine a busca para no máximo {llm.data.limite_por_execucao} resultados.</p>}
          </div>
        )}
      </div>
    </Card>
  );
}
