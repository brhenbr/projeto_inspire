# Roteiro de Testes — desenho

**Em palavras simples:** uma página pequena e independente que conduz uma pessoa por uma lista de casos de teste, um de
cada vez. Para cada caso ela lê o passo a passo, executa no sistema que está testando, marca **passou** ou **falhou**
(com a mensagem de erro) e escreve um comentário. Tudo fica guardado e dá para ver quem testou o quê. A ferramenta não
sabe nada sobre o sistema testado: os casos vêm de arquivos, então serve para qualquer módulo ou aplicação.

> Esta pasta faz parte do `kit/` e deve ficar livre de referências ao produto onde nasceu (ver `kit/README.md`).
> Os casos de teste de cada produto ficam **fora** daqui, na documentação do próprio produto.

## Objetivos
1. Treinar o usuário e, ao mesmo tempo, **registrar o resultado** de cada funcionalidade (teste de aceitação).
2. Funcionar sozinha: um contêiner, um arquivo de banco, zero dependências externas, sem internet.
3. Ser reaproveitável: trocar a pasta de casos basta para testar outro módulo ou outro aplicativo.

## O que a pessoa vê
| Tela | O que faz |
|---|---|
| **Início** | Escolhe o roteiro, informa o nome e (opcional) o papel. Se já testou antes com o mesmo nome, oferece **continuar de onde parou**. |
| **Caso** | Mostra um caso por vez: objetivo, preparação, passos numerados, resultado esperado e o que anotar. Botões: **Passou**, **Falhou**, **Não consegui executar**. Em "Falhou" a mensagem de erro é obrigatória. Comentário sempre opcional. Barra de progresso ("12 de 30") e botão **Voltar**. |
| **Resumo** | Ao terminar (ou a qualquer hora): quantos passou/falharam/pulou, com a lista dos que falharam. |
| **Resultados** (abre direto, sem senha) | Quadro caso × testador, filtro por resultado, comentários e erros lado a lado, e **exportar CSV**. |

Sem imagens: o erro é registrado em texto (não ocupa espaço de armazenamento).

## Como os casos são escritos
Um arquivo JSON por roteiro, numa pasta de casos montada no contêiner. Exemplo mínimo:

```json
{
  "roteiro": "colecoes",
  "titulo": "Coleções",
  "versao": "2026-11-22",
  "casos": [
    {
      "id": "COL-01",
      "titulo": "Criar uma coleção descrevendo-a em texto",
      "objetivo": "Montar uma coleção dinâmica sem conhecer os filtros.",
      "preparacao": "Estar logado no sistema; ter a extração feita.",
      "passos": ["Abra o menu Coleções.", "Digite: ...", "Clique em Propor filtros."],
      "esperado": ["Aparecem etiquetas de filtros.", "A contagem é maior que zero."],
      "anotar": "O total mostrado e se os filtros fizeram sentido."
    }
  ]
}
```
Regras: `id` único e estável (é a chave do resultado); mudou o conteúdo do caso, muda a `versao` do roteiro, e a resposta
guarda a versão que a pessoa viu.

## Dados (SQLite, um arquivo)
| Tabela | Campos |
|---|---|
| `sessao` | `id`, `roteiro`, `versao_roteiro`, `testador`, `papel`, `iniciada_em`, `ultima_atividade_em`, `finalizada_em` |
| `resposta` | `id`, `sessao_id`, `caso_id`, `resultado` (`passou`, `falhou`, `nao_executou`), `comentario`, `mensagem_erro`, `respondida_em`; única por (`sessao_id`, `caso_id`) |

Responder de novo o mesmo caso **substitui** a resposta (a pessoa pode corrigir). Não há dados pessoais além do nome
informado; a ferramenta não pede e-mail.

## Arquitetura
- **Um contêiner**, Python da biblioteca padrão (servidor HTTP, `sqlite3`) **sem dependências de terceiros**; páginas
  HTML e JavaScript simples, sem etapa de build. Escolha pensada para ser auditável e durar (nada para atualizar ou varrer).
- **API mínima** (JSON): `GET /api/roteiros`, `POST /api/sessoes`, `GET /api/sessoes/{id}`, `PUT /api/sessoes/{id}/respostas/{caso}`,
  `POST /api/sessoes/{id}/finalizar`, `GET /api/resultados` e `GET /api/resultados.csv`.
- **Volume** para o arquivo `.db` (não se perde ao recriar o contêiner) e **somente leitura** para a pasta de casos.
- Escuta em `127.0.0.1` por padrão; para outras pessoas acessarem é preciso expor a porta de forma consciente.
- **Segurança:** sem login nem senha (decisão do cliente: por ora não é necessário), então a porta só é publicada em `127.0.0.1`; SQL sempre parametrizado; texto dos
  comentários escapado na tela (sem HTML injetado); limites de tamanho nos campos; CSV protegido contra fórmulas de planilha.

## Fluxo de uma pessoa
1. Abre a página, escolhe o roteiro, escreve o nome. 2. Executa o caso 1 no sistema testado e volta. 3. Marca o
resultado (e o erro, se falhou). 4. Segue até o último. 5. Vê o resumo. Pode fechar e voltar depois com o mesmo nome.

## Reunir resultados de vários testadores
Decisão do cliente: cada testador usa a ferramenta na **própria máquina**, com o **seu** SQLite. No Resumo há o botão
**Baixar meus resultados** (CSV só da sua sessão), que a pessoa envia ao responsável (nunca ao repositório). O script
`consolidar.py` lê vários CSV e grava um único SQLite com o resumo por caso. Evita hospedar a ferramenta e ter de
proteger um endereço compartilhado.

## Fora do escopo (de propósito)
Login por usuário, anexos e imagens, notificações, integração com ferramentas de chamados. Quem precisar disso depois
pode ler o CSV ou a API.

## Testes da própria ferramenta
Testes automatizados da API (criar sessão, responder, substituir, retomar, exigir erro em "falhou", CSV) e um teste
ponta a ponta simples no navegador. A ferramenta se testa com um roteiro de exemplo incluído na pasta.
