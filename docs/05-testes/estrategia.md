# Estratégia de testes

**Em palavras simples:** testamos em três níveis, do mais barato ao mais completo, para que o sistema
não quebre por coisa boba, sem exagerar para um MVP.

| Nível | O que cobre | Ferramenta | Quando roda |
|---|---|---|---|
| Unidade | Regras e funções isoladas (config, filtros, regras de qualidade) | pytest, Vitest | A cada mudança |
| Integração | Código com PostgreSQL real e a API do portal simulada | pytest, respx | Portão local |
| Ponta a ponta (E2E) | Fluxos do usuário no navegador: extração, busca, curadoria, LLM | Playwright | Antes de cada demonstração; o cliente participa |

## Regras
- **Portão local:** `bash scripts/qualidade.sh` roda lint, tipos, testes e cobertura. Cobertura mínima de 80% no backend.
- **Banco real nos testes de integração**, nunca simulado, para pegar erros de SQL e de migração.
- **A API do portal é sempre simulada nos testes.** Só os spikes e a extração real a chamam.
- **Teste de segurança obrigatório:** contatos pessoais nunca chegam ao banco, à API nem ao LLM (US-009, US-068).
- **Falhas conhecidas da API do portal** (401, 429, 5xx, timeout, página vazia intermitente) têm testes próprios (US-002).
