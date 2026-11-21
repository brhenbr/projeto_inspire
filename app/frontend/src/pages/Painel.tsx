import { Link } from "react-router-dom";

import { api, type EstadoExtracao } from "../api";
import { ESFERAS, ESTADOS_CURADORIA, ESTADOS_EXECUCAO, fmtDate, fmtNum } from "../format";
import { useApi } from "../hooks";
import { Bar, Card, Empty, ErrorBox, Kpi, Loading } from "../ui";

type Grupo = { valor: string | null; n: number };
type Painel = {
  totais: Record<string, number | string | null>;
  por_esfera: Grupo[];
  por_tema: Grupo[];
  por_formato: Grupo[];
  por_licenca: Grupo[];
  por_periodicidade: Grupo[];
  qualidade_faixas: { faixa: string; n: number }[];
  por_estado_curadoria: Grupo[];
  ultima_extracao: Record<string, string | number | null> | null;
};

function Barras({ itens, rotulo }: { itens: Grupo[]; rotulo?: (v: string) => string }) {
  const max = Math.max(1, ...itens.map((i) => i.n));
  if (!itens.length) return <Empty>Sem dados.</Empty>;
  return (
    <div className="lista-barras">
      {itens.map((i) => (
        <div key={String(i.valor)} style={{ display: "contents" }}>
          <span>{rotulo ? rotulo(String(i.valor)) : i.valor}</span>
          <Bar value={i.n} max={max} />
          <span>{fmtNum(i.n)}</span>
        </div>
      ))}
    </div>
  );
}

export default function PainelPage() {
  const painel = useApi(() => api.get<Painel>("/painel"), []);
  const extracao = useApi(() => api.get<EstadoExtracao>("/extracoes/estado"), [], 5000);
  const p = painel.data;

  if (painel.loading) return <main className="pagina"><Loading /></main>;
  if (painel.error) return <main className="pagina"><ErrorBox error={painel.error} onRetry={painel.reload} /></main>;
  if (!p) return null;
  const t = p.totais;
  const vazio = Number(t.conjuntos ?? 0) === 0;

  return (
    <main className="pagina">
      <h1>Painel do catálogo</h1>
      <p className="subtitulo">Visão geral dos metadados do dados.gov.br espelhados e da curadoria.</p>

      {extracao.data?.ativa && (
        <div className="info" role="status">
          Há uma extração em andamento ({ESTADOS_EXECUCAO[extracao.data.ativa.estado] ?? extracao.data.ativa.estado}).{" "}
          <Link to="/extracao">Acompanhar</Link>
        </div>
      )}

      {vazio ? (
        <Card title="Nenhum dado ainda">
          <p>O catálogo ainda não foi extraído. Faça a primeira extração para começar.</p>
          <Link className="botao" to="/extracao">Ir para a extração</Link>
        </Card>
      ) : (
        <>
          <div className="grade grade-kpi">
            <Kpi label="Conjuntos de dados" value={fmtNum(t.conjuntos)} hint={`${fmtNum(t.recursos)} recursos`} />
            <Kpi label="Organizações" value={fmtNum(t.organizacoes)} />
            <Kpi label="Nota média de qualidade" value={t.nota_media === null ? "—" : fmtNum(t.nota_media)} hint="0 a 100" />
            <Kpi label="Conjuntos curados" value={fmtNum(t.curados)} hint="com alguma alteração" />
            <Kpi label="Sem detalhe no portal" value={fmtNum(t.sem_detalhe)} hint="detalhe indisponível" />
            <Kpi label="Removidos do portal" value={fmtNum(t.removidos)} />
          </div>

          <div className="grade grade-2">
            <Card title="Distribuição da qualidade">
              <div className="lista-barras">
                {p.qualidade_faixas.map((f) => (
                  <div key={f.faixa} style={{ display: "contents" }}>
                    <span>Nota {f.faixa}</span>
                    <Bar value={f.n} max={Math.max(1, ...p.qualidade_faixas.map((x) => x.n))} tone={f.faixa.startsWith("0") || f.faixa.startsWith("20") ? "ruim" : f.faixa.startsWith("40") ? "medio" : "bom"} />
                    <span>{fmtNum(f.n)}</span>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Andamento da curadoria">
              <Barras itens={p.por_estado_curadoria} rotulo={(v) => ESTADOS_CURADORIA[v] ?? v} />
            </Card>
            <Card title="Por esfera"><Barras itens={p.por_esfera} rotulo={(v) => ESFERAS[v] ?? v} /></Card>
            <Card title="Temas mais frequentes"><Barras itens={p.por_tema} /></Card>
            <Card title="Formatos dos recursos"><Barras itens={p.por_formato} /></Card>
            <Card title="Última extração">
              {p.ultima_extracao ? (
                <ul>
                  <li>{ESTADOS_EXECUCAO[String(p.ultima_extracao.estado)] ?? p.ultima_extracao.estado} ({String(p.ultima_extracao.tipo)}) em {fmtDate(String(p.ultima_extracao.finalizada_em), true)}</li>
                  <li>{fmtNum(p.ultima_extracao.listados)} conjuntos listados</li>
                  <li>{fmtNum(p.ultima_extracao.novos)} novos · {fmtNum(p.ultima_extracao.alterados)} alterados · {fmtNum(p.ultima_extracao.removidos)} removidos</li>
                </ul>
              ) : (
                <Empty>Nenhuma extração concluída.</Empty>
              )}
              <Link to="/extracao">Ver extrações</Link>
            </Card>
          </div>
        </>
      )}
    </main>
  );
}
