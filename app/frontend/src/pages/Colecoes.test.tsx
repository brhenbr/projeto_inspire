import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { calls, mockApi, renderAt } from "../test-utils";
import { ColecaoPage, ColecoesPage } from "./Colecoes";

const proposta = {
  nome_sugerido: "Bases sociais de saúde",
  filtros: { tema: "saude,educacao", esfera: "federal" },
  explicacao: "Saúde, federal.",
  ignorados: [],
  organizacao: null,
  provedor: { nome: "groq", externo: true, simulado: false },
  resultado: { total: 7, pagina: 1, tamanho: 5, aproximada: false, itens: [{ id: "a", titulo: "Saúde da população" }] },
};
const ui = () => (
  <Routes>
    <Route path="/colecoes" element={<ColecoesPage />} />
    <Route path="/colecoes/:id" element={<ColecaoPage />} />
  </Routes>
);
const base = { "/temas": [{ slug: "saude", titulo: "Saúde" }, { slug: "educacao", titulo: "Educação" }], "/colecoes": [], "/llm/estado": { habilitado: true, externo: true, simulado: false, host: "api.groq.com", limite_por_execucao: 50 } };

describe("Coleção por texto", () => {
  it("propõe filtros, permite remover um, atualiza a contagem e só cria ao confirmar", async () => {
    const spy = mockApi({
      ...base,
      "/chat/colecao": proposta,
      "/conjuntos": { total: 30, pagina: 1, tamanho: 5, aproximada: false, itens: [{ id: "b", titulo: "Outro conjunto" }] },
    });
    renderAt(ui(), "/colecoes");
    await userEvent.type(await screen.findByLabelText("Descrição da coleção"), "bases sociais de saúde");
    await userEvent.click(screen.getByRole("button", { name: "Propor filtros" }));

    expect(await screen.findByText("Saúde da população")).toBeInTheDocument();
    expect(screen.getByTestId("total-proposta")).toHaveTextContent("7 conjunto(s)");
    expect(calls(spy).some((c) => c.init?.method === "POST" && c.url.pathname.endsWith("/colecoes"))).toBe(false); // nada criado ainda

    await userEvent.click(screen.getByRole("button", { name: "Remover Esfera: federal" }));
    expect(await screen.findByText("Outro conjunto")).toBeInTheDocument();
    expect(screen.getByTestId("total-proposta")).toHaveTextContent("30 conjunto(s)");
    const busca = calls(spy).filter((c) => c.url.pathname.endsWith("/conjuntos")).at(-1);
    expect(busca?.url.searchParams.get("tema")).toBe("saude,educacao");
    expect(busca?.url.searchParams.has("esfera")).toBe(false);
  });

  it("mostra um chip por tema com o nome do tema; remover um deixa o outro; restaurar volta à proposta", async () => {
    mockApi({
      ...base,
      "/chat/colecao": proposta,
      "/conjuntos": { total: 3, pagina: 1, tamanho: 5, aproximada: false, itens: [] },
    });
    renderAt(ui(), "/colecoes");
    await userEvent.type(await screen.findByLabelText("Descrição da coleção"), "saúde e educação federais");
    await userEvent.click(screen.getByRole("button", { name: "Propor filtros" }));
    expect(await screen.findByText("Tema: Saúde")).toBeInTheDocument();
    expect(screen.getByText("Tema: Educação")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Remover Tema: Saúde" }));
    expect(screen.queryByText("Tema: Saúde")).not.toBeInTheDocument();
    expect(screen.getByText("Tema: Educação")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Restaurar filtros propostos" })); // sem nova chamada ao LLM
    expect(await screen.findByText("Tema: Saúde")).toBeInTheDocument();
  });

  it("não deixa criar uma coleção que daria zero conjuntos", async () => {
    mockApi({ ...base, "/chat/colecao": { ...proposta, resultado: { ...proposta.resultado, total: 0, itens: [] } } });
    renderAt(ui(), "/colecoes");
    await userEvent.type(await screen.findByLabelText("Descrição da coleção"), "algo raro");
    await userEvent.click(screen.getByRole("button", { name: "Propor filtros" }));

    expect(await screen.findByText(/Nenhum conjunto com esses filtros/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar coleção dinâmica" })).toBeDisabled();
  });

  it("editar uma coleção dinâmica: remove um filtro, troca o nome e salva tudo de uma vez", async () => {
    const spy = mockApi({
      ...base,
      "/colecoes/5/conjuntos": { total: 0, pagina: 1, tamanho: 20, aproximada: false, itens: [] },
      "/colecoes/5": (_u: URL, init?: RequestInit) => init?.method === "PUT"
        ? { id: 5, nome: "Novo", tipo: "dinamica", conjuntos: 1, regra_filtro: {}, descricao: null }
        : { id: 5, nome: "Antigo", tipo: "dinamica", conjuntos: 9, descricao: "d", regra_filtro: { tema: "saude,educacao", esfera: "federal" }, diff: null },
    });
    renderAt(ui(), "/colecoes/5");
    await userEvent.clear(await screen.findByLabelText("Novo nome"));
    await userEvent.type(screen.getByLabelText("Novo nome"), "Novo");
    const caixa = screen.getByLabelText("Filtros da coleção");
    await userEvent.click(within(caixa).getByRole("button", { name: "Remover Esfera: federal" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    const put = calls(spy).find((c) => c.init?.method === "PUT");
    expect(JSON.parse(String(put?.init?.body))).toEqual({ nome: "Novo", regra_filtro: { tema: "saude,educacao" } });
    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
  });

  it("criar envia a coleção dinâmica com os filtros ajustados e abre a coleção criada", async () => {
    const criada = { id: 9, nome: "Nome sugerido", tipo: "dinamica", conjuntos: 7, regra_filtro: {}, descricao: null, diff: null };
    const spy = mockApi({
      ...base,
      "/chat/colecao": proposta,
      "/colecoes/9/conjuntos": { total: 0, pagina: 1, tamanho: 20, aproximada: false, itens: [] },
      "/colecoes/9": criada,
      "/colecoes": (_u: URL, init?: RequestInit) => (init?.method === "POST" ? criada : []),
    });
    renderAt(ui(), "/colecoes");
    await userEvent.type(await screen.findByLabelText("Descrição da coleção"), "bases sociais de saúde");
    await userEvent.click(screen.getByRole("button", { name: "Propor filtros" }));
    await userEvent.click(await screen.findByRole("button", { name: "Remover Esfera: federal" }));
    await userEvent.click(await screen.findByRole("button", { name: "Criar coleção dinâmica" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Nome sugerido" })).toBeInTheDocument();
    const post = calls(spy).find((c) => c.init?.method === "POST" && c.url.pathname.endsWith("/colecoes"));
    expect(JSON.parse(String(post?.init?.body))).toMatchObject({ tipo: "dinamica", regra_filtro: { tema: "saude,educacao" } });
  });

  it("some quando o LLM está desligado", async () => {
    mockApi({ "/colecoes": [], "/llm/estado": { habilitado: false, motivo: "desligado" } });
    renderAt(ui(), "/colecoes");
    expect(await screen.findByText("Nova coleção manual")).toBeInTheDocument();
    expect(screen.queryByLabelText("Descrição da coleção")).not.toBeInTheDocument();
  });
});
