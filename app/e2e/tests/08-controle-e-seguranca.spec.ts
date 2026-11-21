import { expect, test } from "@playwright/test";

import { aguardarExtracaoTerminar, comoCurador } from "./helpers";

test.beforeEach(async ({ page }) => comoCurador(page));

test.describe("8. Controle de pedidos de extração e segurança", () => {
  test("a tela desabilita o botão dentro do intervalo e diz o motivo e quando libera", async ({ page, request }) => {
    await aguardarExtracaoTerminar(request);
    await page.goto("/extracao");

    await expect(page.getByRole("button", { name: "Atualizar catálogo" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Extração completa" })).toBeDisabled();
    await expect(page.getByText(/Atualização incremental indisponível agora: Intervalo mínimo/)).toBeVisible();
    await expect(page.getByText(/Disponível às/).first()).toBeVisible();
  });

  test("a API recusa o pedido dentro do intervalo (429) com o horário de liberação", async ({ request }) => {
    const r = await request.post("/api/v1/extracoes", { data: { tipo: "incremental" } });

    expect(r.status()).toBe(429);
    const corpo = await r.json();
    expect(corpo.motivo).toMatch(/Intervalo mínimo/);
    expect(new Date(corpo.disponivel_em).getTime()).toBeGreaterThan(Date.now());
  });

  test("cliques repetidos e simultâneos criam uma única extração", async ({ request }) => {
    const respostas = await Promise.all(
      Array.from({ length: 6 }, () => request.post("/api/v1/extracoes", { data: { tipo: "incremental", forcar: true } })),
    );
    const status = respostas.map((r) => r.status()).sort();
    const ids = new Set((await Promise.all(respostas.map((r) => r.json()))).map((c) => c.id));

    expect(ids.size).toBe(1); // todos devolvem a MESMA execução
    expect(status.filter((s) => s === 202)).toHaveLength(1); // só um criou
    expect(status.filter((s) => s === 200)).toHaveLength(5); // os outros receberam a existente
    await aguardarExtracaoTerminar(request);

    const lista = await (await request.get("/api/v1/extracoes?limite=50")).json();
    const execucoesComEsseId = lista.filter((e: { id: number }) => ids.has(e.id));
    expect(execucoesComEsseId).toHaveLength(1);
  });

  test("não é possível forçar uma segunda extração enquanto há uma ativa", async ({ request }) => {
    const primeira = await request.post("/api/v1/extracoes", { data: { tipo: "completa", forcar: true } });
    expect([200, 202]).toContain(primeira.status());
    const segunda = await request.post("/api/v1/extracoes", { data: { tipo: "incremental", forcar: true } });

    // se a primeira ainda roda, devolve-se a mesma; se já terminou, a segunda é nova. Nunca duas ativas.
    const estado = await (await request.get("/api/v1/extracoes/estado")).json();
    const ativas = (await (await request.get("/api/v1/extracoes?limite=10")).json()).filter(
      (e: { estado: string }) => ["enfileirada", "em_andamento", "pausada"].includes(e.estado),
    );
    expect(ativas.length).toBeLessThanOrEqual(1);
    expect([200, 202]).toContain(segunda.status());
    expect(estado).toHaveProperty("incremental");
    await aguardarExtracaoTerminar(request);
  });

  test("cancelar uma extração e conferir o estado final na tela", async ({ page, request }) => {
    const r = await request.post("/api/v1/extracoes", { data: { tipo: "completa", forcar: true } });
    const { id } = await r.json();
    const c = await request.post(`/api/v1/extracoes/${id}/cancelar`);
    // o portal falso é muito rápido: a extração pode já ter terminado (409) ou ser cancelada
    expect([200, 409]).toContain(c.status());
    await aguardarExtracaoTerminar(request);

    await page.goto("/extracao");
    await expect(page.getByRole("row").filter({ hasText: new RegExp(`^${id}\\b`) }).first()).toBeVisible();
  });

  test("segurança: cabeçalhos do servidor web e documentação da API", async ({ request }) => {
    const r = await request.get("/");
    expect(r.headers()["x-content-type-options"]).toBe("nosniff");
    expect(r.headers()["x-frame-options"]).toBe("DENY");
    expect(r.headers()["referrer-policy"]).toBe("no-referrer");

    expect((await request.get("/api/docs")).status()).toBe(200);
    const spec = await (await request.get("/api/openapi.json")).json();
    expect(Object.keys(spec.paths)).toEqual(
      expect.arrayContaining(["/v1/extracoes", "/v1/conjuntos", "/v1/llm/execucoes", "/v1/exportacao/conjuntos", "/v1/qualidade/regras"]),
    );
    expect(spec.info.title).toBe("Inspire Catálogo");
  });

  test("segurança: a chave do portal e os contatos pessoais não vazam pela API", async ({ request }) => {
    const textos: string[] = [];
    for (const rota of [
      "/api/v1/conjuntos?tamanho=100",
      "/api/v1/conjuntos/ds-0001",
      "/api/v1/organizacoes",
      "/api/v1/extracoes",
      "/api/v1/llm/estado",
      "/api/v1/llm/propostas?tamanho=100",
      "/api/v1/exportacao/conjuntos",
    ]) {
      textos.push(await (await request.get(rota)).text());
    }
    const tudo = textos.join("\n");
    expect(tudo).not.toContain("chave-de-teste");
    expect(tudo).not.toMatch(/@orgao-\d|emailResponsavel|Responsável \d/);
  });

  test("a API recusa entradas inválidas com mensagens claras", async ({ request }) => {
    expect((await request.get("/api/v1/conjuntos?ordem=aleatoria")).status()).toBe(422);
    expect((await request.get("/api/v1/conjuntos/nao-existe")).status()).toBe(404);
    expect((await request.post("/api/v1/extracoes", { data: { tipo: "xyz" } })).status()).toBe(422);
    expect((await request.patch("/api/v1/conjuntos/ds-0001/curadoria", { data: { campos: { slug: "x" } } })).status()).toBe(422);
    expect((await request.get("/api/v1/exportacao/conjuntos?saida=xml")).status()).toBe(422);
  });

  test("a busca resiste a texto malicioso", async ({ page }) => {
    for (const q of ["'; DROP TABLE analitico.conjunto_busca; --", "<script>alert(1)</script>", "%%% ___ & | !"]) {
      await page.goto(`/conjuntos?q=${encodeURIComponent(q)}`);
      await expect(page.getByTestId("total")).toBeVisible();
    }
    await page.goto("/conjuntos");
    await expect(page.getByTestId("total")).toContainText("46 conjunto(s)");
    const marcador = await page.evaluate(() => document.title);
    expect(marcador).toBe("Inspire Catálogo");
  });
});
