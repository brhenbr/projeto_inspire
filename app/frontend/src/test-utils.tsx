import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

type Handler = unknown | ((url: URL, init?: RequestInit) => unknown);

/** Simula a API por prefixo de caminho (/api/v1/...). Devolve o espião para conferir as chamadas. */
export function mockApi(routes: Record<string, Handler>) {
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const path = url.pathname.replace("/api/v1", "");
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => path === k || path.startsWith(k + "/"));
    if (!key) return { ok: false, status: 404, json: async () => ({ detail: `sem mock para ${path}` }) };
    const h = routes[key];
    const body = typeof h === "function" ? (h as (u: URL, i?: RequestInit) => unknown)(url, init) : h;
    if (body instanceof Response) return body;
    return { ok: true, status: 200, json: async () => body };
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

export const renderAt = (ui: ReactElement, path = "/") =>
  render(<MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>);

export const calls = (spy: ReturnType<typeof mockApi>) =>
  spy.mock.calls.map(([u, init]) => ({
    url: new URL(String(u), "http://localhost"),
    init: init as RequestInit | undefined,
  }));
