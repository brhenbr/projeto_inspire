# Navegador e dependências oficiais do Playwright; a versão da imagem deve ser a mesma do @playwright/test.
FROM mcr.microsoft.com/playwright:v1.65.1-noble
WORKDIR /e2e
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY playwright.config.ts ./
COPY tests ./tests
CMD ["npx", "playwright", "test"]
