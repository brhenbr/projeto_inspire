import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api, type Interpretacao, type RespostaChat } from "../api";
import { fmtNum } from "../format";
import { useAction, useApi } from "../hooks";
import { FiltroChips, ROTULOS, type Filtros } from "../FiltroChips";
import { Badge, Card, Empty, ErrorBox, Nota } from "../ui";
import type { LlmEstado } from "../api";

const EXEMPLOS = [
  "dados de saúde em formato CSV",
  "educação no estado de São Paulo",
  "conjuntos federais sobre meio ambiente atualizados mensalmente",
  "dados do IBGE com boa qualidade",
];
/** Mostra os filtros entendidos como etiquetas; o usuário sempre vê o que foi usado. */
export function FiltrosEntendidos({ i, onChange }: { i: Pick<Interpretacao, "filtros" | "explicacao" | "ignorados" | "organizacao">; onChange?: (novos: Filtros) => void }) {
  return (
    <div>
      <FiltroChips filtros={i.filtros} organizacao={i.organizacao} onChange={onChange} rotulo="Filtros entendidos" />
      {i.explicacao && <p className="subtitulo">{i.explicacao}</p>}
      {i.ignorados.length > 0 && (
        <div className="info" role="note">
          <strong>Não consegui usar:</strong>
          <ul>{i.ignorados.map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

export default function PerguntarPage() {
  const llm = useApi(() => api.get<LlmEstado>("/llm/estado"), []);
  const [pergunta, setPergunta] = useState("");
  const [resposta, setResposta] = useState<RespostaChat | null>(null);
  const acao = useAction();
  const e = llm.data;

  async function enviar(ev?: FormEvent, texto?: string) {
    ev?.preventDefault();
    const p = (texto ?? pergunta).trim();
    if (p.length < 2) return;
    if (texto) setPergunta(texto);
    const r = await acao.run(() => api.post<RespostaChat>("/chat/perguntar", { pergunta: p }));
    if (r) setResposta(r);
  }

  const buscaUrl = resposta
    ? `/conjuntos?${new URLSearchParams(Object.entries(resposta.filtros).map(([k, v]) => [k, String(v)])).toString()}`
    : "/conjuntos";

  return (
    <main className="pagina">
      <h1>Perguntar ao catálogo</h1>
      <p className="subtitulo">
        Escreva o que procura em linguagem natural. O modelo apenas <strong>traduz o pedido em filtros</strong>; quem
        busca é o catálogo, e você vê e pode ajustar os filtros usados.
      </p>
      {e && !e.habilitado && <Card title="Recurso desligado"><p>{e.motivo}</p></Card>}
      {e?.habilitado && (
        <p className="subtitulo">
          {e.externo
            ? <>Seu texto e a lista de temas e formatos são enviados ao provedor externo <strong>{e.host}</strong>. Não escreva dados pessoais.</>
            : e.simulado ? "Modo simulado: interpretação por regras simples, sem IA e sem enviar nada a ninguém." : "O modelo roda na infraestrutura do projeto."}
        </p>
      )}
      <form onSubmit={enviar} className="linha" style={{ marginBottom: 8 }}>
        <input type="text" aria-label="Sua pergunta" value={pergunta} maxLength={500} style={{ flex: 1 }}
          placeholder="Ex.: dados de saúde em formato CSV" onChange={(ev) => setPergunta(ev.target.value)} />
        <button className="botao" type="submit" disabled={acao.pending || !e?.habilitado}>{acao.pending ? "Interpretando…" : "Perguntar"}</button>
      </form>
      <div className="chips" style={{ marginBottom: 16 }}>
        {EXEMPLOS.map((x) => <button key={x} type="button" className="botao botao-sec botao-peq" onClick={() => enviar(undefined, x)} disabled={!e?.habilitado}>{x}</button>)}
      </div>
      <ErrorBox error={acao.error} />
      {resposta && (
        <>
          <Card title="Como entendi">
            <FiltrosEntendidos i={resposta} />
            {resposta.filtros_removidos.length > 0 && (
              <div className="info" role="note" data-testid="relaxados">
                Não havia resultados com todos os filtros; para achar algo, deixei de usar: {resposta.filtros_removidos.map((k) => ROTULOS[k] ?? k).join(", ")}.
              </div>
            )}
            <p className="subtitulo">Interpretado por {resposta.provedor.nome}{resposta.provedor.simulado ? " (sem IA)" : ""}.</p>
          </Card>
          <div className="linha" style={{ justifyContent: "space-between", margin: "12px 0" }}>
            <strong data-testid="total-chat">{fmtNum(resposta.resultado.total)} conjunto(s)</strong>
            <Link className="botao botao-sec botao-peq" to={buscaUrl}>Abrir na busca para refinar</Link>
          </div>
          {resposta.resultado.itens.length === 0 && <Empty>Nada encontrado com esses filtros. Abra na busca e remova algum.</Empty>}
          {resposta.resultado.itens.map((c) => (
            <article className="resultado" key={c.id}>
              <h3><Link to={`/conjuntos/${c.id}`}>{c.titulo}</Link></h3>
              <div className="meta">
                <Nota value={c.nota_qualidade} />
                {c.organizacao_titulo && <span>{c.organizacao_titulo}</span>}
                {c.formatos.slice(0, 4).map((f) => <Badge key={f}>{f}</Badge>)}
              </div>
            </article>
          ))}
        </>
      )}
    </main>
  );
}
