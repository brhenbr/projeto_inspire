# Diário — 2026-11-21 — Sessão 03: construção autônoma do MVP

## Objetivo da sessão
O cliente ficou ausente e pediu: terminar a aplicação inteira, tomar as decisões, registrar as críticas em ADR (três
opções, prós e contras) e rodar os testes E2E. Ver o mapa completo em
[Implementação 03](../04-implementacao/03-aplicacao-completa.md).

## O que foi feito
- Extração completa e real do catálogo, controle de pedidos (ADR-0006), CLI e API de extrações.
- Discovery, qualidade, curadoria, coleções, LLM (simulado e compatível com OpenAI), exportação.
- Interface web com 9 telas. Testes E2E com Playwright e portal falso.
- ADRs 0007 a 0013 (decisões críticas, cada uma com três opções).

## Resultados de verificação
| Camada | Resultado |
|---|---|
| Backend (unidade e integração, PostgreSQL real) | 247 testes, cobertura 92,7% (meta 80%), ruff e mypy estrito limpos |
| Frontend (Vitest) | 32 testes, eslint e tsc limpos |
| E2E (Playwright, 8 cenários) | **52 de 52 passando** na execução final (4,7 min) |
| Extração real contra o portal | **Concluída:** 20.218 conjuntos de 20.682 declarados (97,8%), 560 sem detalhe, 0 erros, 89 min |
| Desempenho com dados reais | painel 0,3 s; busca 0,07 a 0,11 s; busca com erro de digitação 0,66 s; detalhe 0,08 s |
| Privacidade no banco real | 0 de 19.658 documentos com campo pessoal (13.363 tinham responsável no portal) |

## Problemas encontrados e corrigidos (por ordem de gravidade)
1. **Bloqueio do portal (HTTP 405).** Primeira extração real: 16.601 conjuntos marcados como "sem detalhe". O cliente tratava
   405 como definitivo e não limitava a taxa. Corrigido (limite de 4 req/s, pausa coletiva crescente) e a extração foi refeita.
2. **Testes tocavam o banco da aplicação** e um job de teste foi executado de verdade pelo worker. Agora testes de integração usam
   `inspire_test` e recusam outro banco; também ficaram herméticos quanto a variáveis de ambiente do compose.
3. **Exportação perdia 20 de 61 conjuntos:** parâmetro `formato` colidia com o filtro de formato do recurso. Renomeado para `saida`.
4. **Busca em português não casava "populações" com "população"** (o stemmer depende do acento). Normalização no índice e na consulta.
5. **Formulário de metadados mostrava valores antigos** depois de reverter ou aprovar. A tela agora remonta com os valores novos.
6. **nginx devolvia 502** ao recriar a API (guardava o IP do início); passa a resolver o nome dinamicamente. **Migração aplicada em versão
   intermediária** no banco real: criada a `0006` idempotente em vez de editar migração aplicada.
7. Imagem de migração desatualizada (já corrigida na sessão 02); scripts de E2E com falhas minhas (abortava ao fim de um contêiner de
   uso único; não reconstruía a imagem dos testes; healthcheck com IPv6), todos corrigidos.

## Decisões tomadas sem o cliente (revisão pendente)
ADRs [0007](../03-decisoes/0007-fila-de-jobs.md) a [0013](../03-decisoes/0013-estrategia-de-testes-e2e.md). Além delas:
- O LLM sobe em **modo simulado por padrão no compose** (não usa IA nem rede); provedor real exige configuração e lista de hosts.
- Valores iniciais de **pesos da qualidade** são julgamento meu (matriz em `docs/02-arquitetura/matriz-de-qualidade.md`).
- Limite de taxa ao portal: 4 req/s (conservador; o limite real do portal é desconhecido).
- Funcionalidades deixadas para a fase 2: verificação de links, busca semântica e chat, DCAT-BR/DQV exportados, detecção de duplicados,
  agendamento automático.

## O que precisa do cliente
1. Revisar os ADRs 0007 a 0013 e a matriz de pesos de qualidade.
2. **Provedor de LLM:** escolher um (ou um servidor com GPU) e informar a chave; a tarefa de avaliação de provedores (US-067) não foi feita.
3. Licença do repositório e primeiro `git push` (o CI será criado nessa hora).
4. Lista das "bases sociais" para a coleção inicial (US-037) e a leitura da especificação oficial do DCAT-BR (US-023).
5. Rever os diagramas C4 em linguagem mais simples (US-072).
