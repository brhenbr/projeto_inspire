# 3. Testar e avaliar

**Em palavras simples:** o teste é um **roteiro de 43 casos de uso**, cada um com o passo a passo em dados reais. Uma página
de testes mostra **um caso por vez**; você executa no sistema, volta e marca se **passou**, **falhou** ou **não conseguiu
executar**, com um comentário. Assim você aprende o sistema e o avalia ao mesmo tempo. **Todos fazem todos os casos**, e
cada comentário ajuda a decidir o que melhorar.

## Antes de começar
- O sistema precisa estar no ar ([Rodar o sistema](02-rodar-o-sistema.md)) em <http://127.0.0.1:8080>.
- Preencha o campo **Curador(a)** (canto superior direito do sistema) com o seu nome.
- Reserve de 2 a 3 horas. Dá para parar e continuar depois.

## Passo a passo
1. Suba a página de testes:
   ```
   bash scripts/testes-de-aceitacao.sh
   ```
2. Abra **<http://127.0.0.1:8090>**. Informe o seu nome, escolha o roteiro e clique em **Começar ou continuar**.
3. Para cada caso: leia o objetivo e o passo a passo, **execute no sistema** (deixe o sistema aberto em outra aba),
   volte, escolha **Passou**, **Falhou** ou **Não consegui executar** e escreva um comentário. Se **falhou**, cole a
   **mensagem de erro** (ou descreva o que aconteceu): é obrigatório.
4. Ao terminar, abra o **Resumo**, clique em **Finalizar teste** e depois em **Baixar meus resultados**.
5. **Envie o arquivo `.csv`** para quem conduz o teste (e-mail ou pasta combinada). Nunca o coloque no repositório.

Para pausar, basta fechar a página; ao voltar com o **mesmo nome** você continua de onde parou.
Para desligar a página de testes: `bash scripts/testes-de-aceitacao.sh parar` (as respostas ficam guardadas).

## O que torna um comentário útil
- **O que você esperava** e **o que aconteceu** (se diferente).
- Onde **travou ou se confundiu**, mesmo que tenha dado certo no fim.
- Termos que **não entendeu** e o que **faltou** para o seu trabalho.
- Em casos com IA, que o resultado **varia** de uma tentativa para outra: anote o que viu.

## Pontos de atenção
- **Números mudam.** Os números dos casos são de 22/11/2026; basta a mesma ordem de grandeza.
- **Modo simulado:** nos casos de IA, a interpretação é por regras simples e mais limitada. Isso é esperado.
- **Caso EXT-02 (atualizar o catálogo)** é opcional e só vale se você tiver a chave do portal. Combine para não rodar
  vários ao mesmo tempo.
- **Caso COL-07 (bases sociais)** é aberto: monte a coleção do seu jeito e conte o caminho que usou. Compararemos as
  escolhas de todos.

## Para quem conduz o teste: juntar os resultados
Reúna os `.csv` recebidos numa pasta e rode:
```
python kit/roteiro-de-testes/consolidar.py consolidado.db maria.csv joao.csv ana.csv
```
Gera um SQLite único e mostra, por caso, quantos passaram, falharam ou não executaram (marca os que têm falha). Rodar de novo
acrescenta; a resposta mais recente de cada pessoa em cada caso prevalece.

## Quer entender os casos por dentro?
Estão em `docs/07-manual/casos/catalogo.json` (e resumidos em [LEIA-ME do manual](../07-manual/LEIA-ME.md)). A página de testes é
uma ferramenta independente: [kit/roteiro-de-testes](../../kit/roteiro-de-testes/README.md).
