# Manual do usuário como roteiro de testes

**Em palavras simples:** este manual é uma lista de **43 casos de uso** que cobrem todas as telas e funções do sistema,
cada um com o passo a passo em dados reais. Você executa o caso no sistema, volta a uma página de testes e marca se
**passou**, **falhou** ou **não conseguiu executar**, com um comentário. Assim você aprende o sistema e, ao mesmo tempo,
testa. Todos os testadores fazem todos os casos.

Antes de começar, leia [Como o sistema funciona](../02-arquitetura/00-como-o-sistema-funciona.md) (uma página, sem
termos técnicos).

## Como fazer
1. **Suba o sistema** com a base carregada (ver [pacote de teste](../06-deploy/pacote-de-teste.md)). Ele fica em
   http://127.0.0.1:8080.
2. **Suba a página de testes:** `bash scripts/testes-de-aceitacao.sh` (abre em http://127.0.0.1:8090).
3. Na página de testes, informe o seu nome e comece. Ela mostra **um caso por vez**: você executa no sistema (outra aba
   do navegador), volta e marca o resultado. Se falhou, cole a mensagem de erro. Comentários ajudam muito.
4. Pode parar e voltar depois com o mesmo nome: ela continua de onde parou.
5. Ao terminar, clique em **Baixar meus resultados** e envie o arquivo para quem conduz o teste (e-mail ou pasta
   combinada; **nunca para o repositório**).

## Para quem conduz o teste
- Junte os arquivos dos testadores em um SQLite: `python kit/roteiro-de-testes/consolidar.py consolidado.db *.csv`.
- Os casos ficam em `casos/catalogo.json`. Mudou o sistema? Atualize o caso e a `versao` do arquivo; valide com
  `bash scripts/validar-casos.sh`.

## Pontos de atenção
- **Dados reais mudam.** Os números dos casos (por exemplo, "cerca de 86 conjuntos") são de 22/11/2026. Depois de uma
  nova extração podem variar um pouco; o que importa é a ordem de grandeza e o comportamento.
- **O LLM não responde sempre igual.** Nos casos que usam IA (COL-03, PER-01 a PER-03, LLM-02 a LLM-04), os resultados
  variam; o caso explica o que conferir. No **modo simulado** (padrão do pacote) a interpretação é por regras simples e
  mais limitada, e isso é esperado.
- **EXT-02 (atualizar o catálogo)** é opcional e exige a sua chave do portal; combine para não rodar ao mesmo tempo que
  outros testadores.
- **Sem imagens:** o erro é registrado em texto, para não ocupar espaço.

## Casos por assunto
| Prefixo | Assunto | Casos |
|---|---|---|
| PAI | Painel e identificação do curador | 2 |
| BUS | Busca, filtros, ordenação, endereço da busca, paginação | 7 |
| DET | Detalhe do conjunto, nota e histórico | 3 |
| ORG | Organizações | 2 |
| CUR | Curadoria humana, status, fila e lote | 4 |
| COL | Coleções (manual, dinâmica, por texto, edição, exceção, apagar) e o caso aberto das "bases sociais" | 7 |
| PER | Perguntar em português | 3 |
| LLM | Sugestões de LLM | 4 |
| EXP | Exportações (CSV, JSON, DCAT-BR, coleção) | 4 |
| CFG / EXT / API / SEG / GER / FIN | Configurações, extração, API, privacidade, erros e impressões gerais | 7 |
