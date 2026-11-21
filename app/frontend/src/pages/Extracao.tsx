import { Fragment, useState } from "react";

import { ApiError, api, type Disponibilidade, type Extracao, type EstadoExtracao } from "../api";
import { ESTADOS_EXECUCAO, fmtDate, fmtNum, minutesUntil } from "../format";
import { useApi } from "../hooks";
import { Badge, Bar, Card, Empty, ErrorBox, Loading } from "../ui";

type Fila = Record<string, number>;
const ATIVOS = new Set(["enfileirada", "em_andamento", "pausada"]);

function quando(d: Disponibilidade): string {
  const min = minutesUntil(d.disponivel_em);
  return d.disponivel_em ? `Disponível às ${fmtDate(d.disponivel_em, true)}${min !== null ? ` (em ${min} min)` : ""}` : "";
}

export default function ExtracaoPage() {
  const estado = useApi(() => api.get<EstadoExtracao>("/extracoes/estado"), [], 2500);
  const historico = useApi(() => api.get<Extracao[]>("/extracoes", { limite: 15 }), [], 4000);
  const [forcar, setForcar] = useState(false);
  const [msg, setMsg] = useState<{ tom: "ok" | "info" | "erro"; texto: string } | null>(null);
  const [pendente, setPendente] = useState(false);
  const [aberta, setAberta] = useState<number | null>(null);
  const e = estado.data;

  async function pedir(tipo: "incremental" | "completa") {
    if (forcar && !window.confirm("Forçar ignora o intervalo mínimo entre extrações e sobrecarrega o portal. Continuar?")) return;
    setPendente(true);
    setMsg(null);
    try {
      const r = await api.post<Extracao>("/extracoes", { tipo, forcar });
      setMsg({ tom: "ok", texto: `Extração #${r.id} (${tipo === "completa" ? "completa" : "incremental"}) ${ESTADOS_EXECUCAO[r.estado]?.toLowerCase() ?? r.estado}.` });
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        const data = err.data as { disponivel_em?: string };
        setMsg({ tom: "info", texto: `${err.detail}. ${data?.disponivel_em ? `Disponível às ${fmtDate(data.disponivel_em, true)}.` : ""}` });
      } else {
        setMsg({ tom: "erro", texto: err instanceof Error ? err.message : String(err) });
      }
    } finally {
      setPendente(false);
      estado.reload();
      historico.reload();
    }
  }
  async function cancelar(id: number) {
    try {
      await api.post(`/extracoes/${id}/cancelar`);
      setMsg({ tom: "info", texto: "Cancelamento solicitado." });
    } catch (err) {
      setMsg({ tom: "erro", texto: err instanceof Error ? err.message : String(err) });
    }
    estado.reload();
  }

  const ativa = e?.ativa;
  const fila = (ativa?.totais?.fila ?? {}) as Fila;
  const total = Object.values(fila).reduce((a, b) => a + b, 0);
  const feitos = total - (fila.pendente ?? 0);

  return (
    <main className="pagina">
      <h1>Extração do catálogo</h1>
      <p className="subtitulo">Traz os metadados do dados.gov.br. Só os metadados: os arquivos continuam nos órgãos. O sistema impede pedidos repetidos para não sobrecarregar o portal.</p>
      {estado.loading && <Loading />}
      <ErrorBox error={estado.error} onRetry={estado.reload} />
      {msg && <div className={msg.tom === "ok" ? "ok" : msg.tom === "info" ? "info" : "erro"} role="status">{msg.texto}</div>}

      {e && (
        <div className="grade grade-2">
          <Card title="Atualizar o catálogo">
            {ativa ? (
              <div role="status">
                <p><strong>Extração #{ativa.id} {ESTADOS_EXECUCAO[ativa.estado]?.toLowerCase()}</strong> ({ativa.tipo === "completa" ? "completa" : "incremental"}){ativa.cancelamento_solicitado && " — cancelamento solicitado"}</p>
                {total > 0 ? (
                  <>
                    <Bar value={feitos} max={total} />
                    <p className="subtitulo">{fmtNum(feitos)} de {fmtNum(total)} conjuntos processados</p>
                  </>
                ) : (
                  <p className="subtitulo">Preparando: dimensões, organizações e listagem…</p>
                )}
                <button className="botao botao-perigo" type="button" onClick={() => cancelar(ativa.id)} disabled={ativa.cancelamento_solicitado}>Cancelar extração</button>
              </div>
            ) : (
              <>
                <div className="linha">
                  <button className="botao" type="button" disabled={pendente || (!forcar && !e.incremental.pode_pedir)} onClick={() => pedir("incremental")}>Atualizar catálogo</button>
                  <button className="botao botao-sec" type="button" disabled={pendente || (!forcar && !e.completa.pode_pedir)} onClick={() => pedir("completa")}>Extração completa</button>
                </div>
                {!forcar && !e.incremental.pode_pedir && <p className="info">Atualização incremental indisponível agora: {e.incremental.motivo}. {quando(e.incremental)}</p>}
                {!forcar && !e.completa.pode_pedir && <p className="subtitulo">Extração completa: {e.completa.motivo}. {quando(e.completa)}</p>}
                <label className="linha" style={{ marginTop: 10 }}>
                  <input type="checkbox" checked={forcar} onChange={(ev) => setForcar(ev.target.checked)} /> Forçar (ignora o intervalo mínimo)
                </label>
                <p className="subtitulo">
                  A <strong>atualização</strong> busca só o que mudou desde a última vez. A <strong>completa</strong> refaz todos os conjuntos.
                </p>
              </>
            )}
          </Card>
          <Card title="Situação">
            <ul>
              <li>Última extração completa: {e.ultima_completa_em ? `${fmtDate(e.ultima_completa_em, true)} (há ${e.dias_desde_ultima_completa} dia(s))` : "nunca"}</li>
              <li>{e.sugerir_completa ? <Badge tone="medio">Recomendado refazer a extração completa</Badge> : <Badge tone="bom">Extração completa em dia</Badge>}</li>
            </ul>
            <p className="subtitulo">A extração completa semanal captura mudanças que a atualização incremental pode não perceber.</p>
          </Card>
        </div>
      )}

      <Card title="Histórico">
        {historico.data && (historico.data.length === 0 ? <Empty>Nenhuma extração ainda.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Tipo</th><th>Situação</th><th>Início</th><th>Fim</th><th /></tr></thead>
            <tbody>
              {historico.data.map((x) => (
                <Fragment key={x.id}>
                  <tr>
                    <td>{x.id}</td>
                    <td>{x.tipo === "completa" ? "Completa" : "Incremental"}{x.forcada && <Badge tone="medio">forçada</Badge>}</td>
                    <td><Badge tone={x.estado === "concluida" ? "bom" : x.estado === "falhou" ? "ruim" : ATIVOS.has(x.estado) ? "azul" : "medio"}>{ESTADOS_EXECUCAO[x.estado] ?? x.estado}</Badge></td>
                    <td>{fmtDate(x.iniciada_em ?? x.criada_em, true)}</td>
                    <td>{fmtDate(x.finalizada_em, true)}</td>
                    <td><button type="button" className="botao botao-sec botao-peq" onClick={() => setAberta(aberta === x.id ? null : x.id)}>{aberta === x.id ? "Ocultar relatório" : "Relatório"}</button></td>
                  </tr>
                  {aberta === x.id && <tr><td colSpan={6}><Relatorio x={x} /></td></tr>}
                </Fragment>
              ))}
            </tbody>
          </table>
        ))}
      </Card>
    </main>
  );
}

function Relatorio({ x }: { x: Extracao }) {
  const t = x.totais as Record<string, unknown>;
  const n = (k: string) => fmtNum(t[k] as number | undefined);
  const div = (t.divergencias_por_organizacao ?? []) as { organizacao: string; esperado: number; listado: number }[];
  return (
    <div aria-label={`Relatório da extração ${x.id}`}>
      {x.erro && <div className="erro">{x.erro}</div>}
      <div className="chips" style={{ marginBottom: 8 }}>
        <Badge>Listados {n("listados")} de {n("esperados")} esperados</Badge>
        {t.cobertura !== undefined && <Badge tone={Number(t.cobertura) >= 0.99 ? "bom" : "ruim"}>Cobertura {(Number(t.cobertura) * 100).toFixed(1)}%</Badge>}
        <Badge tone="bom">{n("novos")} novos</Badge>
        <Badge tone="azul">{n("alterados")} alterados</Badge>
        <Badge>{n("inalterados")} inalterados</Badge>
        <Badge>{n("reaparecidos")} reaparecidos</Badge>
        <Badge tone={Number(t.removidos) > 0 ? "medio" : "neutro"}>{n("removidos")} removidos</Badge>
        <Badge title="Detalhes que não foi preciso buscar de novo">{n("detalhes_evitados")} detalhes evitados</Badge>
        <Badge tone={Number(t.sem_detalhe) > 0 ? "ruim" : "neutro"} title="O portal não entrega o detalhe">{n("sem_detalhe")} sem detalhe</Badge>
        <Badge tone={Number(t.erros) > 0 ? "ruim" : "neutro"}>{n("erros")} erros</Badge>
        {t.duracao_s !== undefined && <Badge>{fmtNum(t.duracao_s as number)} s</Badge>}
        {t.remocao_aplicada === false && <Badge tone="medio" title="A listagem veio incompleta; por segurança nada foi marcado como removido">remoções não aplicadas</Badge>}
      </div>
      {div.length > 0 && (
        <table>
          <thead><tr><th>Organização com diferença</th><th className="num">Declarado</th><th className="num">Coletado</th></tr></thead>
          <tbody>{div.slice(0, 10).map((d) => <tr key={d.organizacao}><td>{d.organizacao}</td><td className="num">{fmtNum(d.esperado)}</td><td className="num">{fmtNum(d.listado)}</td></tr>)}</tbody>
        </table>
      )}
    </div>
  );
}
