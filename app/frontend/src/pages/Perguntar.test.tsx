import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { calls, mockApi, renderAt } from "../test-utils";
import PerguntarPage from "./Perguntar";

const estado = (over = {}) => ({ habilitado: true, motivo: null, externo: false, simulado: true, provedor: "simulado", modelo: "m", limite_por_execucao: 50, ...over });
const resposta = {
  pergunta: "saúde em CSV",
  filtros_removidos: ["esfera", "periodicidade"],
  filtros: { tema: "saude", formato: "CSV", organizacao: "ipea" },
  explicacao: "Entendi: saúde em CSV.",
  ignorados: ["uf: “XX” não existe no catálogo"],
  organizacao: { slug: "ipea", titulo: "Instituto de Pesquisa Econômica Aplicada" },
  provedor: { nome: "groq", modelo: "m", externo: true, simulado: false },
  resultado: {
    total: 1, pagina: 1, tamanho: 10, aproximada: false,
    itens: [{ id: "a", titulo: "Saúde da população", organizacao_titulo: "IPEA", formatos: ["CSV"], nota_qualidade: 80 }],
  },
};
const ui = () => <Routes><Route path="/perguntar" element={<PerguntarPage />} /></Routes>;

describe("Perguntar", () => {
  it("envia o pedido, mostra os filtros entendidos, o que foi ignorado e o link para refinar", async () => {
    const spy = mockApi({ "/llm/estado": estado({ externo: true, simulado: false, host: "api.groq.com" }), "/chat/perguntar": resposta });
    renderAt(ui(), "/perguntar");
    expect(await screen.findByText(/api\.groq\.com/)).toBeInTheDocument(); // aviso de provedor externo

    await userEvent.type(screen.getByLabelText("Sua pergunta"), "saúde em CSV");
    await userEvent.click(screen.getByRole("button", { name: "Perguntar" }));

    expect(await screen.findByText("Tema: saude")).toBeInTheDocument();
    expect(screen.getByText("Órgão: Instituto de Pesquisa Econômica Aplicada")).toBeInTheDocument();
    expect(screen.getByText(/não existe no catálogo/)).toBeInTheDocument();
    expect(screen.getByTestId("relaxados")).toHaveTextContent("Esfera, Periodicidade");
    expect(screen.getByTestId("total-chat")).toHaveTextContent("1 conjunto(s)");
    const link = screen.getByRole("link", { name: "Abrir na busca para refinar" });
    expect(link.getAttribute("href")).toBe("/conjuntos?tema=saude&formato=CSV&organizacao=ipea");
    const post = calls(spy).find((c) => c.init?.method === "POST");
    expect(JSON.parse(String(post?.init?.body))).toEqual({ pergunta: "saúde em CSV" });
  });

  it("com o recurso desligado não deixa perguntar", async () => {
    mockApi({ "/llm/estado": { habilitado: false, motivo: "O recurso de LLM está desligado" } });
    renderAt(ui(), "/perguntar");

    expect(await screen.findByText("O recurso de LLM está desligado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Perguntar" })).toBeDisabled();
  });

  it("mostra o erro da API sem quebrar a tela", async () => {
    mockApi({
      "/llm/estado": estado(),
      "/chat/perguntar": new Response(JSON.stringify({ detail: "Não consegui entender a resposta do modelo" }), { status: 502 }),
    });
    renderAt(ui(), "/perguntar");
    await userEvent.type(await screen.findByLabelText("Sua pergunta"), "algo");
    await userEvent.click(screen.getByRole("button", { name: "Perguntar" }));

    expect(await screen.findByText(/Não consegui entender/)).toBeInTheDocument();
  });
});
