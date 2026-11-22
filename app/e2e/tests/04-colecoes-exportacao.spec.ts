import { expect, test, type Download } from "@playwright/test";
import { readFile } from "node:fs/promises";

import { comoCurador } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

const CURADO = "Saúde e População Brasileira (curado)";

async function conteudo(d: Download): Promise<Buffer> {
  const caminho = await d.path();
  return readFile(caminho);
}

test.describe("4. Coleções e exportação", () => {
  test("criar uma coleção manual e preenchê-la a partir de uma busca", async ({ page }) => {
    await page.goto("/colecoes");
    await expect(page.getByText("Nenhuma coleção ainda.")).toBeVisible();

    await page.getByLabel("Nome", { exact: true }).fill("Bases sociais");
    await page.getByLabel("Descrição (opcional)").fill("Saúde, assistência e educação");
    await page.getByRole("button", { name: "Criar coleção", exact: true }).click();
    await expect(page.getByRole("link", { name: "Bases sociais" })).toBeVisible();

    await page.goto("/conjuntos?organizacao=orgao-1");
    await page.getByLabel("Coleção de destino").selectOption({ label: "Bases sociais" });
    await page.getByRole("button", { name: "Adicionar", exact: true }).click();
    await expect(page.getByText("16 conjunto(s) adicionado(s) à coleção.")).toBeVisible();

    await page.goto("/colecoes");
    await page.getByRole("link", { name: "Bases sociais" }).click();
    await expect(page.getByText("16 conjunto(s)").first()).toBeVisible();
  });

  test("não permite duas coleções com o mesmo nome", async ({ page }) => {
    await page.goto("/colecoes");
    await page.getByLabel("Nome", { exact: true }).fill("Bases sociais");
    await page.getByRole("button", { name: "Criar coleção", exact: true }).click();

    await expect(page.getByRole("alert")).toContainText("Já existe uma coleção");
  });

  test("exportar a coleção em CSV: BOM, cabeçalho e uma linha por conjunto", async ({ page }) => {
    await page.goto("/colecoes");
    await page.getByRole("link", { name: "Bases sociais" }).click();

    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Exportar CSV" }).click()]);

    expect(download.suggestedFilename()).toMatch(/^colecao-\d+-\d{8}\.csv$/);
    const bytes = await conteudo(download);
    expect([...bytes.subarray(0, 3)]).toEqual([0xef, 0xbb, 0xbf]); // BOM: o Excel abre com acentos corretos
    const linhas = bytes.toString("utf-8").trim().split(/\r\n/);
    expect(linhas[0]).toContain("id,titulo,titulo_original,descricao");
    expect(linhas).toHaveLength(17); // cabeçalho + 16
    expect(bytes.toString("utf-8")).toContain(CURADO);
  });

  test("exportar uma busca em JSON traz original, curado e status", async ({ page }) => {
    await page.goto("/conjuntos?q=" + encodeURIComponent("população brasileira curado"));
    await page.getByText(CURADO).first().waitFor();

    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Exportar JSON" }).click()]);

    const dados = JSON.parse((await conteudo(download)).toString("utf-8")) as Record<string, unknown>[];
    const item = dados.find((d) => d.id === "ds-saude")!;
    expect(item.titulo).toBe(CURADO);
    expect(item.titulo_original).toBe("Saúde da População Brasileira");
    expect(item.curado).toBe(true);
    expect(item.estado_curadoria).toBe("aprovado");
    expect(Array.isArray(item.tags)).toBe(true);
    expect(JSON.stringify(dados)).not.toMatch(/@orgao-|Responsável \d/);
  });

  test("salvar uma busca como coleção dinâmica", async ({ page }) => {
    await page.goto("/conjuntos?tema=saude");
    const total = (await page.getByTestId("total").textContent())!.match(/\d+/)![0];

    await page.getByLabel("Nome da coleção dinâmica").fill("Tema saúde");
    await page.getByRole("button", { name: "Salvar", exact: true }).click();
    await expect(page.getByText(new RegExp(`Coleção dinâmica “Tema saúde” criada com ${total} conjunto`))).toBeVisible();

    await page.goto("/colecoes");
    await expect(page.getByRole("row", { name: /Tema saúde/ })).toContainText("Dinâmica");
    await page.getByRole("link", { name: "Tema saúde" }).click();
    await expect(page.getByRole("heading", { name: "Regra (filtros salvos)" })).toBeVisible();
    await expect(page.getByText("tema: saude")).toBeVisible();
  });

  test("coleção dinâmica aceita exceções: excluir um conjunto da regra", async ({ page }) => {
    await page.goto("/colecoes");
    await page.getByRole("link", { name: "Tema saúde" }).click();
    const antes = Number((await page.getByText(/^\d+ conjunto\(s\)$/).first().textContent())!.match(/\d+/)![0]);

    await page.getByRole("button", { name: "Excluir da coleção" }).first().click();

    await expect(page.getByText(`${antes - 1} conjunto(s)`).first()).toBeVisible();
  });

  test("renomear e apagar uma coleção (com confirmação) sem apagar os conjuntos", async ({ page }) => {
    await page.goto("/colecoes");
    await page.getByLabel("Nome", { exact: true }).fill("Temporária");
    await page.getByRole("button", { name: "Criar coleção", exact: true }).click();
    await page.getByRole("link", { name: "Temporária" }).click();

    await page.getByLabel("Novo nome").fill("Temporária renomeada");
    await page.getByRole("button", { name: "Salvar nome" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Temporária renomeada" })).toBeVisible();

    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Apagar coleção" }).click();
    await expect(page).toHaveURL(/\/colecoes$/);
    await expect(page.getByRole("link", { name: "Temporária renomeada" })).toHaveCount(0);

    await page.goto("/conjuntos");
    await expect(page.getByTestId("total")).toContainText("46 conjunto(s)");
  });
});
