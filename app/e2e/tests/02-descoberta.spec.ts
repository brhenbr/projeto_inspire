import { expect, test } from "@playwright/test";

import { comoCurador, numeroDaNota } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

const TITULO = "Saúde da População Brasileira";

test.describe("2. Descoberta (busca, filtros, detalhe)", () => {
  test("a busca ignora acentos, maiúsculas e plural", async ({ page }) => {
    for (const q of ["saúde população", "saude populacao", "SAÚDE DA POPULAÇÃO", "populações"]) {
      await page.goto(`/conjuntos?q=${encodeURIComponent(q)}`);
      await expect(page.getByRole("link", { name: TITULO }).first(), `busca: ${q}`).toBeVisible();
    }
  });

  test("a busca acha pelo conteúdo da descrição e tolera erro de digitação", async ({ page }) => {
    await page.goto("/conjuntos?q=mortalidade hospitalares");
    await expect(page.getByRole("link", { name: TITULO })).toBeVisible();
    await expect(page.getByTestId("total")).toContainText("1 conjunto(s)");

    await page.goto("/conjuntos?q=Saude da Populacoa Brasileria");
    await expect(page.getByText(/Nenhum resultado exato/)).toBeVisible();
    await expect(page.getByRole("link", { name: TITULO })).toBeVisible();
  });

  test("busca sem resultado explica o que fazer", async ({ page }) => {
    await page.goto("/conjuntos?q=xyzzyqwerty");
    await expect(page.getByText(/Nada encontrado/)).toBeVisible();
    await expect(page.getByTestId("total")).toContainText("0 conjunto(s)");
  });

  test("a faceta de organização filtra e o filtro ativo pode ser removido", async ({ page }) => {
    await page.goto("/conjuntos");
    await expect(page.getByTestId("total")).toContainText("46 conjunto(s)");

    await page.getByLabel("Filtros").getByRole("button", { name: /Órgão orgao-1/ }).click();

    await expect(page).toHaveURL(/organizacao=orgao-1/);
    await expect(page.getByTestId("total")).toContainText("16 conjunto(s)");

    await page.getByRole("button", { name: /organizacao: orgao-1/ }).click();
    await expect(page.getByTestId("total")).toContainText("46 conjunto(s)");
  });

  test("filtros combinam e a página é compartilhável por link", async ({ page }) => {
    await page.goto("/conjuntos?organizacao=orgao-1&formato=CSV&tema=saude");
    const total = Number((await page.getByTestId("total").textContent())?.match(/\d+/)?.[0]);
    expect(total).toBeGreaterThan(0);
    expect(total).toBeLessThan(16);
    await expect(page.getByRole("button", { name: /formato: CSV/ })).toBeVisible();
  });

  test("ordena por nota", async ({ page }) => {
    await page.goto("/conjuntos");
    await page.getByLabel("Ordenar por").selectOption({ label: "Maior nota" });
    await expect(page).toHaveURL(/ordem=nota/);

    const notas = await page.locator("article.resultado .badge", { hasText: /^Nota/ }).allTextContents();
    const valores = notas.map(numeroDaNota);
    expect(valores.length).toBeGreaterThan(5);
    expect(valores).toEqual([...valores].sort((a, b) => b - a));
  });

  test("a paginação navega entre páginas sem repetir resultados", async ({ page }) => {
    await page.goto("/conjuntos?ordem=titulo");
    await expect(page.locator("article.resultado").first()).toBeVisible();
    const primeira = await page.locator("article.resultado h3").allTextContents();
    expect(primeira.length).toBe(20);

    await page.getByRole("button", { name: "Próxima →" }).click();
    await expect(page).toHaveURL(/pagina=2/);
    await expect(page.locator("article.resultado h3").first()).not.toHaveText(primeira[0]);
    const segunda = await page.locator("article.resultado h3").allTextContents();
    expect(segunda.filter((t) => primeira.includes(t))).toEqual([]);
  });

  test("o detalhe mostra qualidade explicada e recursos com link para o órgão", async ({ page }) => {
    await page.goto(`/conjuntos?q=${encodeURIComponent(TITULO)}`);
    await page.getByRole("link", { name: TITULO }).first().click();

    await expect(page.getByRole("heading", { level: 1, name: TITULO })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ver no portal ↗" })).toHaveAttribute("href", /dados\.gov\.br\/dados\/conjuntos-dados\/conjunto-ds-saude/);

    await page.getByRole("tab", { name: "Qualidade" }).click();
    await expect(page.getByRole("heading", { name: "Verificações" })).toBeVisible();
    await expect(page.getByLabel("Passou").first()).toBeVisible();
    await expect(page.getByLabel("Falhou").first()).toBeVisible(); // tem falhas explicadas (ex.: palavras-chave, licença)
    await expect(page.getByText(/palavra\(s\)-chave \(mínimo 3\)/)).toBeVisible();

    await page.getByRole("tab", { name: "Recursos (2)" }).click();
    const links = page.getByRole("link", { name: "Abrir ↗" });
    await expect(links).toHaveCount(2);
    await expect(links.first()).toHaveAttribute("href", /orgao-1\.gov\.br/);
    await expect(links.first()).toHaveAttribute("rel", /noreferrer/);
  });

  test("conjunto sem detalhe no portal é sinalizado e não tem nota", async ({ page }) => {
    await page.goto("/conjuntos?sem_detalhe=true");
    await expect(page.getByTestId("total")).toContainText("1 conjunto(s)");
    await expect(page.getByText("Sem detalhe", { exact: true })).toBeVisible();
    await expect(page.getByText("sem nota")).toBeVisible();

    await page.locator("article.resultado h3 a").first().click();
    await expect(page.getByText(/O portal não entrega o detalhe/)).toBeVisible();
  });

  test("organizações: lista, ordenação e detalhe com o que mais precisa melhorar", async ({ page }) => {
    await page.goto("/organizacoes");
    await expect(page.getByRole("row")).toHaveCount(4); // cabeçalho + 3

    await page.getByRole("link", { name: "Órgão orgao-1" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Órgão orgao-1" })).toBeVisible();
    await expect(page.locator(".kpi", { hasText: "Conjuntos coletados" })).toContainText("16");
    await expect(page.getByRole("heading", { name: "O que mais precisa melhorar" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Qualidade por dimensão" })).toBeVisible();

    await page.getByRole("link", { name: "Ver os conjuntos" }).click();
    await expect(page).toHaveURL(/organizacao=orgao-1/);
  });

  test("nenhuma tela exibe contatos pessoais dos responsáveis", async ({ page, request }) => {
    for (const rota of ["/conjuntos?ordem=titulo", "/conjuntos/ds-0001", "/organizacoes/orgao-1", "/"]) {
      await page.goto(rota);
      await page.waitForLoadState("networkidle");
      const texto = await page.locator("body").innerText();
      expect(texto, rota).not.toMatch(/@orgao-\d/);
      expect(texto, rota).not.toMatch(/Responsável \d/);
    }
    const detalhe = await (await request.get("/api/v1/conjuntos/ds-0001")).text();
    expect(detalhe).not.toMatch(/@orgao-|emailResponsavel|Responsável \d/);
  });
});
