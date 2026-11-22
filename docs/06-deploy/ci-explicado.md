# CI explicado (integração contínua)

**Em palavras simples:** o CI é um **robô do GitHub** que, toda vez que alguém envia código novo, **roda sozinho os mesmos
testes e conferências** que rodaríamos à mão e diz se está tudo certo. Em vez de confiar na memória de cada pessoa ("será que
rodei os testes?"), o robô faz isso sempre, igual, e deixa o resultado visível para todos. Você não precisa configurar nada:
o arquivo `.github/workflows/ci.yml` já diz ao GitHub o que fazer.

## O que acontece, na prática
1. Alguém envia código (um **push** ou um **pull request**, que é um pedido para incluir uma mudança).
2. O GitHub **separa um computador virtual** (Linux, gratuito, descartável) e baixa o projeto nele.
3. O robô executa **três tarefas em paralelo** (os "jobs"). Cada uma é uma linha do resultado:

| Tarefa | O que confere | Tempo |
|---|---|---|
| **Qualidade** | Estilo e erros de código, tipos, testes do backend (com PostgreSQL de verdade), testes do frontend, validade dos casos do manual e testes da ferramenta de roteiro de testes | 10 a 15 min |
| **Segurança** | Procura **chaves e senhas** em todo o histórico do git e **vulnerabilidades conhecidas** nas dependências | 2 a 4 min |
| **E2E** | Abre um navegador de verdade e usa o sistema (55 cenários) contra um portal falso | 10 a 15 min |

4. O resultado aparece na página do pull request: **✔ verde** (passou) ou **✗ vermelho** (algo falhou), com o log de cada
   tarefa. Se o E2E falhar, o relatório com as telas do erro fica disponível para baixar por 7 dias.

## Onde ver
No GitHub, aba **Actions** do repositório: lista cada execução, com o histórico. Dentro de um pull request, a seção
**Checks** mostra as três tarefas. Um selo (✔/✗) aparece também ao lado de cada commit.

## O que fazer quando fica vermelho
1. Abra a execução e clique na tarefa que falhou; o erro está no fim do log.
2. Corrija e envie de novo (o robô roda outra vez sozinho).
3. Se for um problema do próprio robô (por exemplo, instabilidade do GitHub), use **Re-run jobs** na página da execução.

## Custo e limites
- Repositório **público**: roda **de graça**, sem limite prático.
- Repositório **privado**: há uma cota mensal gratuita de minutos (2.000 no plano gratuito). Cada execução completa usa uns
  30 a 40 minutos de computador, somando as três tarefas (o Linux conta 1 minuto por minuto). Dá para umas 50 execuções por mês;
  se acabar, o GitHub avisa. Os E2E são os mais pesados.

## Por que o CI deste projeto é conservador
- **Nenhum acesso a segredos:** o robô não recebe chaves de API (o sistema roda em modo simulado e com um portal falso).
  Por isso é seguro mesmo em pull requests de outras pessoas.
- **Permissão mínima:** o arquivo declara `contents: read`; o robô só **lê** o repositório.
- **Ações de terceiros fixadas por hash:** só usamos `actions/checkout` e `actions/upload-artifact`, apontados por
  identificador exato, não por versão que pode mudar. A busca de segredos e a auditoria de dependências são scripts nossos,
  que você lê no próprio repositório.

## Como o robô roda o que está no seu computador
Os comandos são os mesmos do dia a dia, e podem ser rodados à mão a qualquer momento:
```
bash scripts/qualidade.sh              # tarefa Qualidade
python scripts/varrer_segredos.py      # tarefa Segurança (segredos)
bash scripts/auditar-dependencias.sh   # tarefa Segurança (dependências)
bash scripts/e2e.sh                    # tarefa E2E
```
Se passa no seu computador e falha no GitHub, o log mostra a diferença (normalmente versão de ferramenta ou memória).

## Proteger a branch principal (recomendado, depois do primeiro envio)
No GitHub: *Settings → Branches → Add branch protection rule* para `main`, marcando **Require status checks to pass** e
escolhendo as três tarefas. Assim, ninguém junta uma mudança que quebre os testes.
