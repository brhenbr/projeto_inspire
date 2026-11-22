// Teste de fumaça da interface no navegador (Playwright). Uso: bash testar-ui.sh
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://host.docker.internal:8090";
const PIN = process.env.RESULTS_PIN ?? "pin-local-teste";
const nome = "Testador " + Date.now();
const falhas = [];
const confere = (ok, msg) => { if (!ok) { falhas.push(msg); console.log("  FALHOU:", msg); } else console.log("  ok:", msg); };

const browser = await chromium.launch();
const page = await browser.newPage();
const erros = [];
page.on("pageerror", (e) => erros.push(String(e)));
// o 401 do PIN errado é esperado, então não conta como erro
page.on("console", (m) => { if (m.type() === "error" && !m.text().includes("401")) erros.push(m.text()); });

await page.goto(BASE);
await page.getByLabel("Seu nome").fill(nome);
await page.getByRole("button", { name: "Começar ou continuar" }).click();
await page.getByRole("heading", { name: "Abrir a página inicial" }).waitFor();
confere(await page.getByText("0 de 3 respondidos").isVisible(), "começa com 0 de 3 respondidos");

// sem escolher resultado: avisa
await page.getByRole("button", { name: "Salvar e ir para o próximo" }).click();
confere(await page.getByText("Escolha o resultado").isVisible(), "exige escolher o resultado");

// caso 1: passou
await page.getByRole("button", { name: "Passou", exact: true }).click();
await page.getByLabel("Comentário").fill("<b>rápido</b>");
await page.getByRole("button", { name: "Salvar e ir para o próximo" }).click();
await page.getByRole("heading", { name: "Fazer uma busca" }).waitFor();
confere(await page.getByText("1 de 3 respondidos").isVisible(), "avança e conta 1 de 3");

// caso 2: falhou sem erro => bloqueia; com erro => salva
await page.getByRole("button", { name: "Falhou", exact: true }).click();
await page.getByRole("button", { name: "Salvar e ir para o próximo" }).click();
confere(await page.getByText("Descreva a mensagem de erro").isVisible(), "falhou exige a mensagem de erro");
await page.getByLabel(/Mensagem de erro/).fill("HTTP 500 ao buscar");
await page.getByRole("button", { name: "Salvar e ir para o próximo" }).click();
await page.getByRole("heading", { name: "Sair do sistema" }).waitFor();

// voltar mostra a resposta anterior
await page.getByRole("link", { name: "← Voltar" }).click();
await page.getByRole("heading", { name: "Fazer uma busca" }).waitFor();
confere((await page.getByLabel(/Mensagem de erro/).inputValue()) === "HTTP 500 ao buscar", "voltar mostra o erro já registrado");

// último caso e resumo
await page.getByRole("link", { name: /EX-03/ }).click();
await page.getByRole("button", { name: "Não consegui executar" }).click();
await page.getByRole("button", { name: "Salvar e ver o resumo" }).click();
await page.getByRole("heading", { name: "Resumo" }).waitFor();
confere(await page.getByText("Para olhar com atenção").isVisible(), "resumo lista o que falhou ou não foi executado");
await page.getByRole("button", { name: "Finalizar teste" }).click();
await page.getByText("Teste finalizado").waitFor();
confere(true, "finaliza o teste");

// HTML do comentário não pode virar elemento
await page.goto(BASE + "/#/resultados");
await page.getByLabel("PIN").fill("pin-errado");
await page.getByRole("button", { name: "Ver resultados" }).click();
await page.getByText("PIN incorreto").waitFor();
confere(true, "PIN errado é recusado");
await page.getByLabel("PIN").fill(PIN);
await page.getByRole("button", { name: "Ver resultados" }).click();
await page.getByRole("cell", { name: nome }).first().waitFor();
confere(await page.getByText("<b>rápido</b>").first().isVisible(), "comentário aparece como texto, sem virar HTML");
confere((await page.locator("td b").count()) === 0, "nenhum <b> foi injetado");

// retomar depois de finalizar cria nova sessão; antes de finalizar, retoma
confere(erros.length === 0, "sem erros no console do navegador" + (erros.length ? ": " + erros.join(" | ") : ""));
await browser.close();
if (falhas.length) { console.log(`\n${falhas.length} verificação(ões) falharam`); process.exit(1); }
console.log("\nTudo certo na interface.");
