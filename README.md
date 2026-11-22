# Inspire Catálogo

**Uma cópia pesquisável do catálogo de dados abertos do governo (dados.gov.br), com nota de qualidade das descrições,
curadoria humana (com sugestões opcionais de IA), coleções e exportação nos padrões do governo.**

Projeto da frente UFSCar do Inspire, desenvolvido para ser **avaliado por pesquisadores e melhorado a partir da sua
experiência**. Só os **metadados** (as descrições) são tratados: os arquivos de dados continuam nos órgãos.

> **Status:** MVP (fase 1) completo e testado. Protótipo de uso monousuário, sem login, rodando na sua máquina.
> O que ainda não faz está em [limites conhecidos](docs/01-produto/limites-conhecidos.md).

## Para que serve
| Quem | O que faz |
|---|---|
| **Quem explora dados** | Procura conjuntos por assunto, por órgão ou perguntando em português; vê a nota de qualidade; exporta para planilha |
| **Quem cura** | Corrige título, descrição e palavras-chave; aprova ou rejeita sugestões da IA; organiza coleções |
| **Quem coordena** | Acompanha a qualidade geral e por órgão e o andamento da curadoria |

Leia [**Como o sistema funciona**](docs/02-arquitetura/00-como-o-sistema-funciona.md): uma página, sem jargão.

## Comece em 3 passos
1. **Instale** o Docker Desktop e o Git. → [Preparar o ambiente](docs/guia/01-preparar-o-ambiente.md)
2. **Rode** o sistema com a base já carregada (sem chave, sem esperar). → [Rodar o sistema](docs/guia/02-rodar-o-sistema.md)
3. **Teste e avalie** com o manual de 43 casos em dados reais. → [Testar e avaliar](docs/guia/03-testar-e-avaliar.md)

```
git clone https://github.com/brhenbr/projeto_inspire.git && cd projeto_inspire
bash scripts/pacote-de-teste.sh carregar pacote/inspire-base-AAAAMMDD.dump   # pacote fornecido pela equipe
# abra http://127.0.0.1:8080
```
Detalhes, requisitos (Docker, 4 GB de memória, 6 GB de disco) e solução de problemas estão no
[**Guia do pesquisador**](docs/guia/README.md).

## O que o sistema faz hoje
Extração incremental do portal (com limite de ritmo) · busca em português (aceita acento e erro de digitação) · **Perguntar**
em linguagem natural · nota de qualidade explicada (17 regras) · curadoria com histórico e reversão · coleções manuais,
dinâmicas e descritas em texto · sugestões de LLM com aprovação humana (roteador de provedores gratuitos) · exportação CSV,
JSON e **DCAT-BR** (com qualidade em DQV) · painel e organizações · API REST documentada.

## Mapa da documentação
| Quero... | Vá para |
|---|---|
| Entender o que é | [Como o sistema funciona](docs/02-arquitetura/00-como-o-sistema-funciona.md) |
| Instalar, rodar, testar, resolver problemas | [Guia do pesquisador](docs/guia/README.md) |
| Ver como é feito por dentro | [C4: contexto, contêineres, componentes e fluxos](docs/02-arquitetura/c1-contexto.md) |
| Saber por que foi decidido assim | [Decisões (ADRs)](docs/03-decisoes/README.md) |
| Ver o que falta e os limites | [Backlog](docs/01-produto/backlog/backlog.md) · [Limites conhecidos](docs/01-produto/limites-conhecidos.md) |
| Sugerir melhorias ou mexer no código | [Evoluir o projeto](docs/guia/05-evoluir-o-projeto.md) · [CONTRIBUTING](CONTRIBUTING.md) |
| Conferir segurança e privacidade | [Segurança e soberania](docs/05-testes/seguranca-e-soberania.md) · [SECURITY](SECURITY.md) |
| Toda a documentação | [docs/](docs/README.md) |

## Estrutura do repositório
```
app/backend    Python + FastAPI (API, trabalhador, módulos de negócio)
app/frontend   React + TypeScript (a interface)
app/e2e        Testes de navegador (Playwright)
docs/          Documentação: guia, arquitetura, decisões, testes, manual
kit/           Ferramentas reaproveitáveis (inclui a página de testes: roteiro-de-testes)
scripts/       Comandos úteis (qualidade, E2E, pacote de teste, auditoria)
```

## Comandos para quem desenvolve
```
docker compose up --build              # sobe o sistema em http://127.0.0.1:8080
bash scripts/qualidade.sh              # lint, tipos, testes (backend com PostgreSQL real, frontend)
bash scripts/e2e.sh                    # testes ponta a ponta (navegador + portal falso)
bash scripts/formatar.sh               # formata o backend
bash scripts/auditar-dependencias.sh   # vulnerabilidades conhecidas nas dependências
bash scripts/validar-casos.sh          # valida os casos do manual de testes
```
Um robô de **integração contínua (CI)** roda esses mesmos testes a cada envio de código: veja
[CI explicado](docs/06-deploy/ci-explicado.md).

## Configuração (opcional)
Para **atualizar o catálogo** com dados novos é preciso uma chave de API do dados.gov.br, e para **IA real** uma chave de
um provedor de LLM gratuito. Copie `.env.example` para `.env` e preencha só o que for usar; o `.env` nunca é versionado.
Sem nada disso, o sistema funciona com a base do pacote e a IA em **modo simulado** (sem internet).

## Segurança e privacidade em uma frase
Nada sai da sua máquina sem decisão registrada; contatos pessoais dos responsáveis são removidos antes de gravar; só
informação pública vai a um LLM, e só se você o ligar; versões de dependências fixadas e auditadas.

## Licença
**Ainda não definida** (decisão prevista para a fase 2): até lá, todos os direitos são reservados e o uso é para avaliação
e desenvolvimento do projeto Inspire.
