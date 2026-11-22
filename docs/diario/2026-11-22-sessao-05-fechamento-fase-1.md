# Diário — 2026-11-22 — Sessão 05: fechamento da fase 1

## Objetivo da sessão
O cliente testou o sistema, pediu ajustes, definiu a ferramenta de testes e pediu para **terminar tudo o que falta da fase 1**
(sem a fase 2) deixando o repositório pronto para o push final, em modo autônomo.

## Decisões do cliente
- Busca semântica **fora do MVP**. Termos de uso dos provedores de LLM e **licença** ficam para a **fase 2** (usar como está).
- Testadores usam Docker com a **base já carregada**; cada um com o **seu SQLite**, enviando o CSV de volta (nunca ao repositório).
- Ferramenta de testes: só o nome, três resultados (passou, falhou, não consegui executar), **sem PIN**, sem imagens.
- C4 em linguagem simples ficam comigo, para engenharia e para produto.
- Lista de "bases sociais": eu proponho; os testadores também montam a sua (caso aberto).

## O que foi feito
- **Ajustes do teste manual do cliente** (coleções editáveis, um chip por tema, restaurar filtros, nome curto, campo "Curador(a)" legível): ver [ADR-0016](../03-decisoes/0016-chat-como-tradutor-de-filtros.md).
- **Ferramenta Roteiro de Testes** (`kit/roteiro-de-testes`, [ADR-0017](../03-decisoes/0017-ferramenta-roteiro-de-testes.md)): SQLite, Python puro, "Baixar meus resultados" e `consolidar.py`.
- **Pacote de teste** com a base carregada (`scripts/pacote-de-teste.sh`) e teste do fluxo do testador numa instalação limpa.
- **Manual de testes**: 43 casos com dados reais (`docs/07-manual`), página "como o sistema funciona", C4 reescritos.
- **Bases sociais**: proposta e lacunas do portal ([proposta](../01-produto/bases-sociais-proposta.md)).
- **Avaliação de LLMs gratuitos** ([avaliação](../04-implementacao/05-avaliacao-de-llm-gratuitos.md)) e **checklist de segurança** com varreduras ([checklist](../05-testes/seguranca-e-soberania.md)).
- Preparação do repositório: `.gitattributes`, README final, proposta de CI, scripts de auditoria e de validação dos casos.

## Problemas encontrados e corrigidos
1. **Script do pacote carregava a base antes de o PostgreSQL subir** (achado na instalação limpa): agora espera o banco saudável.
2. **Fim de linha CRLF quebraria os `.sh` no Windows**: criado `.gitattributes` com LF.
3. **Modo simulado do "Perguntar"** transformava "formato" em palavra de busca e, sem resultado, mostrava o **catálogo inteiro**:
   palavras de pedido viram genéricas e o afrouxamento nunca solta o último filtro.
4. **A mensagem "Salvo" sumia** ao salvar metadados (o formulário remonta): estado movido para o componente pai.
5. **Auditoria de dependências** do backend lia só 1 pacote (ambiente `uv`): refeita a partir do `uv.lock` (47 pacotes).
6. Testes E2E antigos com seletores ambíguos e uma corrida de leitura: corrigidos.

## Verificação
| Camada | Resultado |
|---|---|
| Backend | 276 testes, ruff e mypy limpos |
| Frontend | 41 testes, eslint e tsc limpos |
| Ferramenta de testes | 19 testes da API + teste da interface em navegador real |
| E2E (Playwright) | **55 de 55** (9 cenários) |
| Dependências | `pip-audit` 0 e `npm audit` 0 vulnerabilidades |
| Segredos | nenhuma chave do `.env` no histórico do git |
| Instalação limpa | clone + pacote: 20.218 conjuntos, LLM simulado, curadoria vazia, 43 casos carregados, em ~3 min |

## O que ainda depende do cliente
1. Aprovar (ou cortar) a lista de bases sociais.
2. Decidir se o **PDF do dossiê** (terceiros) pode ir ao repositório público.
3. Escolher onde e como montar o repositório e fazer o primeiro push; depois, ativar o CI proposto.
4. Fase 2: licença, termos de uso dos provedores, verificação de links, busca semântica, agendamento etc.
