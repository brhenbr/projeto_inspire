# Diário — 2026-11-21 — Sessão 04: LLM real, DCAT-BR, chat e coleção por texto

## Objetivo da sessão
O cliente voltou, elogiou o MVP, aprovou todos os ADRs 0007–0013, pediu o roteador de LLMs gratuitos e a "parada
média" do plano (DCAT-BR, chat, coleção por texto, acabamento), e voltou a ficar ausente (modo autônomo).

## Decisões do cliente nesta sessão
- Provedor de LLM: APIs gratuitas dos principais fornecedores, com troca automática quando um estoura o limite.
- Licença e publicação no GitHub: depois dos testes. CI: o cliente quer entender antes (expliquei na conversa).
- Coleções: ele pedirá ao LLM para montá-las e não sabe como os professores as montarão (a tela ficou flexível).

## O que foi feito
Ver [Implementação 04](../04-implementacao/04-dcat-chat-e-roteador-llm.md). ADRs novos: 0014, 0015, 0016.

## Verificação
| Camada | Resultado |
|---|---|
| Backend | 272 testes, ruff e mypy limpos |
| Frontend | 38 testes, eslint e tsc limpos |
| E2E | **55 de 55** (9 cenários; 3 novos) |
| Provedores reais | Groq respondeu 4/4 propostas; roteador, chat e coleção por texto testados no catálogo real |

## Bug relatado pelo cliente
O texto digitado em "Curador(a)" ficava invisível (letra branca em campo branco no cabeçalho escuro). Corrigido no CSS.

## O que precisa do cliente
1. Conferir os termos de uso dos provedores gratuitos para dados públicos (US-067 parcial).
2. Decidir se quer a busca semântica por embeddings (US-080) ou se o chat basta.
3. Lista das "bases sociais" (US-037) e definição de licença e publicação (US-064).
4. Rever os diagramas C4 em linguagem mais simples (US-072).

## Teste manual do cliente (2026-11-22) e ajustes
O cliente executou o caso "bases sociais" e apontou: total instável entre chamadas, tema em uma etiqueta só, necessidade
de restaurar filtros sem chamar o LLM, nome da coleção cortado, falta de edição e descrição truncada na tela. Tudo tratado
(ver ADR-0016, seção de ajustes). Verificação: backend 274, frontend 41, E2E 55 de 55.
