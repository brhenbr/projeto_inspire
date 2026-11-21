import { expect, test } from "@playwright/test";

import { aguardarExtracaoTerminar, aguardarTitulo, comoCurador, FAKE_PORTAL } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

const CURADO = "Saúde e População Brasileira (curado)";

test.describe("7. O portal muda: extração incremental, curadoria preservada", () => {
  test("a extração incremental busca só o que mudou", async ({ page, request }) => {
    // o "portal" altera dois conjuntos: um curado e aprovado (ds-saude) e outro comum
    await request.post(`${FAKE_PORTAL}/_teste/titulo/ds-saude`, { params: { titulo: "Título que o portal mudou depois" } });
    await request.post(`${FAKE_PORTAL}/_teste/titulo/ds-0010`, { params: { titulo: "Conjunto 10 com título novo no portal" } });

    await page.goto("/extracao");
    await page.getByLabel(/Forçar/).check(); // o intervalo mínimo ainda vale: forçar é a exceção registrada
    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Atualizar catálogo" }).click();
    await expect(page.getByText(/Extração #2 \(incremental\)/)).toBeVisible();
    await aguardarExtracaoTerminar(request);
    await aguardarTitulo(request, "ds-0010", "Conjunto 10 com título novo no portal");

    await page.reload();
    await page.getByRole("button", { name: "Relatório" }).first().click();
    const rel = page.getByLabel("Relatório da extração 2");
    await expect(rel).toContainText("2 alterados");
    await expect(rel).toContainText("0 novos");
    await expect(rel).toContainText("43 detalhes evitados"); // 46 - ds-saude - ds-0010 - o "sem detalhe", que é tentado de novo
    await expect(page.getByText("forçada")).toBeVisible();
  });

  test("conjunto sem curadoria passa a mostrar o novo valor do portal", async ({ page }) => {
    await page.goto("/conjuntos?q=" + encodeURIComponent("título novo no portal"));
    await expect(page.getByRole("link", { name: "Conjunto 10 com título novo no portal" })).toBeVisible();
  });

  test("conjunto curado: a curadoria prevalece e ele volta para revisão", async ({ page }) => {
    await page.goto("/conjuntos?q=" + encodeURIComponent("população brasileira curado"));
    await page.getByRole("link", { name: CURADO }).click();

    await expect(page.getByRole("heading", { level: 1, name: CURADO })).toBeVisible(); // continua o título curado
    await expect(page.locator(".cabeca-detalhe").getByText("Pendente")).toBeVisible(); // era "Aprovado"; mudou no portal
    await expect(page.getByText("No portal: Título que o portal mudou depois")).toBeVisible();

    await page.getByRole("tab", { name: "Histórico" }).click();
    await expect(page.getByRole("cell", { name: "alterado", exact: true })).toBeVisible();
  });

  test("as sugestões de LLM pendentes ficam desatualizadas e não podem ser aprovadas", async ({ page, request }) => {
    // ds-0007 tinha uma proposta pendente (cenário 5). Muda no portal e extrai de novo.
    await request.post(`${FAKE_PORTAL}/_teste/titulo/ds-0007`, { params: { titulo: "Conjunto 7 mudou no portal" } });
    await expect(async () => {
      const r = await request.post("/api/v1/extracoes", { data: { tipo: "incremental", forcar: true } });
      expect([200, 202]).toContain(r.status());
    }).toPass();
    await aguardarExtracaoTerminar(request);
    await aguardarTitulo(request, "ds-0007", "Conjunto 7 mudou no portal");

    const d = await (await request.get("/api/v1/conjuntos/ds-0007")).json();
    expect(d.propostas_pendentes).toBe(0);

    await page.goto("/llm");
    await page.getByLabel("Filtrar propostas").selectOption({ label: "Desatualizadas" });
    const card = page.getByRole("article", { name: /^Proposta/ }).filter({ hasText: "Conjunto 7 mudou no portal" });
    await expect(card.first()).toBeVisible();
    await expect(card.first().getByRole("button", { name: "Aprovar" })).toHaveCount(0);
  });
});
