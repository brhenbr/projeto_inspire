# Roteiro de Testes

Ferramenta pequena e independente para **conduzir pessoas por casos de teste** e **guardar os resultados**: o testador
informa o nome, vê um caso por vez, executa no sistema testado e marca *Passou*, *Falhou* (com a mensagem de erro) ou
*Não consegui executar*, com comentário opcional. Serve a qualquer módulo ou aplicativo: só muda a pasta de casos.

Desenho e decisões: [DESENHO.md](DESENHO.md). Sem dependências de terceiros (só Python padrão), um contêiner, um
arquivo SQLite. Não cita nenhum produto: pode ser extraída deste repositório sem alterações.

## Subir
```
cd kit/roteiro-de-testes
docker compose up -d --build
```
Abra http://127.0.0.1:8090. Para testar outros casos: `CASOS_DIR_HOST=/caminho/dos/casos docker compose up -d`.

| Variável | Para que serve | Padrão |
|---|---|---|
| `CASOS_DIR_HOST` | Pasta com os roteiros `.json` (montada somente leitura) | `./casos-exemplo` |
| `ROTEIRO_PORT` | Porta no seu computador | `8090` |

Os dados ficam no volume `roteiro-dados` (sobrevivem a recriar o contêiner). Para zerar: `docker compose down -v`.

## Escrever um roteiro
Um arquivo `.json` na pasta de casos (veja `casos-exemplo/exemplo.json`). Campos de cada caso: `id` (único e estável),
`titulo`, `passos` (lista) e, opcionais, `objetivo`, `preparacao`, `esperado` (lista) e `anotar`. Mudou o conteúdo?
Mude a `versao` do roteiro: cada sessão guarda a versão que o testador viu. Arquivos inválidos são ignorados e o
motivo aparece no log do contêiner.

## Ver os resultados
Menu **Resultados** (abre direto): tabela com testador, caso, resultado, erro e comentário. **Baixar CSV** exporta tudo
(células que começam com `=`, `+`, `-` ou `@` ganham um apóstrofo, para não virarem fórmula na planilha).

## Testes da ferramenta
```
bash testar.sh
```
Roda os testes automatizados em um contêiner descartável (sem instalar nada no seu computador).

## Segurança, em resumo
Escuta em `127.0.0.1` por padrão; SQL parametrizado; texto sempre como texto (sem HTML injetado);
política de conteúdo restritiva; contêiner sem root, somente leitura e sem capacidades extras; limites de tamanho.
**Não tem login nem senha**: o nome é só um rótulo e qualquer pessoa que alcance a página vê todos os resultados. Não coloque na internet sem uma camada de acesso por cima.
