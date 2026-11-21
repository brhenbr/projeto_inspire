import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function mockFetch(body: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("mostra o estado do sistema quando a API responde", async () => {
    mockFetch({ status: "ok", banco: "ok", versao: "0.1.0" });
    render(<App />);

    expect(await screen.findByText(/API: funcionando/)).toBeInTheDocument();
    expect(screen.getByText(/Banco de dados: funcionando/)).toBeInTheDocument();
    expect(screen.getByText(/Versão: 0.1.0/)).toBeInTheDocument();
  });

  it("avisa quando o banco está indisponível", async () => {
    mockFetch({ status: "degradado", banco: "indisponivel", versao: "0.1.0" }, 503);
    render(<App />);

    expect(await screen.findByText(/Banco de dados: indisponível/)).toBeInTheDocument();
  });

  it("mostra um alerta quando a API não responde", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("rede fora")));
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível falar com a API");
  });
});
