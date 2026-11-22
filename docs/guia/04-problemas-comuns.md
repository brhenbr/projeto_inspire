# 4. Problemas comuns

**Em palavras simples:** os tropeços mais prováveis, com a causa e a solução. Se o seu não estiver aqui, veja os registros
(`docker compose logs api worker`) e [abra uma issue](05-evoluir-o-projeto.md#reportar-um-defeito) colando a mensagem.

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `Cannot connect to the Docker daemon` / `docker: error during connect` | O Docker Desktop está fechado | Abra o Docker Desktop e espere "Engine running" |
| `bash: scripts/...: No such file` ou `\r: command not found` | Terminal errado ou fim de linha do Windows | Use o **Git Bash**; se persistir: `git config core.autocrlf false`, apague a pasta e clone de novo |
| `port is already allocated` / `address already in use` (8080 ou 8090) | Outro programa usa a porta | Feche o outro programa; ou rode com outra porta: `ROTEIRO_PORT=8091` para a página de testes. Para o sistema, mude `8080:8080` em `docker-compose.yml` |
| O navegador diz "não foi possível acessar" | O sistema ainda está subindo | Espere 1 a 2 minutos e recarregue; veja `docker compose ps` (tudo "healthy"/"Up") |
| A tela abre, mas o **Painel mostra zero conjuntos** | A base não foi carregada | Faça o [Caminho A](02-rodar-o-sistema.md) (pacote) ou a extração (Caminho B) |
| `O pacote está corrompido ou foi alterado` | O arquivo `.dump` não bate com o `.sha256` | Baixe os dois de novo; confirme que estão na mesma pasta |
| Falha ao construir (`failed to solve`, `no space left`) | Falta de espaço em disco | Libere espaço; `docker system prune` remove restos de construções antigas (peça confirmação antes) |
| O sistema fica lento ou reinicia sozinho | Pouca memória para o Docker | No Docker Desktop, *Settings → Resources*, libere ao menos 4 GB |
| **Atualizar catálogo** mostra "DADOS_GOV_API_KEY não configurada" | Sem chave do portal no `.env` | Normal no pacote de teste. Para atualizar, crie a chave (passo 1) e reinicie: `docker compose up -d` |
| **Atualizar catálogo** diz para esperar um intervalo | Proteção contra uso excessivo do portal | Aguarde o horário indicado (incremental: 60 min). Isso é intencional |
| Muitos conjuntos "sem detalhe" depois de atualizar | O portal responde 400 para alguns (cerca de 2,8%) ou bloqueou por excesso de chamadas | Aguarde e atualize de novo mais tarde; não rode várias extrações juntas |
| **Perguntar** devolve resultados estranhos | Modo simulado (regras simples) ou o LLM interpretou mal | Veja as etiquetas em "Como entendi", remova as que não fazem sentido, ou use "Abrir na busca" |
| "Todos os provedores indisponíveis agora" | Acabou a cota gratuita dos LLMs | Aguarde alguns minutos (o sistema tenta o próximo provedor sozinho) ou volte ao modo simulado |
| Acentos estranhos no CSV | Planilha abriu como outra codificação | No Excel, use *Dados → De texto/CSV* e escolha UTF-8; os dados têm "BOM" para abrir direto |
| Quero **começar de novo** (limpar tudo) | — | `docker compose down -v` e depois o Caminho A de novo |

## Ainda sem solução?
Anote **o que você fez**, **o que esperava**, **o que aconteceu** e cole a mensagem de erro, e abra uma issue
([modelo de defeito](../../.github/ISSUE_TEMPLATE/defeito.yml)). Quanto mais exato, mais rápido resolvemos.
