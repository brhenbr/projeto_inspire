import { useEffect, useState } from "react";

import { fetchSaude, type Saude } from "./api";

type Estado =
  | { tipo: "carregando" }
  | { tipo: "pronto"; saude: Saude }
  | { tipo: "erro"; mensagem: string };

export default function App() {
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });

  useEffect(() => {
    const controller = new AbortController();
    fetchSaude(controller.signal)
      .then((saude) => setEstado({ tipo: "pronto", saude }))
      .catch((erro: unknown) => {
        if (controller.signal.aborted) return;
        setEstado({ tipo: "erro", mensagem: erro instanceof Error ? erro.message : "Erro desconhecido" });
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="pagina">
      <h1>Inspire Catálogo</h1>
      <p className="subtitulo">Extração, discovery e curadoria do catálogo do dados.gov.br</p>
      <section aria-label="Estado do sistema" className="cartao">
        <h2>Estado do sistema</h2>
        {estado.tipo === "carregando" && <p>Verificando…</p>}
        {estado.tipo === "erro" && <p role="alert">Não foi possível falar com a API. {estado.mensagem}</p>}
        {estado.tipo === "pronto" && (
          <ul>
            <li>API: {estado.saude.status === "ok" ? "funcionando" : "com problemas"}</li>
            <li>Banco de dados: {estado.saude.banco === "ok" ? "funcionando" : "indisponível"}</li>
            <li>Versão: {estado.saude.versao}</li>
          </ul>
        )}
      </section>
    </main>
  );
}
