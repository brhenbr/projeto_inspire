# 5. Evoluir o projeto

**Em palavras simples:** o projeto é um protótipo feito para ser melhorado por quem o usa. Esta página mostra como
**sugerir**, **reportar defeitos** e, se você programa, **mexer no código** com segurança. Tudo acontece no GitHub, por
**issues** (conversas e pedidos) e **pull requests** (propostas de mudança).

## Sugerir uma melhoria
Abra uma issue com o [modelo de melhoria](../../.github/ISSUE_TEMPLATE/melhoria.yml): conte **o problema que você tem**
(não precisa propor a solução), quem se beneficia e com que frequência. Isso entra no [backlog](../01-produto/backlog/backlog.md).

## Reportar um defeito
Use o [modelo de defeito](../../.github/ISSUE_TEMPLATE/defeito.yml): passos para reproduzir, o esperado, o que aconteceu e a
mensagem de erro. Se foi achado num caso do manual, informe o **código do caso** (por exemplo, `COL-03`).

## Entender o desenho antes de mexer
| Quero saber... | Leia |
|---|---|
| O que é e como funciona (sem jargão) | [Como o sistema funciona](../02-arquitetura/00-como-o-sistema-funciona.md) |
| Quais as partes e como conversam | [C1](../02-arquitetura/c1-contexto.md) → [C2](../02-arquitetura/c2-conteineres.md) → [C3](../02-arquitetura/c3-componentes.md) |
| O que acontece passo a passo | [Fluxos](../02-arquitetura/fluxos.md) |
| Por que foi decidido assim | [Decisões (ADRs)](../03-decisoes/README.md) |
| O que ainda não faz | [Limites conhecidos](../01-produto/limites-conhecidos.md) |
| O que falta fazer | [Backlog](../01-produto/backlog/backlog.md) |

## Mexer no código (para quem programa)
**Mapa rápido:** `app/backend/src/inspire/` (Python/FastAPI, um módulo por assunto), `app/frontend/src/` (React/TypeScript),
`app/e2e/` (testes de navegador), `scripts/` (comandos úteis), `docs/` (tudo o que está escrito), `kit/` (ferramentas
reaproveitáveis, como a página de testes).

**Fluxo de trabalho recomendado**
1. Crie uma **branch** a partir da `main`: `git switch -c minha-melhoria`.
2. Faça a mudança **com testes** (o backend exige 80% de cobertura).
3. Rode o **portão de qualidade** antes de enviar:
   ```
   bash scripts/formatar.sh     # arruma o estilo do backend
   bash scripts/qualidade.sh    # lint, tipos, testes do backend (com PostgreSQL real) e do frontend
   bash scripts/e2e.sh          # opcional: testes de navegador (~10 min, baixa ~4 GB na 1ª vez)
   ```
4. Se a mudança altera uma **decisão** (tecnologia, segurança, modelo), registre um **ADR** em `docs/03-decisoes/`
   (modelo em `kit/templates/adr.md`), com **três opções**, prós e contras.
5. Atualize a **documentação** que a mudança afeta (e, se mudou uma tela, o caso correspondente em `docs/07-manual/casos/`).
6. Envie e abra um **pull request** (o modelo pede o essencial). O **CI** (veja abaixo) roda sozinho; revise o resultado.

**Regras que valem sempre** (as razões estão em [segurança e soberania](../05-testes/seguranca-e-soberania.md)):
- Nunca coloque **chaves, senhas ou o `.env`** no git. O CI procura segredos, mas não confie só nele.
- **Contatos pessoais** dos responsáveis pelos conjuntos nunca são guardados nem enviados a LLM.
- Dependências: altere `pyproject.toml`/`package.json` e regenere `uv.lock`/`package-lock.json` em contêiner; nunca instale no computador.
- **Nunca edite uma migração do banco já aplicada**: crie uma nova.
- Documentação em **português**; código e identificadores em **inglês**.

## O que é o CI (e o que ele faz por você)
O CI é um robô do GitHub que, a cada envio de código, roda **sozinho** os mesmos testes e varreduras. Você vê o resultado
na página do pull request (✔ verde ou ✗ vermelho). Explicação completa em [CI explicado](../06-deploy/ci-explicado.md).

## Licença
O repositório **ainda não tem licença**: por padrão, todos os direitos são reservados até a decisão (prevista para a
fase 2). Enquanto isso, o uso é para avaliação e desenvolvimento do projeto Inspire.
