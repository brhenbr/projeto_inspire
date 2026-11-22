import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

import { comoCurador } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

const CURADO = "Saúde e População Brasileira (curado)";

test.describe("9. DCAT-BR, chat e coleção por texto", () => {
  test("exportar uma busca em DCAT-BR traz o título curado, a qualidade em DQV e nenhum contato", async ({ page }) => {
    await page.goto("/conjuntos?q=" + encodeURIComponent("população brasileira curado"));
    await page.getByText(CURADO).first().waitFor();

    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Exportar DCAT-BR" }).click()]);

    expect(download.suggestedFilename()).toMatch(/\.jsonld$/);
    const texto = (await readFile((await download.path())!)).toString("utf-8");
    const doc = JSON.parse(texto) as { "@graph": Record<string, unknown>[] };
    expect(doc["@graph"][0]["@type"]).toBe("dcat:Catalog");
    const ds = doc["@graph"].find((n) => n["dct:identifier"] === "ds-saude")!;
    expect(ds["@type"]).toBe("dcat:Dataset");
    expect(ds["dct:title"]).toBe(CURADO); // o valor curado, não o do portal
    expect(ds["inspire:curado"]).toBe(true);
    expect(Array.isArray(ds["dcat:distribution"])).toBe(true);
    expect((ds["dqv:hasQualityMeasurement"] as unknown[]).length).toBeGreaterThan(1);
    expect(texto).not.toMatch(/contactPoint|vcard|@orgao-|Responsável \d/); // contatos são dados pessoais
  });

  test("perguntar em linguagem natural mostra como entendeu e traz resultados", async ({ page }) => {
    await page.goto("/perguntar");
    await expect(page.getByText(/Modo simulado/).first()).toBeVisible();

    await page.getByLabel("Sua pergunta").fill("quero dados de saúde da população brasileira");
    await page.getByRole("button", { name: "Perguntar" }).click();

    await expect(page.getByRole("heading", { name: "Como entendi" })).toBeVisible();
    await expect(page.getByLabel("Filtros entendidos")).toContainText(/Tema: saude|Palavras:/);
    await expect(page.getByRole("link", { name: CURADO })).toBeVisible();
    await expect(page.getByTestId("total-chat")).toContainText("conjunto(s)");
    await page.getByRole("link", { name: "Abrir na busca para refinar" }).click();
    await expect(page).toHaveURL(/\/conjuntos\?/);
    await expect(page.getByTestId("total")).toBeVisible();
  });

  test("criar coleção por texto: propõe, mostra amostra, nada é criado até confirmar", async ({ page, request }) => {
    const antes = ((await (await request.get("/api/v1/colecoes")).json()) as unknown[]).length;
    await page.goto("/colecoes");

    await page.getByLabel("Descrição da coleção").fill("dados de saúde da população");
    await page.getByRole("button", { name: "Propor filtros" }).click();
    await expect(page.getByTestId("total-proposta")).toBeVisible();
    expect(((await (await request.get("/api/v1/colecoes")).json()) as unknown[]).length).toBe(antes);

    await page.getByLabel("Nome da nova coleção").fill("Coleção por texto E2E");
    await page.getByRole("button", { name: "Criar coleção dinâmica" }).click();

    await expect(page.getByRole("heading", { name: "Coleção por texto E2E" })).toBeVisible();
    expect(((await (await request.get("/api/v1/colecoes")).json()) as unknown[]).length).toBe(antes + 1);
  });
});
