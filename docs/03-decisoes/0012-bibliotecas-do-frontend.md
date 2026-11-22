# ADR-0012: Bibliotecas do frontend

- **Status:** aceita (decidida de forma autônoma; revisada e confirmada pelo cliente em 2026-11-21)
- **Data:** 2026-11-21
- **Decisores:** Claude, por delegação do cliente

## Contexto
O [ADR-0003](0003-stack-tecnologica.md) fixou React + TypeScript + Vite e deixou aberta a escolha de
biblioteca de componentes, roteamento e busca de dados. O cliente pediu interação básica, com boa
usabilidade. O projeto pode ficar público e precisa de dependências **poucas, auditáveis e fixadas**
([ADR-0002](0002-seguranca-e-soberania.md)); a instalação já mostrou custo alto de rede na máquina de desenvolvimento.

## Opções consideradas
### 1. Biblioteca de componentes completa (Mantine ou MUI) + TanStack Query + React Router
- **Prós:** muitos componentes prontos (tabelas, seletores, modais), cache de requisições, menos CSS.
- **Contras:** dezenas de dependências transitivas para auditar; aparência e comportamento atrelados à
  biblioteca; mais peso para o navegador; versões mudam rápido; para telas simples (listas, formulários,
  painéis) o ganho é pequeno.

### 2. React + React Router + componentes e CSS próprios, com um hook simples de dados — escolhida
- **Prós:** **uma única dependência nova** (React Router); controle total da acessibilidade e do visual;
  código pequeno de entender e manter; build leve; as telas deste produto são listas, formulários e painéis.
- **Contras:** escrevemos nós mesmos botões, abas, paginação e etiquetas; sem cache automático de requisições
  (aceitável: dados mudam pouco e a API é local).

### 3. Sem roteador (estado na própria página) e sem biblioteca
- **Prós:** zero dependência nova.
- **Contras:** perde links diretos, botão "voltar" e compartilhamento de uma busca por URL, que são
  essenciais para quem faz descoberta de dados.

## Decisão
**Opção 2.** Componentes próprios (etiqueta, cartão, abas, paginação, faceta), CSS único com variáveis,
português do Brasil, foco visível e rótulos em todos os campos. A **busca fica na URL** (filtros, ordem e
página), o que permite compartilhar e voltar.

## Consequências
- Se a interface crescer muito, adotar uma biblioteca de componentes passa a compensar; a API não muda.
- Acessibilidade é responsabilidade nossa: rótulos, foco, contraste e papéis ARIA são verificados nos testes.
