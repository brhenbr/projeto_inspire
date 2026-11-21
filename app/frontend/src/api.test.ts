import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, qs, setCurator } from "./api";

const reply = (status: number, body: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("qs", () => {
  it("ignora valores vazios e monta a consulta", () => {
    expect(qs({ q: "saúde", vazio: "", nulo: null, indef: undefined, n: 0, f: false })).toBe("?q=sa%C3%BAde&n=0&f=false");
    expect(qs()).toBe("");
  });
});

describe("api", () => {
  it("envia o nome do curador no cabeçalho", async () => {
    const f = vi.fn().mockResolvedValue(reply(200, { ok: 1 }));
    vi.stubGlobal("fetch", f);
    setCurator("  Ana  ");
    await api.get("/x");
    expect((f.mock.calls[0][1] as RequestInit).headers).toMatchObject({ "X-Curador": "Ana" });
  });

  it("envia JSON no corpo", async () => {
    const f = vi.fn().mockResolvedValue(reply(200, {}));
    vi.stubGlobal("fetch", f);
    await api.patch("/x", { campos: { titulo: "t" } });
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({ campos: { titulo: "t" } });
  });

  it("traduz erros da API para mensagens legíveis", async () => {
    const cases: [number, unknown, string][] = [
      [404, { detail: "Conjunto não encontrado" }, "Conjunto não encontrado"],
      [422, { detail: [{ loc: ["body", "campos"], msg: "campo obrigatório" }] }, "campos: campo obrigatório"],
      [429, { motivo: "Intervalo mínimo desde a última extração", disponivel_em: "2026-01-01T00:00:00Z" }, "Intervalo mínimo desde a última extração"],
      [500, null, "Erro 500"],
    ];
    for (const [status, body, msg] of cases) {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(status, body)));
      await expect(api.get("/x")).rejects.toMatchObject({ status, detail: msg });
    }
  });

  it("guarda os dados do erro (ex.: horário de liberação do 429)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(429, { motivo: "m", disponivel_em: "x" })));
    const err = await api.post("/extracoes").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).data).toEqual({ motivo: "m", disponivel_em: "x" });
  });

  it("204 não tem corpo", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 204, json: async () => { throw new Error("sem corpo"); } }),
    );
    await expect(api.del("/colecoes/1")).resolves.toBeUndefined();
  });

  it("503 do /saude devolve o corpo em vez de falhar", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(503, { status: "degradado", banco: "indisponivel" })));
    await expect(api.get("/saude")).resolves.toMatchObject({ status: "degradado" });
  });

  it("monta endereços de download", () => {
    expect(api.url("/exportacao/conjuntos", { saida: "csv", q: "a b" })).toBe("/api/v1/exportacao/conjuntos?saida=csv&q=a+b");
  });
});
