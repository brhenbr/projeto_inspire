import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, type ConjuntoDetalhe, type LlmEstado, type LlmTarefa, type Tema, type LlmProposta } from "../api";
import PropostaCard from "../PropostaCard";
import { CAMPOS, ESTADOS_CURADORIA, ESFERAS, fmtDate, fmtNum, fmtValue } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Bar, Card, Empty, ErrorBox, EstadoCuradoria, Field, Loading, Nota, Tabs } from "../ui";

type Aba = "metadados" | "qualidade" | "recursos" | "historico" | "llm";
const PERIODICIDADES = ["DIARIA", "SEMANAL", "QUINZENAL", "MENSAL", "BIMESTRAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "BIENAL"];

export default function ConjuntoPage() {
  const { id = "" } = useParams();
  const dados = useApi(() => api.get<ConjuntoDetalhe>(`/conjuntos/${id}`), [id]);
  const [aba, setAba] = useState<Aba>("metadados");
  const [aviso, setAviso] = useState<string | null>(null); // fica aqui: o formulário remonta ao recarregar
  const d = dados.data;

  if (dados.loading) return <main className="pagina"><Loading /></main>;
  if (dados.error) return <main className="pagina"><ErrorBox error={dados.error} onRetry={dados.reload} /><Link to="/conjuntos">Voltar à busca</Link></main>;
  if (!d) return null;
  const titulo = d.efetivo?.titulo ?? d.original.titulo;

  return (
    <main className="pagina">
      <p><Link to="/conjuntos">← Voltar à busca</Link></p>
      <div className="cabeca-detalhe">
        <h1>{titulo}</h1>
        <div className="linha">
          <Nota value={d.qualidade?.nota ?? null} />
          <EstadoCuradoria value={d.estado_curadoria} />
          {d.alteracoes.length > 0 && <Badge tone="azul">Curado</Badge>}
          {d.sem_detalhe && <Badge tone="ruim">Sem detalhe no portal</Badge>}
          {d.removido_em && <Badge tone="ruim">Removido do portal em {fmtDate(d.removido_em)}</Badge>}
          {d.organizacao.slug && <Link to={`/organizacoes/${d.organizacao.slug}`}>{d.organizacao.titulo}</Link>}
          {d.organizacao.esfera && <Badge>{ESFERAS[d.organizacao.esfera] ?? d.organizacao.esfera}{d.organizacao.uf ? ` · ${d.organizacao.uf}` : ""}</Badge>}
          {d.link_portal && <a href={d.link_portal} target="_blank" rel="noreferrer noopener">Ver no portal ↗</a>}
        </div>
      </div>

      {d.sem_detalhe && (
        <div className="info">O portal não entrega o detalhe deste conjunto (erro do lado do portal), então só temos o resumo da listagem. Ele não recebe nota de qualidade.</div>
      )}

      <Tabs
        active={aba}
        onChange={setAba}
        tabs={[
          { key: "metadados", label: "Metadados e curadoria" },
          { key: "qualidade", label: "Qualidade" },
          { key: "recursos", label: `Recursos (${d.recursos.length})` },
          { key: "historico", label: "Histórico" },
          { key: "llm", label: `Sugestões de LLM${d.propostas_pendentes ? ` (${d.propostas_pendentes})` : ""}` },
        ]}
      />
      {aba === "metadados" && <Metadados key={JSON.stringify([d.efetivo, d.estado_curadoria])} d={d} onChanged={dados.reload} ok={aviso} setOk={setAviso} />}
      {aba === "qualidade" && <Qualidade d={d} />}
      {aba === "recursos" && <Recursos d={d} />}
      {aba === "historico" && <Historico d={d} />}
      {aba === "llm" && <SugestoesLlm d={d} onChanged={dados.reload} />}
    </main>
  );
}

// ---------------------------------------------------------------- metadados e edição

function Metadados({ d, onChanged, ok, setOk }: { d: ConjuntoDetalhe; onChanged: () => void; ok: string | null; setOk: (m: string | null) => void }) {
  const ef = d.efetivo;
  const temas = useApi(() => api.get<Tema[]>("/temas"), []);
  const [titulo, setTitulo] = useState(ef?.titulo ?? "");
  const [descricao, setDescricao] = useState(ef?.descricao ?? "");
  const [tags, setTags] = useState((ef?.tags ?? []).join(", "));
  const [selTemas, setSelTemas] = useState<string[]>(ef?.temas ?? []);
  const [periodicidade, setPeriodicidade] = useState(ef?.periodicidade ?? "");
  const [licenca, setLicenca] = useState(ef?.licenca ?? "");
  const [comentario, setComentario] = useState("");
  const acao = useAction();
  const status = useAction();
  const [estado, setEstado] = useState(d.estado_curadoria);
  const [duplicadoDe, setDuplicadoDe] = useState("");

  if (!ef) return <Empty>Sem metadados efetivos (o conjunto ainda não entrou no modelo de leitura).</Empty>;
  const lista = (s: string) => s.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);

  async function salvar() {
    const campos: Record<string, unknown> = {};
    if (titulo.trim() !== ef!.titulo) campos.titulo = titulo;
    if (descricao.trim() !== (ef!.descricao ?? "").trim()) campos.descricao = descricao;
    if (JSON.stringify([...new Set(lista(tags))].sort()) !== JSON.stringify([...ef!.tags].sort())) campos.tags = lista(tags);
    if (JSON.stringify([...selTemas].sort()) !== JSON.stringify([...ef!.temas].sort())) campos.temas = selTemas;
    if (periodicidade.trim() !== (ef!.periodicidade ?? "")) campos.periodicidade = periodicidade;
    if (licenca.trim() !== (ef!.licenca ?? "")) campos.licenca = licenca;
    if (!Object.keys(campos).length) { setOk("Nada mudou."); return; }
    const r = await acao.run(() => api.patch<{ alterados: string[] }>(`/conjuntos/${d.id}/curadoria`, { campos, comentario: comentario || null }));
    if (r) { setOk(`Salvo: ${r.alterados.map((c) => CAMPOS[c] ?? c).join(", ")}.`); setComentario(""); onChanged(); }
  }
  async function reverter(campo: string) {
    const r = await acao.run(() => api.post<{ revertido: boolean }>(`/conjuntos/${d.id}/curadoria/reverter`, { campo }));
    if (r) { setOk(`“${CAMPOS[campo]}” voltou ao valor do portal.`); onChanged(); }
  }
  async function salvarStatus() {
    const r = await status.run(() => api.put(`/conjuntos/${d.id}/status`, { estado, duplicado_de: estado === "duplicado" ? duplicadoDe || null : null }));
    if (r) { setOk(`Status: ${ESTADOS_CURADORIA[estado]}.`); onChanged(); }
  }
  const mudou = (campo: keyof typeof ef) => JSON.stringify(ef[campo]) !== JSON.stringify(d.original[campo]);
  const original = (campo: keyof typeof ef) => (
    mudou(campo) ? (
      <div className="linha" style={{ alignItems: "flex-start" }}>
        <div className="original" style={{ flex: 1 }}><strong>No portal:</strong> {fmtValue(d.original[campo])}</div>
        <button type="button" className="botao botao-sec botao-peq" onClick={() => reverter(campo)}>Reverter ao valor do portal</button>
      </div>
    ) : null
  );

  return (
    <div className="grade grade-2">
      <Card title="Editar metadados">
        <p className="subtitulo">O dado do portal nunca é alterado: a edição fica como curadoria, com histórico.</p>
        <ErrorBox error={acao.error} />
        {ok && <div className="ok" role="status">{ok}</div>}
        <Field label="Título"><input type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} /></Field>
        {original("titulo")}
        <Field label="Descrição" hint={`${descricao.trim().length} caracteres (recomendado: 100 ou mais)`}>
          <textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </Field>
        {original("descricao")}
        <Field label="Palavras-chave" hint="Separadas por vírgula (recomendado: 3 ou mais)"><input type="text" value={tags} onChange={(e) => setTags(e.target.value)} /></Field>
        {original("tags")}
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 12px" }}>
          <legend className="campo-rotulo">Temas</legend>
          <div className="chips">
            {(temas.data ?? []).map((t) => (
              <label key={t.slug} className="badge badge-neutro" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={selTemas.includes(t.slug)} onChange={(e) => setSelTemas(e.target.checked ? [...selTemas, t.slug] : selTemas.filter((x) => x !== t.slug))} /> {t.titulo}
              </label>
            ))}
          </div>
        </fieldset>
        {original("temas")}
        <div className="linha">
          <Field label="Periodicidade">
            <input type="text" list="periodicidades" value={periodicidade} onChange={(e) => setPeriodicidade(e.target.value.toUpperCase())} />
            <datalist id="periodicidades">{PERIODICIDADES.map((p) => <option key={p} value={p} />)}</datalist>
          </Field>
          <Field label="Licença"><input type="text" value={licenca} onChange={(e) => setLicenca(e.target.value)} placeholder="ex.: cc-by" /></Field>
        </div>
        {original("periodicidade")}
        {original("licenca")}
        <Field label="Comentário (opcional)" hint="Aparece no histórico"><input type="text" value={comentario} onChange={(e) => setComentario(e.target.value)} /></Field>
        <button className="botao" type="button" disabled={acao.pending} onClick={salvar}>Salvar alterações</button>
      </Card>

      <div>
        <Card title="Status da curadoria">
          <ErrorBox error={status.error} />
          <div className="linha">
            <select aria-label="Status da curadoria" value={estado} onChange={(e) => setEstado(e.target.value)}>
              {Object.entries(ESTADOS_CURADORIA).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            {estado === "duplicado" && <input type="text" aria-label="Identificador do conjunto original" placeholder="id do original" value={duplicadoDe} onChange={(e) => setDuplicadoDe(e.target.value)} />}
            <button className="botao" type="button" disabled={status.pending} onClick={salvarStatus}>Salvar status</button>
          </div>
          {d.colecoes.length > 0 && (
            <p>Coleções: {d.colecoes.map((c) => <Link key={c.id} to={`/colecoes/${c.id}`} style={{ marginRight: 8 }}>{c.nome}</Link>)}</p>
          )}
        </Card>
        <Card title="Dados do portal">
          <table>
            <tbody>
              {([
                ["Selo do portal", d.portal.selo],
                ["Situação segundo o portal", d.portal.atualizado],
                ["Dados abertos", d.portal.dados_abertos === null ? null : d.portal.dados_abertos ? "Sim" : "Não"],
                ["Origem do cadastro", d.portal.origem_cadastro],
                ["Observância legal", d.portal.observancia_legal],
                ["Cobertura temporal", [d.portal.cobertura_temporal_inicio, d.portal.cobertura_temporal_fim].filter(Boolean).join(" a ") || null],
                ["Cobertura espacial", d.portal.cobertura_espacial],
                ["Catalogado em", fmtDate(String(d.portal.catalogado_em ?? ""))],
                ["Metadados atualizados em", fmtDate(String(d.portal.metadados_atualizados_em ?? ""), true)],
                ["Dados atualizados em", fmtDate(String(d.portal.dados_atualizados_em ?? ""))],
              ] as [string, string | number | boolean | null][]).map(([k, v]) => (
                <tr key={k}><th scope="row">{k}</th><td>{v === null || v === "" ? "—" : String(v)}</td></tr>
              ))}
            </tbody>
          </table>
          <p className="subtitulo" style={{ marginTop: 10 }}>
            Contato do responsável: {d.portal.tem_responsavel || d.portal.tem_email_responsavel ? "informado no portal" : "não informado"}. Dados pessoais de contato não são armazenados por este sistema.
          </p>
        </Card>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- qualidade

function Qualidade({ d }: { d: ConjuntoDetalhe }) {
  const q = d.qualidade;
  if (!q) return <Empty>Este conjunto não tem nota de qualidade (removido do portal ou sem detalhe).</Empty>;
  const tone = (n: number) => (n >= 70 ? "bom" : n >= 40 ? "medio" : "ruim");
  return (
    <div className="grade grade-2">
      <Card title="Por dimensão">
        <p>Nota geral: <Nota value={q.nota} /> <span className="subtitulo">calculada em {fmtDate(q.calculada_em, true)}</span></p>
        <div className="lista-barras">
          {Object.entries(q.dimensoes).map(([dim, n]) => (
            <div key={dim} style={{ display: "contents" }}>
              <span>{dim}</span><Bar value={n} tone={tone(n)} /><span>{fmtNum(n)}</span>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Verificações">
        <table>
          <thead><tr><th>Resultado</th><th>Regra</th><th className="num">Peso</th><th>Observação</th></tr></thead>
          <tbody>
            {q.detalhes.map((r) => (
              <tr key={r.regra}>
                <td>{r.passou === null ? <span className="regra-na" title="Sem dados para avaliar">—</span> : r.passou ? <span className="regra-ok" aria-label="Passou">✔</span> : <span className="regra-falha" aria-label="Falhou">✘</span>}</td>
                <td>{r.nome} <span className="subtitulo">({r.dimensao})</span></td>
                <td className="num">{r.ativa ? r.peso : "inativa"}</td>
                <td>{r.mensagem || (r.avaliavel ? "" : "não avaliável")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="subtitulo">Pesos e regras em <Link to="/configuracoes">Configurações</Link>. Detalhes na documentação (matriz de qualidade).</p>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- recursos e histórico

function Recursos({ d }: { d: ConjuntoDetalhe }) {
  if (!d.recursos.length) return <Empty>Nenhum recurso associado a este conjunto.</Empty>;
  return (
    <Card title="Recursos (arquivos e APIs no portal de origem)">
      <p className="subtitulo">Este sistema guarda apenas os metadados; os arquivos ficam nos órgãos.</p>
      <table>
        <thead><tr><th>Título</th><th>Formato</th><th className="num">Tamanho</th><th className="num">Downloads</th><th>Link</th></tr></thead>
        <tbody>
          {d.recursos.map((r) => (
            <tr key={r.id}>
              <td>{r.titulo ?? "—"}{r.descricao && <div className="subtitulo">{r.descricao}</div>}</td>
              <td>{r.formato ? <Badge>{r.formato}</Badge> : "—"}</td>
              <td className="num">{r.tamanho ? fmtNum(r.tamanho) : "—"}</td>
              <td className="num">{fmtNum(r.downloads)}</td>
              <td>{r.link ? <a href={r.link} target="_blank" rel="noreferrer noopener">Abrir ↗</a> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Historico({ d }: { d: ConjuntoDetalhe }) {
  return (
    <div className="grade grade-2">
      <Card title="Alterações da curadoria">
        {d.alteracoes.length === 0 ? <Empty>Nenhuma alteração ainda.</Empty> : (
          <table>
            <thead><tr><th>Quando</th><th>Campo</th><th>Novo valor</th><th>Quem</th></tr></thead>
            <tbody>
              {d.alteracoes.map((a) => (
                <tr key={a.id}>
                  <td>{fmtDate(a.em, true)}</td>
                  <td>{CAMPOS[a.campo] ?? a.campo}</td>
                  <td>{a.valor === null ? <em>revertido ao valor do portal</em> : fmtValue(a.valor).slice(0, 160)}{a.comentario && <div className="subtitulo">{a.comentario}</div>}</td>
                  <td>{a.autor} <Badge tone={a.origem === "llm" ? "medio" : "azul"}>{a.origem === "llm" ? "LLM" : "humano"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <Card title="Mudanças vindas do portal">
        {d.historico.length === 0 ? <Empty>Sem registros.</Empty> : (
          <table>
            <thead><tr><th>Quando</th><th>Evento</th><th>Extração</th></tr></thead>
            <tbody>{d.historico.map((h, i) => <tr key={i}><td>{fmtDate(h.em, true)}</td><td>{h.evento}</td><td>#{h.execucao_id}</td></tr>)}</tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- sugestões de LLM

function SugestoesLlm({ d, onChanged }: { d: ConjuntoDetalhe; onChanged: () => void }) {
  const llm = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const tarefas = useApi(() => api.get<LlmTarefa[]>("/llm/tarefas"), []);
  const props = useApi(() => api.get<{ itens: LlmProposta[] }>("/llm/propostas", { conjunto_id: d.id, tamanho: 50 }), [d.id], 4000);
  const [tarefa, setTarefa] = useState("melhorar-descricao");
  const [instrucoes, setInstrucoes] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const acao = useAction();

  async function pedir() {
    const r = await acao.run(() => api.post<{ id: number }>("/llm/execucoes", { tarefa, ids: [d.id], instrucoes: instrucoes || null }));
    if (r) { setMsg(`Execução #${r.id} enfileirada. As propostas aparecem aqui quando ficarem prontas.`); props.reload(); }
  }
  return (
    <div>
      {llm.data && !llm.data.habilitado && <div className="info">O recurso de LLM está desligado. {llm.data.motivo}</div>}
      {llm.data?.habilitado && (
        <Card title="Pedir uma sugestão">
          <ErrorBox error={acao.error} />
          {msg && <div className="ok" role="status">{msg}</div>}
          <div className="linha">
            <select aria-label="Tarefa" value={tarefa} onChange={(e) => setTarefa(e.target.value)}>
              {(tarefas.data ?? []).map((t) => <option key={t.chave} value={t.chave}>{t.nome}</option>)}
            </select>
            <input type="text" aria-label="Instruções adicionais" placeholder="Instruções adicionais (opcional)" value={instrucoes} onChange={(e) => setInstrucoes(e.target.value)} style={{ flex: 1 }} />
            <button className="botao" type="button" disabled={acao.pending} onClick={pedir}>Gerar sugestão</button>
          </div>
          <p className="subtitulo">A sugestão só é aplicada se você aprovar. Só campos públicos do conjunto são usados.</p>
        </Card>
      )}
      {(props.data?.itens ?? []).length === 0 ? <Empty>Nenhuma sugestão para este conjunto.</Empty> :
        props.data!.itens.map((p) => <PropostaCard key={p.id} p={p} onDone={() => { props.reload(); onChanged(); }} />)}
    </div>
  );
}
