import { defineConfig } from "@playwright/test";

// Os cenários formam uma jornada: cada arquivo depende do estado deixado pelo anterior (ordem alfabética).
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { outputFolder: "reports/html", open: "never" }], ["json", { outputFile: "reports/resultado.json" }]],
  outputDir: "reports/artefatos",
  use: {
    baseURL: process.env.BASE_URL ?? "http://web:8080",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
    acceptDownloads: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
