import { expect, test, type Page } from "@playwright/test";

import { comoCurador } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

async function aguardarExecucaoConcluida(page: Page, tarefa: string) {
  await expect(page.getByRole("row").filter({ hasText: tarefa }).first().getByText("Concluída")).toBeVisible({ timeout: 60_000 });
}

async function filtrarPropostas(page: Page, rotulo: string) {
  await page.getByLabel("Filtrar propostas").selectOption({ label: rotulo });
}

test.describe("5. Curadoria assistida por LLM", () => {
  test("o modo simulado é anunciado de forma clara, na tela inteira", async ({ page }) => {
    await page.goto("/llm");

    await expect(page.getByText(/Modo simulado:/).first()).toBeVisible(); // faixa no topo
    await expect(page.getByText("Modo simulado (sem IA)")).toBeVisible();
    await expect(page.getByText(/Nenhum dado sai desta máquina/)).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0); // não há aviso de provedor externo
  });

  test("gerar sugestões para os primeiros da fila e acompanhar até concluir", async ({ page }) => {
    await page.goto("/llm");

    await page.getByLabel(/^Tarefa/).selectOption({ label: "Sugerir palavras-chave" });
    await page.getByLabel(/^Quantos conjuntos/).fill("4");
    await page.getByLabel(/^Instruções adicionais/).fill("foco em termos de busca");
    await page.getByRole("button", { name: "Gerar sugestões" }).click();

    await expect(page.getByText(/Execução #\d+ enfileirada para 4 conjunto/)).toBeVisible();
    await aguardarExecucaoConcluida(page, "sugerir-tags");
    await expect(page.getByRole("article", { name: /^Proposta/ }).first().getByText("Aguardando revisão")).toBeVisible();
    await expect(page.getByRole("article", { name: /^Proposta/ }).first()).toBeVisible();
  });

  test("aprovar, editar e rejeitar propostas; nada muda sem aprovação", async ({ page }) => {
    await page.goto("/llm");
    const propostas = page.getByRole("article", { name: /^Proposta/ });
    await expect(propostas.first()).toBeVisible();
    const pendentes = await propostas.count();
    expect(pendentes).toBeGreaterThanOrEqual(3);

    // 1) aprovar a primeira
    await propostas.nth(0).getByRole("button", { name: "Aprovar" }).click();
    await expect(propostas).toHaveCount(pendentes - 1);

    // 2) editar a próxima, com um valor do curador
    await propostas.nth(0).getByRole("button", { name: "Editar" }).click();
    await propostas.nth(0).getByLabel(/^Valor editado/).fill("tag-do-curador, outra-tag, terceira-tag");
    await propostas.nth(0).getByRole("button", { name: "Salvar edição e aplicar" }).click();
    await expect(propostas).toHaveCount(pendentes - 2);

    // 3) rejeitar a próxima
    await propostas.nth(0).getByRole("button", { name: "Rejeitar" }).click();
    await expect(propostas).toHaveCount(pendentes - 3);

    await filtrarPropostas(page, "Aprovadas");
    await expect(page.getByRole("article", { name: /^Proposta/ }).first().getByText("Aprovada", { exact: true })).toBeVisible();
    await filtrarPropostas(page, "Editadas");
    await expect(page.getByRole("article", { name: /^Proposta/ }).first()).toContainText("tag-do-curador");
    await filtrarPropostas(page, "Rejeitadas");
    await expect(page.getByRole("article", { name: /^Proposta/ }).first().getByText("Rejeitada", { exact: true })).toBeVisible();
  });

  test("o que foi aprovado aparece no histórico do conjunto com a origem LLM", async ({ page }) => {
    await page.goto("/llm");
    await filtrarPropostas(page, "Aprovadas");
    const card = page.getByRole("article", { name: /^Proposta/ }).first();
    await card.getByRole("link").first().click();

    await page.getByRole("tab", { name: "Histórico" }).click();
    await expect(page.getByText("LLM", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/Proposta de LLM #\d+ \(aprovada\)/)).toBeVisible();
  });

  test("do detalhe do conjunto: pedir uma sugestão e aprová-la ali mesmo", async ({ page }) => {
    await page.goto("/conjuntos/ds-0005");
    await page.getByRole("tab", { name: /Sugestões de LLM/ }).click();

    await page.getByLabel("Tarefa").selectOption({ label: "Melhorar a descrição" });
    await page.getByRole("button", { name: "Gerar sugestão" }).click();
    await expect(page.getByText(/Execução #\d+ enfileirada/)).toBeVisible();

    const proposta = page.getByRole("article", { name: /^Proposta/ }).first();
    await expect(proposta).toBeVisible({ timeout: 60_000 });
    await expect(proposta.getByText("Sugestão")).toBeVisible();
    await proposta.getByRole("button", { name: "Aprovar" }).click();

    await page.getByRole("tab", { name: "Metadados e curadoria" }).click();
    await expect(page.getByLabel(/^Descrição/)).toHaveValue(/Conjunto de dados publicado por Órgão/);
  });

  test("nada é aplicado sem aprovação: o conjunto de uma proposta pendente segue igual", async ({ page, request }) => {
    await page.goto("/conjuntos/ds-0007");
    const original = await page.getByLabel(/^Descrição/).inputValue();
    await page.getByRole("tab", { name: /Sugestões de LLM/ }).click();
    await page.getByLabel("Tarefa").selectOption({ label: "Melhorar a descrição" });
    await page.getByRole("button", { name: "Gerar sugestão" }).click();
    await expect(page.getByRole("article", { name: /^Proposta/ }).first()).toBeVisible({ timeout: 60_000 });

    const d = await (await request.get("/api/v1/conjuntos/ds-0007")).json();
    expect(d.efetivo.descricao ?? "").toBe(original);
    expect(d.alteracoes).toHaveLength(0);
    expect(d.propostas_pendentes).toBeGreaterThan(0);
  });
});
