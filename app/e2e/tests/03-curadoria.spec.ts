import { expect, test } from "@playwright/test";

import { abrirConjunto, comoCurador, CURADOR, notaDoCabecalho } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

const ORIGINAL = "Saúde da População Brasileira";
const CURADO = "Saúde e População Brasileira (curado)";

test.describe("3. Curadoria humana", () => {
  test("editar metadados melhora a nota e fica registrado, sem alterar o dado do portal", async ({ page }) => {
    await abrirConjunto(page, ORIGINAL, ORIGINAL);
    const antes = await notaDoCabecalho(page);

    await page.getByLabel("Título", { exact: true }).fill(CURADO);
    await page.getByLabel(/^Palavras-chave/).fill("saúde, mortalidade, hospitais");
    await page.getByLabel("Licença").fill("cc-by");
    await page.getByLabel(/^Comentário/).fill("Padronização do projeto");
    await page.getByRole("button", { name: "Salvar alterações" }).click();

    await expect(page.getByText(/Salvo: Título, Palavras-chave, Licença/)).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: CURADO })).toBeVisible();
    await expect(page.locator(".cabeca-detalhe").getByText("Curado", { exact: true })).toBeVisible();
    await expect(page.locator(".cabeca-detalhe").getByText("Em revisão")).toBeVisible(); // a primeira edição abre a revisão
    await expect.poll(() => notaDoCabecalho(page)).toBeGreaterThan(antes);

    // o valor do portal continua visível ao lado
    await expect(page.getByText("No portal: " + ORIGINAL)).toBeVisible();
  });

  test("a versão curada aparece na busca; a original continua achável pelo conteúdo", async ({ page }) => {
    await page.goto("/conjuntos?q=" + encodeURIComponent("população brasileira curado"));
    await expect(page.getByRole("link", { name: CURADO })).toBeVisible();
    await expect(page.locator("article.resultado", { hasText: CURADO }).getByText("Curado", { exact: true })).toBeVisible();
  });

  test("reverter um campo devolve o valor do portal e preserva o histórico", async ({ page }) => {
    await abrirConjunto(page, "população brasileira curado", CURADO);
    const antes = await notaDoCabecalho(page);

    await page.getByRole("button", { name: "Reverter ao valor do portal" }).first().click(); // palavras-chave ou licença

    await expect(page.getByText(/voltou ao valor do portal/)).toBeVisible();
    await expect.poll(() => notaDoCabecalho(page)).toBeLessThan(antes);

    await page.getByRole("tab", { name: "Histórico" }).click();
    await expect(page.getByText("revertido ao valor do portal")).toBeVisible();
    await expect(page.getByRole("cell", { name: new RegExp(CURADOR) }).first()).toBeVisible();
  });

  test("status de curadoria: aprovar atualiza a etiqueta e a fila", async ({ page }) => {
    await abrirConjunto(page, "população brasileira curado", CURADO);

    await page.getByLabel("Status da curadoria").selectOption("aprovado");
    await page.getByRole("button", { name: "Salvar status" }).click();

    await expect(page.getByText("Status: Aprovado.")).toBeVisible();
    await expect(page.locator(".cabeca-detalhe").getByText("Aprovado", { exact: true })).toBeVisible();
  });

  test("duplicado exige um original existente", async ({ page }) => {
    await page.goto("/conjuntos/ds-0002");
    await page.getByLabel("Status da curadoria").selectOption("duplicado");
    await page.getByLabel("Identificador do conjunto original").fill("nao-existe");
    await page.getByRole("button", { name: "Salvar status" }).click();

    await expect(page.getByRole("alert")).toContainText("não existe");
  });

  test("validação: o título não pode ficar vazio", async ({ page }) => {
    await page.goto("/conjuntos/ds-0002");
    await page.getByLabel("Título", { exact: true }).fill("");
    await page.getByRole("button", { name: "Salvar alterações" }).click();

    await expect(page.getByRole("alert")).toContainText("título não pode ficar vazio");
  });

  test("a fila prioriza os piores e aceita ações em lote", async ({ page }) => {
    await page.goto("/curadoria");
    await expect(page.getByRole("heading", { name: /conjunto\(s\)/ })).toBeVisible();

    const prioridades = (await page.locator("tbody tr td.num").allTextContents()).map((t) => Number(t.replace(/\./g, "").replace(",", ".")));
    expect(prioridades.length).toBeGreaterThan(3);
    expect(prioridades).toEqual([...prioridades].sort((a, b) => b - a));

    await page.getByRole("checkbox", { name: /^Selecionar (?!todos)/ }).nth(0).check();
    await page.getByRole("checkbox", { name: /^Selecionar (?!todos)/ }).nth(1).check();
    await page.getByRole("button", { name: "Em revisão" }).click();

    await expect(page.getByText(/2 conjunto\(s\) marcado\(s\) como “Em revisão”/)).toBeVisible();
  });

  test("o histórico do conjunto mostra quem alterou, quando e com qual comentário", async ({ page }) => {
    await abrirConjunto(page, "população brasileira curado", CURADO);
    await page.getByRole("tab", { name: "Histórico" }).click();

    await expect(page.getByRole("heading", { name: "Alterações da curadoria" })).toBeVisible();
    await expect(page.getByText("Padronização do projeto")).toBeVisible();
    await expect(page.getByText("humano", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Mudanças vindas do portal" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "novo", exact: true })).toBeVisible();
  });
});
