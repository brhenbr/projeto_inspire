import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, type Busca, type Colecao, type LlmEstado, type PropostaColecao } from "../api";
import { fmtNum } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Card, Empty, ErrorBox, Field, Loading, Nota, Pagination } from "../ui";
import { FiltroChips, type Filtros } from "../FiltroChips";
import { FiltrosEntendidos } from "./Perguntar";

export function ColecoesPage() {
  const lista = useApi(() => api.get<Colecao[]>("/colecoes"), []);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const acao = useAction();

  async function criar() {
    const r = await acao.run(() => api.post<Colecao>("/colecoes", { nome, descricao: descricao || null, tipo: "manual" }));
    if (r) { setNome(""); setDescricao(""); lista.reload(); }
  }

  return (
    <main className="pagina">
      <h1>Coleções</h1>
      <p className="subtitulo">Agrupe conjuntos (ex.: bases sociais de saúde, assistência e educação). Manuais, escolhidas uma a uma, ou dinâmicas, definidas por filtros e atualizadas a cada extração.</p>
      <div className="grade grade-2">
        <Card title="Suas coleções">
          {lista.loading && <Loading />}
          <ErrorBox error={lista.error} onRetry={lista.reload} />
          {lista.data && (lista.data.length === 0 ? <Empty>Nenhuma coleção ainda.</Empty> : (
            <table>
              <thead><tr><th>Nome</th><th>Tipo</th><th className="num">Conjuntos</th></tr></thead>
              <tbody>
                {lista.data.map((c) => (
                  <tr key={c.id}>
                    <td><Link to={`/colecoes/${c.id}`}>{c.nome}</Link>{c.descricao && <div className="subtitulo">{c.descricao}</div>}</td>
                    <td><Badge tone={c.tipo === "dinamica" ? "azul" : "neutro"}>{c.tipo === "dinamica" ? "Dinâmica" : "Manual"}</Badge></td>
                    <td className="num">{fmtNum(c.conjuntos)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
        </Card>
        <Card title="Nova coleção manual">
          <ErrorBox error={acao.error} />
          <Field label="Nome"><input type="text" value={nome} onChange={(e) => setNome(e.target.value)} /></Field>
          <Field label="Descrição (opcional)"><input type="text" value={descricao} onChange={(e) => setDescricao(e.target.value)} /></Field>
          <button className="botao" type="button" disabled={!nome.trim() || acao.pending} onClick={criar}>Criar coleção</button>
          <p className="subtitulo" style={{ marginTop: 12 }}>
            Para uma coleção <strong>dinâmica</strong>, faça uma <Link to="/conjuntos">busca</Link> com filtros e use “Salvar esta busca como coleção dinâmica”.
          </p>
        </Card>
      </div>
      <ColecaoPorTexto onCreated={lista.reload} />
    </main>
  );
}

/** Descreva a coleção em texto; o LLM propõe os filtros, você ajusta, confere a amostra e só então cria. */
function ColecaoPorTexto({ onCreated }: { onCreated: () => void }) {
  const llm = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const navigate = useNavigate();
  const [texto, setTexto] = useState("");
  const [proposta, setProposta] = useState<PropostaColecao | null>(null);
  const [filtros, setFiltros] = useState<Filtros>({});
  const [nome, setNome] = useState("");
  const [resultado, setResultado] = useState<PropostaColecao["resultado"] | null>(null);
  const propor = useAction();
  const criar = useAction();
  const e = llm.data;

  async function contar(f: Filtros) {
    setFiltros(f);
    setResultado(await api.get<Busca>("/conjuntos", { ...f, tamanho: 5 }).catch(() => null));
  }
  async function enviar() {
    const p = await propor.run(() => api.post<PropostaColecao>("/chat/colecao", { descricao: texto }));
    if (p) { setProposta(p); setFiltros(p.filtros); setNome(p.nome_sugerido); setResultado(p.resultado); }
  }
  async function confirmar() {
    const c = await criar.run(() => api.post<Colecao>("/colecoes", { nome, descricao: texto, tipo: "dinamica", regra_filtro: filtros }));
    if (c) { onCreated(); navigate(`/colecoes/${c.id}`); }
  }

  if (!e?.habilitado) return null;
  const vazio = resultado?.total === 0;
  const alterado = proposta !== null && JSON.stringify(filtros) !== JSON.stringify(proposta.filtros);
  return (
    <Card title="Criar coleção descrevendo em texto">
      <p className="subtitulo">
        Descreva a coleção (ex.: “bases sociais de saúde e educação do governo federal”). O modelo propõe filtros; <strong>nada é criado até você confirmar</strong>.
        {e.externo && <> Seu texto é enviado ao provedor externo <strong>{e.host}</strong>; não escreva dados pessoais.</>}
      </p>
      <textarea aria-label="Descrição da coleção" rows={3} maxLength={500} style={{ width: "100%" }} value={texto} onChange={(ev) => setTexto(ev.target.value)} placeholder="Descreva a coleção" />
      <div className="linha" style={{ marginTop: 8 }}>
        <button className="botao" type="button" disabled={texto.trim().length < 2 || propor.pending} onClick={enviar}>{propor.pending ? "Interpretando…" : "Propor filtros"}</button>
        <span className="subtitulo">{texto.length}/500</span>
      </div>
      <ErrorBox error={propor.error} />
      {proposta && (
        <div style={{ marginTop: 12 }}>
          <FiltrosEntendidos i={{ ...proposta, filtros }} onChange={contar} />
          {alterado && <button type="button" className="botao botao-sec botao-peq" onClick={() => contar(proposta.filtros)}>Restaurar filtros propostos</button>}
          {resultado
            ? <p><strong data-testid="total-proposta">{fmtNum(resultado.total)} conjunto(s)</strong> entrariam agora; a coleção se atualiza a cada extração.</p>
            : <div className="info" role="note">Não consegui contar os conjuntos agora; você ainda pode criar a coleção.</div>}
          {vazio && <div className="info" role="note">Nenhum conjunto com esses filtros. Remova algum filtro (×) ou descreva de outro jeito.</div>}
          <ul>{(resultado?.itens ?? []).map((c) => <li key={c.id}><Link to={`/conjuntos/${c.id}`}>{c.titulo}</Link></li>)}</ul>
          <ErrorBox error={criar.error} />
          <label className="linha">Nome da coleção
            <input type="text" aria-label="Nome da nova coleção" style={{ flex: 1 }} value={nome} onChange={(ev) => setNome(ev.target.value)} />
          </label>
          <button className="botao" type="button" disabled={!nome.trim() || Object.keys(filtros).length === 0 || vazio || criar.pending} onClick={confirmar}>Criar coleção dinâmica</button>
        </div>
      )}
    </Card>
  );
}

export function ColecaoPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const col = useApi(() => api.get<Colecao>(`/colecoes/${id}`), [id]);
  const [page, setPage] = useState(1);
  const itens = useApi(() => api.get<Busca>(`/colecoes/${id}/conjuntos`, { pagina: page, tamanho: 20 }), [id, page]);
  const [nome, setNome] = useState<string | null>(null);
  const [descricao, setDescricao] = useState<string | null>(null);
  const [regra, setRegra] = useState<Filtros | null>(null);
  const [novaDescricao, setNovaDescricao] = useState("");
  const [salvo, setSalvo] = useState<string | null>(null);
  const acao = useAction();
  const reproposta = useAction();
  const c = col.data;

  if (col.loading) return <main className="pagina"><Loading /></main>;
  if (col.error) return <main className="pagina"><ErrorBox error={col.error} /><Link to="/colecoes">Voltar</Link></main>;
  if (!c) return null;

  async function salvarEdicao() {
    const corpo: Record<string, unknown> = {};
    if (nome !== null) corpo.nome = nome;
    if (descricao !== null) corpo.descricao = descricao;
    if (regra !== null) corpo.regra_filtro = regra;
    const r = await acao.run(() => api.put(`/colecoes/${id}`, corpo));
    if (r) { setNome(null); setDescricao(null); setRegra(null); setNovaDescricao(""); setSalvo("Alterações salvas."); col.reload(); itens.reload(); }
  }
  async function reproporRegra() {
    const p = await reproposta.run(() => api.post<PropostaColecao>("/chat/colecao", { descricao: novaDescricao }));
    if (p) setRegra(p.filtros);
  }
  async function apagar() {
    if (!window.confirm(`Apagar a coleção “${c!.nome}”? Os conjuntos não são apagados.`)) return;
    const apagou = await acao.run(async () => {
      await api.del(`/colecoes/${id}`);
      return true;
    });
    if (apagou) navigate("/colecoes");
  }
  async function remover(item: string) {
    const r = await acao.run(() => api.post(`/colecoes/${id}/itens/remover`, { ids: [item] }));
    if (r) { itens.reload(); col.reload(); }
  }
  async function excluir(item: string) {
    const r = await acao.run(() => api.post(`/colecoes/${id}/itens`, { ids: [item], modo: "excluir" }));
    if (r) { itens.reload(); col.reload(); }
  }

  return (
    <main className="pagina">
      <p><Link to="/colecoes">← Coleções</Link></p>
      <h1>{c.nome}</h1>
      <div className="linha" style={{ marginBottom: 14 }}>
        <Badge tone={c.tipo === "dinamica" ? "azul" : "neutro"}>{c.tipo === "dinamica" ? "Dinâmica" : "Manual"}</Badge>
        <span>{fmtNum(c.conjuntos)} conjunto(s)</span>
        <a className="botao botao-sec botao-peq" href={api.url(`/exportacao/colecoes/${id}`, { saida: "csv" })} download>Exportar CSV</a>
        <a className="botao botao-sec botao-peq" href={api.url(`/exportacao/colecoes/${id}`, { saida: "json" })} download>Exportar JSON</a>
        <a className="botao botao-sec botao-peq" href={api.url(`/exportacao/colecoes/${id}`, { saida: "jsonld" })} download>Exportar DCAT-BR</a>
        <button type="button" className="botao botao-perigo botao-peq" onClick={apagar}>Apagar coleção</button>
      </div>
      <ErrorBox error={acao.error} />
      {c.descricao && <p>{c.descricao}</p>}
      {c.tipo === "dinamica" && (
        <Card title="Regra (filtros salvos)">
          <FiltroChips filtros={c.regra_filtro as Filtros} rotulo="Regra da coleção" />
          {c.diff ? (
            <p style={{ marginTop: 10 }}>Desde a última extração: <strong>{c.diff.entraram.length}</strong> entraram e <strong>{c.diff.sairam.length}</strong> saíram.
              {c.diff.entraram.slice(0, 5).map((i) => <Link key={i} to={`/conjuntos/${i}`} style={{ marginLeft: 8 }}>{i}</Link>)}</p>
          ) : <p className="subtitulo">A comparação com a extração anterior aparece depois da próxima extração.</p>}
        </Card>
      )}
      <Card title="Editar coleção">
        <Field label="Nome"><input type="text" aria-label="Novo nome" style={{ width: "100%" }} value={nome ?? c.nome} onChange={(e) => { setNome(e.target.value); setSalvo(null); }} /></Field>
        <Field label="Descrição"><textarea aria-label="Nova descrição" rows={3} style={{ width: "100%" }} value={descricao ?? c.descricao ?? ""} onChange={(e) => { setDescricao(e.target.value); setSalvo(null); }} /></Field>
        {c.tipo === "dinamica" && (
          <Field label="Filtros da coleção" hint="Remova com × o que não quiser, ou descreva de novo em texto (o modelo propõe outra regra). Nada vale até salvar.">
            <FiltroChips filtros={(regra ?? c.regra_filtro) as Filtros} rotulo="Filtros da coleção" onChange={(f) => { setRegra(f); setSalvo(null); }} />
            <div className="linha" style={{ marginTop: 8 }}>
              <input type="text" aria-label="Descrever a regra de novo" style={{ flex: 1 }} maxLength={500} value={novaDescricao} onChange={(e) => setNovaDescricao(e.target.value)} placeholder="Ex.: só dados em CSV do Ministério da Saúde" />
              <button className="botao botao-sec" type="button" disabled={novaDescricao.trim().length < 2 || reproposta.pending} onClick={reproporRegra}>{reproposta.pending ? "Interpretando…" : "Propor nova regra"}</button>
            </div>
            <ErrorBox error={reproposta.error} />
          </Field>
        )}
        {salvo && <div className="info" role="status">{salvo}</div>}
        <button className="botao" type="button" disabled={(nome === null && descricao === null && regra === null) || !(nome ?? c.nome).trim() || (regra !== null && Object.keys(regra).length === 0) || acao.pending} onClick={salvarEdicao}>Salvar alterações</button>
      </Card>
      <Card title="Conjuntos da coleção">
        {itens.loading && <Loading />}
        {itens.data && (itens.data.itens.length === 0 ? <Empty>A coleção está vazia.</Empty> : (
          <>
            <table>
              <thead><tr><th>Conjunto</th><th>Organização</th><th>Qualidade</th><th /></tr></thead>
              <tbody>
                {itens.data.itens.map((i) => (
                  <tr key={i.id}>
                    <td><Link to={`/conjuntos/${i.id}`}>{i.titulo}</Link></td>
                    <td>{i.organizacao_titulo ?? "—"}</td>
                    <td><Nota value={i.nota_qualidade} /></td>
                    <td>{c.tipo === "manual"
                      ? <button type="button" className="botao botao-sec botao-peq" onClick={() => remover(i.id)}>Remover</button>
                      : <button type="button" className="botao botao-sec botao-peq" onClick={() => excluir(i.id)} title="Abre uma exceção: o conjunto sai desta coleção dinâmica">Excluir da coleção</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={itens.data.pagina} total={itens.data.total} size={itens.data.tamanho} onChange={setPage} />
          </>
        ))}
      </Card>
    </main>
  );
}
