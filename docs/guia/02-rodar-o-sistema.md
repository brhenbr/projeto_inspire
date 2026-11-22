# 2. Rodar o sistema

**Em palavras simples:** há dois caminhos. O **A (pacote de teste)** é o recomendado: você recebe um arquivo com o
catálogo já copiado do portal e o sistema fica pronto em poucos minutos, sem chave e sem esperar. O **B (do zero)** copia o
catálogo do portal você mesmo e leva cerca de 1h30, e exige uma chave do portal.

*Todos os comandos abaixo são no terminal, dentro da pasta `projeto_inspire` (no Windows, use o Git Bash). O Docker
Desktop precisa estar aberto.*

## Caminho A: com o pacote de teste (recomendado)
1. **Peça o pacote** a quem convidou você: são dois arquivos, `inspire-base-AAAAMMDD.dump` (~52 MB) e o `.sha256`.
2. Crie a pasta `pacote` dentro do projeto e coloque os dois arquivos nela.
3. Carregue e suba tudo com **um comando**:
   ```
   bash scripts/pacote-de-teste.sh carregar pacote/inspire-base-AAAAMMDD.dump
   ```
   Na primeira vez leva uns 3 a 5 minutos (baixa e constrói as imagens). O comando confere a integridade do arquivo,
   carrega a base e sobe o sistema.
4. Abra **<http://127.0.0.1:8080>** no navegador.

**Como saber que deu certo:** o Painel mostra cerca de **20.200 conjuntos** e **256 organizações**, e a faixa no topo diz
**"Modo simulado"**.

## Caminho B: do zero, copiando o portal
1. Obtenha a chave (veja o [passo anterior](01-preparar-o-ambiente.md#duas-contas-opcionais-você-só-precisa-se-quiser-ir-além)),
   copie o modelo e preencha:
   ```
   cp .env.example .env
   ```
   Abra o `.env` num editor e escreva a chave em `DADOS_GOV_API_KEY=`.
2. Suba o sistema: `docker compose up --build` (deixe esse terminal aberto; para parar, `Ctrl+C`).
   Para rodar sem prender o terminal, use `docker compose up -d --build`.
3. Abra <http://127.0.0.1:8080>, vá em **Extração** e clique em **Atualizar catálogo**. A cópia completa leva **cerca de
   1h30** e o sistema respeita o ritmo do portal (4 chamadas por segundo, para não ser bloqueado). Pode fechar a página:
   ela continua em segundo plano.

## Usar o dia a dia
| Quero... | Comando |
|---|---|
| Ver se está no ar | `docker compose ps` |
| Parar sem perder nada | `docker compose stop` |
| Voltar a ligar | `docker compose start` |
| Ver o que está acontecendo (erros) | `docker compose logs -f api worker` |
| Desligar e **apagar tudo** (inclusive a base) | `docker compose down -v` |

Os dados ficam num "volume" do Docker: sobrevivem a `stop`, `start` e a reiniciar o computador. Só `down -v` apaga.

## Conhecendo o sistema (10 minutos)
1. **Painel:** os números gerais.
2. **Buscar:** digite `bolsa família` e abra o conjunto **Bolsa Família**; veja a aba **Qualidade** (a nota é explicada).
3. **Perguntar:** escreva `dados do CadÚnico sobre famílias por faixa de renda`.
4. **Coleções:** crie uma coleção descrevendo-a em texto.
5. **Exportar:** na busca, clique em **Exportar DCAT-BR**.

O restante está no [manual de testes](03-testar-e-avaliar.md), que percorre todas as funções com dados reais.

## Modo simulado × IA real
Por padrão o sistema usa uma "IA de mentira" (regras simples, sem internet): serve para aprender o fluxo, mas as sugestões
são limitadas. Para IA real, preencha no `.env` ao menos uma chave (por exemplo `GROQ_API_KEY=`) e `LLM_PROVIDER=roteador`,
e reinicie: `docker compose up -d`. A tela passa a avisar que há um **provedor externo**; só informação pública do catálogo
e o texto que você digita são enviados.
