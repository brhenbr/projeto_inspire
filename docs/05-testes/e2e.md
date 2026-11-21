# Testes ponta a ponta (E2E)

**Em palavras simples:** um robô abre o sistema num navegador de verdade e faz o que uma pessoa faria:
extrai o catálogo, busca, edita, cria coleções, exporta, pede sugestões ao LLM e aprova. Ele roda contra uma
cópia descartável do sistema inteiro, com um "portal de mentira" que imita o dados.gov.br, então os testes
são rápidos, repetíveis e não sobrecarregam o portal de verdade. Decisão e alternativas:
[ADR-0013](../03-decisoes/0013-estrategia-de-testes-e2e.md).

## Como rodar
```
bash scripts/e2e.sh          # PowerShell: .\scripts\e2e.ps1
```
Pré-requisito: Docker Desktop aberto. Na primeira vez baixa a imagem oficial do Playwright (~1,5 GB).
O script sobe a pilha de `docker-compose.e2e.yml` (banco novo, portal falso, API, worker, web e o Playwright),
roda os cenários e **apaga tudo** ao final. O código de saída indica sucesso ou falha.
Relatório com capturas de tela e rastros dos testes que falharem: `app/e2e/reports/html/index.html`.

## O que existe na pilha E2E
| Peça | Papel |
|---|---|
| `fake-portal` | Imita o portal: chave obrigatória, páginas de 15, datas `dd/mm/aaaa`, respostas vazias intermitentes (1 a cada 7), um conjunto cujo detalhe dá sempre 400, e comandos para o teste mudar o "portal" no meio do cenário |
| `api`, `worker`, `web`, `db` | As mesmas imagens do produto |
| LLM | Modo **simulado** (sem IA e sem rede) |
| `playwright` | Navegador Chromium e os cenários |

O portal falso tem 46 conjuntos em 3 organizações (um deles com erro de detalhe).

## Cenários (8 arquivos, em ordem; cada um depende do estado deixado pelo anterior)
1. **Extração:** painel vazio, extração completa pela tela, relatório de conferência (46 de 46, cobertura, 1 sem detalhe), totais no painel.
2. **Descoberta:** busca sem acento/maiúscula/plural, pelo conteúdo, com erro de digitação e sem resultado; facetas; filtros combinados; ordenação; paginação; detalhe com qualidade explicada e recursos; conjunto sem detalhe; organizações; **ausência de contatos pessoais** em todas as telas e na API.
3. **Curadoria:** editar melhora a nota e não altera o dado do portal; versão curada na busca; reverter; status; duplicado inválido; validações; fila priorizada e ação em lote; histórico com autor e comentário.
4. **Coleções e exportação:** coleção manual a partir de busca; nome único; CSV (BOM, cabeçalho, linhas); JSON com original, curado e status; coleção dinâmica e exceção; renomear e apagar.
5. **LLM:** aviso de modo simulado; gerar para a fila; acompanhar execução; aprovar, editar e rejeitar; origem LLM no histórico; pedir e aprovar no detalhe; **nada é aplicado sem aprovação**.
6. **Qualidade configurável:** matriz de regras; desativar regra e mudar peso; recalcular e ver a nota mudar; restaurar; peso inválido.
7. **O portal muda:** extração incremental busca só o que mudou; a curadoria prevalece; conjunto aprovado volta para revisão; sugestões de LLM pendentes ficam desatualizadas e não podem ser aprovadas.
8. **Controle e segurança:** botão desabilitado com motivo e horário; HTTP 429; seis cliques simultâneos criam **uma** extração; nunca duas ativas; cancelamento; cabeçalhos de segurança; chave e contatos não vazam; entradas inválidas; busca resistente a texto malicioso.

## Limites conhecidos
- O portal falso é uma aproximação construída a partir de medições; o comportamento do portal real (incluindo o bloqueio
  com HTTP 405) foi tratado e testado à parte, e a extração real completa foi executada manualmente nesta fase.
- Os E2E não cobrem um provedor de LLM real (não há provedor aprovado); o contrato HTTP é coberto por testes de integração.
- Acessibilidade foi cuidada (rótulos, foco, papéis ARIA) e usada pelos seletores, mas não há auditoria automatizada dedicada.
