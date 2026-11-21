import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, type Busca, type Colecao } from "../api";
import { fmtNum } from "../format";
import { useAction, useApi } from "../hooks";
import { Badge, Card, Empty, ErrorBox, Field, Loading, Nota, Pagination } from "../ui";

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
    </main>
  );
}

export function ColecaoPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const col = useApi(() => api.get<Colecao>(`/colecoes/${id}`), [id]);
  const [page, setPage] = useState(1);
  const itens = useApi(() => api.get<Busca>(`/colecoes/${id}/conjuntos`, { pagina: page, tamanho: 20 }), [id, page]);
  const [nome, setNome] = useState<string | null>(null);
  const acao = useAction();
  const c = col.data;

  if (col.loading) return <main className="pagina"><Loading /></main>;
  if (col.error) return <main className="pagina"><ErrorBox error={col.error} /><Link to="/colecoes">Voltar</Link></main>;
  if (!c) return null;

  async function renomear() {
    const r = await acao.run(() => api.put(`/colecoes/${id}`, { nome }));
    if (r) { setNome(null); col.reload(); }
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
        <button type="button" className="botao botao-perigo botao-peq" onClick={apagar}>Apagar coleção</button>
      </div>
      <ErrorBox error={acao.error} />
      {c.descricao && <p>{c.descricao}</p>}
      {c.tipo === "dinamica" && (
        <Card title="Regra (filtros salvos)">
          <div className="chips">{Object.entries(c.regra_filtro).map(([k, v]) => <Badge key={k} tone="azul">{k}: {String(v)}</Badge>)}</div>
          {c.diff ? (
            <p style={{ marginTop: 10 }}>Desde a última extração: <strong>{c.diff.entraram.length}</strong> entraram e <strong>{c.diff.sairam.length}</strong> saíram.
              {c.diff.entraram.slice(0, 5).map((i) => <Link key={i} to={`/conjuntos/${i}`} style={{ marginLeft: 8 }}>{i}</Link>)}</p>
          ) : <p className="subtitulo">A comparação com a extração anterior aparece depois da próxima extração.</p>}
        </Card>
      )}
      <Card title="Renomear">
        <div className="linha">
          <input type="text" aria-label="Novo nome" value={nome ?? c.nome} onChange={(e) => setNome(e.target.value)} />
          <button className="botao" type="button" disabled={nome === null || !nome.trim() || acao.pending} onClick={renomear}>Salvar nome</button>
        </div>
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
