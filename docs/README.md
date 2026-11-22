# Documentação do projeto

| Pasta | Conteúdo |
|---|---|
| [00-descoberta](00-descoberta/) | Especificações recebidas e achados da investigação |
| [01-produto](01-produto/) | Visão e escopo, backlog, limites conhecidos, proposta de bases sociais |
| [02-arquitetura](02-arquitetura/00-como-o-sistema-funciona.md) | **Comece por aqui:** como o sistema funciona (sem jargão); diagramas C4, modelo de dados, mapeamento DCAT-BR |
| [03-decisoes](03-decisoes/) | ADRs (decisões de arquitetura e de produto) |
| 04-implementacao, 05-testes, 06-deploy | Registro de construção, testes (estratégia, E2E, segurança) e publicação (execução local, pacote de teste, proposta de CI) |
| [07-manual](07-manual/LEIA-ME.md) | Manual do usuário como roteiro de testes: 43 casos com dados reais |
| [diario](diario/) | Registro de cada sessão de trabalho |

## Como ver os diagramas
Os diagramas são texto (Mermaid) dentro dos arquivos `.md`, versionados com o código.

1. **Mais fácil, offline:** abra [diagramas.html](diagramas.html) no navegador (duplo clique). Ele reúne
   todos os diagramas. Para atualizá-lo depois de editar um diagrama, na raiz do repositório:
   `python -I kit/scripts/gerar_visualizador.py docs docs/diagramas.html`
2. **No VS Code:** instale a extensão **Markdown Preview Mermaid Support** e use *Abrir Visualização*
   (`Ctrl+Shift+V`) no arquivo `.md`.
3. **No GitHub:** os diagramas aparecem renderizados automaticamente ao abrir o `.md`.

`assets/mermaid.min.js` é a biblioteca Mermaid (licença MIT), incluída para a página funcionar sem internet.
