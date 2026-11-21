import { expect, test } from "@playwright/test";

import { aguardarExtracaoTerminar, aguardarQualidade, comoCurador, painel } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

test.describe("1. Extração do catálogo", () => {
  test("o painel começa vazio e leva à extração", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Nenhum dado ainda")).toBeVisible();

    await page.getByRole("link", { name: "Ir para a extração" }).click();

    await expect(page).toHaveURL(/\/extracao$/);
    await expect(page.getByRole("button", { name: "Atualizar catálogo" })).toBeEnabled();
    await expect(page.getByText("Nenhuma extração ainda.")).toBeVisible();
  });

  test("extração completa pela tela, com relatório de conferência", async ({ page, request }) => {
    await page.goto("/extracao");

    await page.getByRole("button", { name: "Extração completa" }).click();

    await expect(page.getByText(/Extração #1 \(completa\)/)).toBeVisible();
    await aguardarExtracaoTerminar(request);
    await aguardarQualidade(request);

    await page.reload();
    // o portal falso tem 1 conjunto cujo detalhe devolve sempre 400: a extração termina com divergência, sem quebrar
    await expect(page.getByText("Concluída com divergências")).toBeVisible();
    await page.getByRole("button", { name: "Relatório" }).first().click();
    const relatorio = page.getByLabel("Relatório da extração 1");
    await expect(relatorio).toContainText("Listados 46 de 46 esperados");
    await expect(relatorio).toContainText("Cobertura 100.0%");
    await expect(relatorio).toContainText("46 novos");
    await expect(relatorio).toContainText("1 sem detalhe");
    await expect(relatorio).toContainText("0 erros");
  });

  test("o painel mostra os totais da extração", async ({ page, request }) => {
    await page.goto("/");

    await expect(page.locator(".kpi", { hasText: "Conjuntos de dados" })).toContainText("46");
    await expect(page.locator(".kpi", { hasText: "Organizações" })).toContainText("3");
    await expect(page.locator(".kpi", { hasText: "Sem detalhe no portal" })).toContainText("1");
    await expect(page.locator(".kpi", { hasText: "Nota média" })).not.toContainText("—");
    await expect(page.getByRole("heading", { name: "Distribuição da qualidade" })).toBeVisible();
    await expect(page.getByText("Concluída com divergências (completa)")).toBeVisible();

    const p = await painel(request);
    expect(p.totais.conjuntos).toBe(46);
    expect(p.por_esfera[0].valor).toBe("federal");
  });
});
