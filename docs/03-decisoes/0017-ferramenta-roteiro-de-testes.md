# ADR-0017: Ferramenta independente de roteiro de testes

- **Status:** aceita
- **Data:** 2026-11-22
- **Decisores:** cliente (ideia e requisitos) e Claude (desenho)

## Contexto
O cliente quer que todos os testadores (professores, alunos, CNPq) conheçam e testem todas as funcionalidades, com um passo
a passo em dados reais, e que o resultado de cada caso seja **registrado** (nome, passou ou falhou, mensagem de erro,
comentário). Quer isso como solução apartada, simples, com SQLite e front-end simples, reaproveitável em outros módulos e
aplicativos. Sem imagens (não gastar armazenamento).

## Opções
**Opção 1 — Documento (HTML/Markdown) com caixas de marcar.** Barato, mas não guarda nada de forma consultável, mistura
respostas de várias pessoas e não dá visão consolidada.

**Opção 2 — Formulário pronto (Google Forms, Jira, ferramenta de gestão de testes).** Rápido e rico. Mas envia respostas e
conteúdo a um serviço externo (soberania, ADR-0002), cria dependência de conta e não serve offline em Docker.

**Opção 3 — Ferramenta própria mínima, independente do produto (escolhida).** Um contêiner com SQLite e uma página simples;
os casos vêm de arquivos JSON, então serve a qualquer sistema. Custo: manter o código (~400 linhas) e fazer os testes dela.

## Decisão
**Opção 3**, em `kit/roteiro-de-testes/`, sem nenhuma referência ao produto (regra do kit) e extraível a qualquer momento.
- **Python da biblioteca padrão** (servidor HTTP e `sqlite3`) e JavaScript sem build: nenhuma dependência de terceiros para
  auditar ou atualizar, alinhado a ADR-0002.
- Resultados: *Passou*, *Falhou* (mensagem de erro obrigatória) e *Não consegui executar*. Só o nome identifica a pessoa.
- Mesmo nome retoma a sessão aberta; sessão finalizada não é retomada (a próxima vira uma nova rodada).
- Sem PIN nem login (decisão do cliente em 2026-11-22: não é necessário por ora); a área de resultados abre direto e a porta só é publicada em `127.0.0.1`. CSV protegido contra fórmulas; texto sempre como texto.
- Sem login por usuário e sem anexos, de propósito. Não deve ser exposta à internet sem uma camada de acesso por cima.

- **Reunir resultados:** cada testador tem o seu banco (roda a ferramenta localmente) e envia o CSV de "Baixar meus
  resultados" ao responsável; `consolidar.py` junta tudo em um SQLite. Alternativa descartada por ora: uma instância
  compartilhada (exigiria hospedagem e proteção de acesso).

## Consequências
- Cada produto mantém os seus casos fora do kit (no caso deste, em `docs/`), e a ferramenta se reaproveita sem mudanças.
- Testada com 15 testes automatizados da API e um teste de fumaça da interface em navegador real.
