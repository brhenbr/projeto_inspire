import { expect, test } from "@playwright/test";

import { comoCurador, painel } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

test.describe("6. Regras de qualidade configuráveis", () => {
  test("a matriz de regras mostra dimensão, fonte e peso", async ({ page }) => {
    await page.goto("/configuracoes");

    for (const dim of ["Completude", "Atualidade", "Acessibilidade", "Processabilidade", "Conformidade"]) {
      await expect(page.getByRole("heading", { name: dim, exact: true })).toBeVisible();
    }
    await expect(page.getByRole("cell", { name: /FAIR A1/ }).first()).toBeVisible();
    await expect(page.getByLabel("Peso de Descrição adequada")).toHaveValue("3");
  });

  test("desativar uma regra e recalcular muda as notas; reativar restaura", async ({ page, request }) => {
    const antes = (await painel(request)).totais.nota_media;

    await page.goto("/configuracoes");
    await page.getByLabel("Ativar Descrição adequada").uncheck();
    await page.getByLabel("Peso de Licença informada").fill("5");
    await page.getByRole("button", { name: "Salvar alterações" }).click();
    await expect(page.getByText(/Regras salvas/)).toBeVisible();
    await page.getByRole("button", { name: "Recalcular notas" }).click();

    await expect.poll(async () => (await painel(request)).totais.nota_media, { timeout: 60_000 }).not.toBe(antes);
    await expect(page.getByText(/Último recálculo/)).toBeVisible();

    // restaura
    await page.reload();
    await page.getByLabel("Ativar Descrição adequada").check();
    await page.getByLabel("Peso de Licença informada").fill("2");
    await page.getByRole("button", { name: "Salvar alterações" }).click();
    await expect(page.getByText(/Regras salvas/)).toBeVisible();
    await page.getByRole("button", { name: "Recalcular notas" }).click();
    await expect.poll(async () => (await painel(request)).totais.nota_media, { timeout: 60_000 }).toBe(antes);
  });

  test("peso inválido é recusado pela API e mostrado ao usuário", async ({ page }) => {
    await page.goto("/configuracoes");
    await page.getByLabel("Peso de Título descritivo").fill("99");
    await page.getByRole("button", { name: "Salvar alterações" }).click();

    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("a tela informa a versão, o estado do banco e do LLM", async ({ page }) => {
    await page.goto("/configuracoes");

    await expect(page.getByText(/API: funcionando/)).toBeVisible();
    await expect(page.getByText(/Banco: funcionando/)).toBeVisible();
    await expect(page.getByText(/LLM: modo simulado/)).toBeVisible();
    await expect(page.getByText(/Dados pessoais de contato dos responsáveis/)).toBeVisible();
  });
});
