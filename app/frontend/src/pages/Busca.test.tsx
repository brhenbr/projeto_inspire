import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { calls, mockApi, renderAt } from "../test-utils";
import BuscaPage from "./Busca";

const item = (id: string, titulo: string, extra = {}) => ({
  id, titulo, resumo: "Resumo do conjunto", organizacao_slug: "ipea", organizacao_titulo: "IPEA", esfera: "federal", uf: null,
  temas: ["saude"], formatos: ["CSV"], tags: [], licenca: "cc-by", periodicidade: "MENSAL", nota_qualidade: 82.5, prioridade: null,
  estado_curadoria: "pendente", curado: false, selo_portal: null, sem_detalhe: false, removido: false, qtd_recursos: 2,
  metadados_atualizados_em: "2026-01-02T00:00:00Z", ...extra,
});
const resposta = (over = {}) => ({
  total: 2, pagina: 1, tamanho: 20, aproximada: false,
  itens: [item("a", "Saúde da população"), item("b", "Educação básica", { curado: true, sem_detalhe: true, nota_qualidade: null })],
  facetas: {
    organizacao: [{ valor: "ipea", rotulo: "IPEA", n: 2 }], formato: [{ valor: "CSV", rotulo: "CSV", n: 2 }],
    tema: [], esfera: [], licenca: [], periodicidade: [], selo: [], estado_curadoria: [],
  },
  ...over,
});
const apiMock = (r = resposta()) => mockApi({ "/conjuntos": r, "/colecoes": [], "/llm/tarefas": [], "/llm/estado": { habilitado: false } });
const ui = () => (
  <Routes>
    <Route path="/conjuntos" element={<BuscaPage />} />
  </Routes>
);
const buscas = (spy: ReturnType<typeof apiMock>) => calls(spy).filter((c) => c.url.pathname.endsWith("/conjuntos"));

describe("Busca", () => {
  it("lista os resultados com nota, curadoria e avisos", async () => {
    apiMock();
    renderAt(ui(), "/conjuntos");

    expect(await screen.findByText("Saúde da população")).toBeInTheDocument();
    expect(screen.getByTestId("total")).toHaveTextContent("2 conjunto(s)");
    expect(screen.getByText("Nota 82,5")).toBeInTheDocument();
    expect(screen.getByText("Curado")).toBeInTheDocument();
    expect(screen.getByText("Sem detalhe")).toBeInTheDocument();
    expect(screen.getByText("sem nota")).toBeInTheDocument();
  });

  it("a busca vai para a URL e para a API", async () => {
    const spy = apiMock();
    renderAt(ui(), "/conjuntos");
    await screen.findByText("Saúde da população");

    await userEvent.type(screen.getByLabelText("Texto da busca"), "saúde população{enter}");

    const ultima = buscas(spy).at(-1)!;
    expect(ultima.url.searchParams.get("q")).toBe("saúde população");
    expect(ultima.url.searchParams.get("pagina")).toBe("1");
  });

  it("clicar numa faceta aplica o filtro e mostra o filtro ativo; clicar de novo remove", async () => {
    const spy = apiMock();
    renderAt(ui(), "/conjuntos");
    await screen.findByText("Saúde da população");

    await userEvent.click(within(screen.getByLabelText("Filtros")).getByRole("button", { name: /IPEA/ }));
    expect(buscas(spy).at(-1)!.url.searchParams.get("organizacao")).toBe("ipea");
    expect(await screen.findByRole("button", { name: /organizacao: ipea/ })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /organizacao: ipea/ }));
    expect(buscas(spy).at(-1)!.url.searchParams.get("organizacao")).toBeNull();
  });

  it("filtros e página vêm da URL (link compartilhável)", async () => {
    const spy = apiMock();
    renderAt(ui(), "/conjuntos?formato=CSV&ordem=nota&pagina=3");
    await screen.findByText("Saúde da população");

    const c = buscas(spy)[0];
    expect(c.url.searchParams.get("formato")).toBe("CSV");
    expect(c.url.searchParams.get("ordem")).toBe("nota");
    expect(c.url.searchParams.get("pagina")).toBe("3");
  });

  it("explica quando a busca foi aproximada e quando não achou nada", async () => {
    apiMock(resposta({ aproximada: true }));
    const { unmount } = renderAt(ui(), "/conjuntos?q=saude");
    expect(await screen.findByText(/Nenhum resultado exato/)).toBeInTheDocument();
    unmount();

    apiMock(resposta({ total: 0, itens: [] }));
    renderAt(ui(), "/conjuntos?q=xyz");
    expect(await screen.findByText(/Nada encontrado/)).toBeInTheDocument();
  });

  it("oferece exportar o resultado com os mesmos filtros", async () => {
    apiMock();
    renderAt(ui(), "/conjuntos?q=saude&organizacao=ipea");
    await screen.findByText("Saúde da população");

    const csv = screen.getByRole("link", { name: "Exportar CSV" });
    expect(csv.getAttribute("href")).toContain("/api/v1/exportacao/conjuntos?");
    expect(csv.getAttribute("href")).toContain("organizacao=ipea");
    expect(csv.getAttribute("href")).toContain("saida=csv");
  });
});
