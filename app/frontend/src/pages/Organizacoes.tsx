import { useState, type FormEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { ESFERAS, fmtNum } from "../format";
import { useApi } from "../hooks";
import { Bar, Badge, Card, Empty, ErrorBox, Kpi, Loading, Nota, Pagination } from "../ui";

type OrgItem = { slug: string; titulo: string; esfera: string | null; uf: string | null; conjuntos: number; nota_media: number | string | null; curados: number; aprovados: number; sem_detalhe: number };
type OrgLista = { total: number; pagina: number; tamanho: number; itens: OrgItem[] };
type OrgDetalhe = {
  slug: string; titulo: string; descricao: string | null; esfera: string | null; uf: string | null; municipio: string | null; qtd_declarada: number;
  resumo: { conjuntos: number; nota_media: number | string | null; curados: number; aprovados: number; sem_detalhe: number };
  regras_que_mais_falham: { regra: string; nome: string; dimensao: string; conjuntos: number }[];
  dimensoes: { dimensao: string; nota: number | string }[];
};

export function OrganizacoesPage() {
  const [sp, setSp] = useSearchParams();
  const page = Number(sp.get("pagina") ?? 1);
  const ordem = sp.get("ordem") ?? "conjuntos";
  const [q, setQ] = useState(sp.get("q") ?? "");
  const dados = useApi(() => api.get<OrgLista>("/organizacoes", { q: sp.get("q"), esfera: sp.get("esfera"), pagina: page, tamanho: 20, ordem }), [sp.toString()]);

  function set(chave: string, valor: string) {
    const n = new URLSearchParams(sp);
    if (valor) n.set(chave, valor); else n.delete(chave);
    n.delete("pagina");
    setSp(n);
  }
  function enviar(e: FormEvent) { e.preventDefault(); set("q", q.trim()); }

  return (
    <main className="pagina">
      <h1>Organizações</h1>
      <p className="subtitulo">Órgãos e entidades que publicam no portal, com a qualidade média dos seus metadados.</p>
      <form className="busca-form" onSubmit={enviar} role="search">
        <input type="search" aria-label="Buscar organização" placeholder="Nome da organização" value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label="Esfera" value={sp.get("esfera") ?? ""} onChange={(e) => set("esfera", e.target.value)}>
          <option value="">Todas as esferas</option>
          {Object.entries(ESFERAS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select aria-label="Ordenar" value={ordem} onChange={(e) => set("ordem", e.target.value)}>
          <option value="conjuntos">Mais conjuntos</option>
          <option value="nota">Menor nota média</option>
          <option value="curados">Mais curados</option>
          <option value="nome">Nome</option>
        </select>
        <button className="botao" type="submit">Buscar</button>
      </form>
      {dados.loading && <Loading />}
      <ErrorBox error={dados.error} onRetry={dados.reload} />
      {dados.data && (
        <Card>
          {dados.data.itens.length === 0 ? <Empty>Nenhuma organização encontrada.</Empty> : (
            <table>
              <thead><tr><th>Organização</th><th>Esfera</th><th className="num">Conjuntos</th><th>Nota média</th><th className="num">Curados</th><th className="num">Sem detalhe</th></tr></thead>
              <tbody>
                {dados.data.itens.map((o) => (
                  <tr key={o.slug}>
                    <td><Link to={`/organizacoes/${o.slug}`}>{o.titulo}</Link></td>
                    <td>{o.esfera ? ESFERAS[o.esfera] : "—"}{o.uf ? ` · ${o.uf}` : ""}</td>
                    <td className="num">{fmtNum(o.conjuntos)}</td>
                    <td><Nota value={o.nota_media} /></td>
                    <td className="num">{fmtNum(o.curados)}</td>
                    <td className="num">{fmtNum(o.sem_detalhe)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Pagination page={dados.data.pagina} total={dados.data.total} size={dados.data.tamanho} onChange={(p) => { const n = new URLSearchParams(sp); n.set("pagina", String(p)); setSp(n); }} />
        </Card>
      )}
    </main>
  );
}

export function OrganizacaoPage() {
  const { slug = "" } = useParams();
  const dados = useApi(() => api.get<OrgDetalhe>(`/organizacoes/${slug}`), [slug]);
  const o = dados.data;
  if (dados.loading) return <main className="pagina"><Loading /></main>;
  if (dados.error) return <main className="pagina"><ErrorBox error={dados.error} onRetry={dados.reload} /><Link to="/organizacoes">Voltar</Link></main>;
  if (!o) return null;
  const tone = (n: number) => (n >= 70 ? "bom" : n >= 40 ? "medio" : "ruim");
  const dif = o.qtd_declarada - o.resumo.conjuntos;
  return (
    <main className="pagina">
      <p><Link to="/organizacoes">← Organizações</Link></p>
      <h1>{o.titulo}</h1>
      <div className="linha" style={{ marginBottom: 12 }}>
        {o.esfera && <Badge>{ESFERAS[o.esfera] ?? o.esfera}</Badge>}
        {o.uf && <Badge>{o.uf}</Badge>}
        {o.municipio && <Badge>{o.municipio}</Badge>}
        <Link className="botao botao-sec botao-peq" to={`/conjuntos?organizacao=${o.slug}`}>Ver os conjuntos</Link>
        <Link className="botao botao-sec botao-peq" to={`/curadoria?organizacao=${o.slug}`}>Fila de curadoria</Link>
      </div>
      <div className="grade grade-kpi">
        <Kpi label="Conjuntos coletados" value={fmtNum(o.resumo.conjuntos)} hint={`${fmtNum(o.qtd_declarada)} declarados pelo portal${dif ? ` (diferença ${fmtNum(dif)})` : ""}`} />
        <Kpi label="Nota média" value={o.resumo.nota_media === null ? "—" : fmtNum(o.resumo.nota_media)} />
        <Kpi label="Curados" value={fmtNum(o.resumo.curados)} />
        <Kpi label="Aprovados" value={fmtNum(o.resumo.aprovados)} />
        <Kpi label="Sem detalhe" value={fmtNum(o.resumo.sem_detalhe)} />
      </div>
      <div className="grade grade-2">
        <Card title="Qualidade por dimensão">
          {o.dimensoes.length === 0 ? <Empty>Sem notas.</Empty> : (
            <div className="lista-barras">
              {o.dimensoes.map((d) => (
                <div key={d.dimensao} style={{ display: "contents" }}>
                  <span>{d.dimensao}</span><Bar value={Number(d.nota)} tone={tone(Number(d.nota))} /><span>{fmtNum(d.nota)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card title="O que mais precisa melhorar">
          {o.regras_que_mais_falham.length === 0 ? <Empty>Nenhuma falha registrada.</Empty> : (
            <table>
              <thead><tr><th>Verificação</th><th className="num">Conjuntos que falham</th></tr></thead>
              <tbody>{o.regras_que_mais_falham.map((r) => <tr key={r.regra}><td>{r.nome} <span className="subtitulo">({r.dimensao})</span></td><td className="num">{fmtNum(r.conjuntos)}</td></tr>)}</tbody>
            </table>
          )}
        </Card>
      </div>
      {o.descricao && <Card title="Sobre"><p>{o.descricao}</p></Card>}
    </main>
  );
}
