# Proposta de CI (ainda **não** ativado)

**Em palavras simples:** "CI" é um robô do GitHub que, a cada envio de código, roda sozinho os mesmos testes e varreduras
que rodamos à mão. Aqui está a proposta, para ativar **depois** do primeiro push, quando o cliente decidir. Este arquivo
é só um rascunho: não existe `.github/workflows/` no repositório, então nada roda sozinho.

## O que o robô faria a cada push e a cada pedido de mudança
1. Construir as imagens e rodar o portão de qualidade (`scripts/qualidade.sh`): ruff, mypy, pytest com PostgreSQL real,
   eslint, tsc e vitest.
2. Rodar os testes E2E (`scripts/e2e.sh`), em uma execução à parte (mais lenta, uns 6 minutos).
3. Varrer as dependências: `pip-audit` sobre o `uv.lock` e `npm audit`.
4. Procurar segredos no código novo (por exemplo, com `gitleaks`).
5. Validar os roteiros de teste (`scripts/validar-casos.sh`).

## Rascunho do arquivo `.github/workflows/ci.yml`
```yaml
name: ci
on: [push, pull_request]
jobs:
  qualidade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash scripts/qualidade.sh
      - run: bash scripts/validar-casos.sh
  seguranca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
      - run: bash scripts/auditar-dependencias.sh
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash scripts/e2e.sh
```
O script `scripts/auditar-dependencias.sh` (já existe e roda à mão) faz o `pip-audit` e o `npm audit`.

## Pontos a decidir
- **Quando ativar:** depois do primeiro push e da definição do repositório.
- **Custo:** repositório público roda de graça; privado tem cota mensal gratuita (suficiente para este tamanho).
- **Ações de terceiros** (`actions/checkout`, `gitleaks-action`): são dependências externas; fixar por versão ou por
  *hash* ao ativar, coerente com a regra de dependências auditáveis (ADR-0002).
