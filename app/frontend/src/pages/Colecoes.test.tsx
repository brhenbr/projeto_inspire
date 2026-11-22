import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { calls, mockApi, renderAt } from "../test-utils";
import { ColecaoPage, ColecoesPage } from "./Colecoes";

const proposta = {
  nome_sugerido: "Bases sociais de saúde",
  filtros: { tema: "saude", esfera: "federal" },
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
const base = { "/colecoes": [], "/llm/estado": { habilitado: true, externo: true, simulado: false, host: "api.groq.com", limite_por_execucao: 50 } };

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

    await userEvent.click(screen.getByRole("button", { name: "Remover filtro Esfera" }));
    expect(await screen.findByText("Outro conjunto")).toBeInTheDocument();
    expect(screen.getByTestId("total-proposta")).toHaveTextContent("30 conjunto(s)");
    const busca = calls(spy).filter((c) => c.url.pathname.endsWith("/conjuntos")).at(-1);
    expect(busca?.url.searchParams.get("tema")).toBe("saude");
    expect(busca?.url.searchParams.has("esfera")).toBe(false);
  });

  it("criar envia a coleção dinâmica com os filtros ajustados", async () => {
    const spy = mockApi({
      ...base,
      "/chat/colecao": proposta,
      "/colecoes/9": { id: 9, nome: "x", tipo: "dinamica", conjuntos: 7 },
    });
    // POST /colecoes devolve a coleção criada; o mock por prefixo atende também GET /colecoes
    mockApi({ ...base, "/chat/colecao": proposta, "/colecoes": (_u: URL, init?: RequestInit) => (init?.method === "POST" ? { id: 9, nome: "x", tipo: "dinamica", conjuntos: 7 } : []), "/colecoes/9": { id: 9, nome: "x", tipo: "dinamica", conjuntos: 7, regra_filtro: {} } });
    void spy;
    renderAt(ui(), "/colecoes");
    await userEvent.type(await screen.findByLabelText("Descrição da coleção"), "bases sociais de saúde");
    await userEvent.click(screen.getByRole("button", { name: "Propor filtros" }));
    await userEvent.click(await screen.findByRole("button", { name: "Criar coleção dinâmica" }));

    expect(await screen.findByRole("heading", { name: /x/ })).toBeInTheDocument(); // navegou para a coleção criada
  });

  it("some quando o LLM está desligado", async () => {
    mockApi({ "/colecoes": [], "/llm/estado": { habilitado: false, motivo: "desligado" } });
    renderAt(ui(), "/colecoes");
    expect(await screen.findByText("Nova coleção manual")).toBeInTheDocument();
    expect(screen.queryByLabelText("Descrição da coleção")).not.toBeInTheDocument();
  });
});
