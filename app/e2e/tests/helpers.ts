import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const FAKE_PORTAL = process.env.FAKE_PORTAL ?? "http://fake-portal:9000";
export const CURADOR = "QA E2E";

/** Cada teste abre um contexto novo; o nome do curador precisa ser definido antes de a página carregar. */
export async function comoCurador(page: Page, nome = CURADOR): Promise<void> {
  await page.addInitScript((n) => localStorage.setItem("inspire.curador", n), nome);
}

export async function aguardarExtracaoTerminar(request: APIRequestContext): Promise<void> {
  await expect
    .poll(async () => (await (await request.get("/api/v1/extracoes/estado")).json()).ativa, {
      message: "a extração deveria terminar",
      timeout: 120_000,
      intervals: [1000],
    })
    .toBeNull();
}

/** O worker recalcula a qualidade logo depois de a extração terminar; espera a nota média aparecer. */
export async function aguardarQualidade(request: APIRequestContext): Promise<void> {
  await expect
    .poll(async () => (await (await request.get("/api/v1/painel")).json()).totais.nota_media, {
      message: "a nota média deveria ser calculada",
      timeout: 60_000,
      intervals: [1000],
    })
    .not.toBeNull();
}

export async function painel(request: APIRequestContext) {
  return (await request.get("/api/v1/painel")).json();
}

export function numeroDaNota(texto: string | null): number {
  const m = /Nota\s+([\d.,]+)/.exec(texto ?? "");
  if (!m) throw new Error(`sem nota em: ${texto}`);
  return Number(m[1].replace(/\./g, "").replace(",", "."));
}

export async function notaDoCabecalho(page: Page): Promise<number> {
  return numeroDaNota(await page.locator(".cabeca-detalhe .badge", { hasText: /^Nota|sem nota/ }).first().textContent());
}

export async function abrirConjunto(page: Page, busca: string, titulo: string): Promise<void> {
  await page.goto(`/conjuntos?q=${encodeURIComponent(busca)}`);
  await page.getByRole("link", { name: titulo }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

export async function idDoConjuntoAberto(page: Page): Promise<string> {
  return new URL(page.url()).pathname.split("/").pop() ?? "";
}
