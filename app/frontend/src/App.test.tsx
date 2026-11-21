import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { mockApi, renderAt } from "./test-utils";

const base = { habilitado: true, motivo: null, externo: false, simulado: false, provedor: "x", modelo: "m", limite_por_execucao: 200 };
const painelVazio = {
  totais: { conjuntos: 0 }, por_esfera: [], por_tema: [], por_formato: [], por_licenca: [], por_periodicidade: [],
  qualidade_faixas: [], por_estado_curadoria: [], ultima_extracao: null,
};

function setup(llm: unknown) {
  return mockApi({ "/llm/estado": llm, "/painel": painelVazio, "/extracoes/estado": { ativa: null } });
}

describe("App", () => {
  it("mostra o menu principal", async () => {
    setup({ ...base, habilitado: false });
    renderAt(<App />);

    for (const nome of ["Painel", "Buscar", "Fila de curadoria", "Coleções", "Organizações", "Sugestões de LLM", "Extração", "Configurações"]) {
      expect(screen.getByRole("link", { name: nome })).toBeInTheDocument();
    }
    expect(await screen.findByText("Nenhum dado ainda")).toBeInTheDocument();
  });

  it("avisa claramente quando o provedor de LLM é externo", async () => {
    setup({ ...base, externo: true, host: "api.exemplo.com" });
    renderAt(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Provedor de LLM externo ativo.*api\.exemplo\.com/);
  });

  it("avisa que o modo é simulado", async () => {
    setup({ ...base, simulado: true, provedor: "simulado" });
    renderAt(<App />);

    expect(await screen.findByText(/Modo simulado:/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("sem aviso quando o LLM está desligado", async () => {
    setup({ ...base, habilitado: false });
    renderAt(<App />);
    await screen.findByText("Nenhum dado ainda");

    expect(screen.queryByText(/Modo simulado/)).not.toBeInTheDocument();
    expect(screen.queryByText(/externo ativo/)).not.toBeInTheDocument();
  });

  it("rota desconhecida mostra página não encontrada", async () => {
    setup({ ...base, habilitado: false });
    renderAt(<App />, "/nao-existe");

    expect(await screen.findByText("Página não encontrada")).toBeInTheDocument();
  });

  it("erro de API no painel mostra alerta com botão de tentar de novo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: "falha interna" }) }));
    renderAt(<App />);

    expect(await screen.findByText("falha interna")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar de novo" })).toBeInTheDocument();
  });
});
