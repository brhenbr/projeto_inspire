# ADR-0001: Premissas de processo e escopo inicial

- **Status:** aceita
- **Data:** 2026-11-21
- **Decisores:** cliente (dono do produto) e Claude (arquitetura/engenharia)

## Contexto
Início do projeto. O cliente definiu o escopo inicial em conversa e pediu que todo o ciclo fique
documentado junto do código, com um kit de processo reaproveitável.

## Decisão
1. **Repositório único**, com o kit de processo em pastas apartáveis (`kit/`, `.claude/`), livres de
   referências ao produto.
2. **Documentação em português**, código em inglês, decisões em ADRs, sessões em diário.
3. **Desenho em C4** (C1–C3 e fluxos/sequência/estados no nível 4), diagramas em Mermaid.
4. **Escopo inicial:** somente metadados do catálogo completo, só datasets públicos, extração
   manual e recorrente, web + API, execução em Docker.
5. **Portal somente leitura** no curto/médio prazo; arquitetura preparada para, no futuro, propor
   alterações de volta (a escrita no portal exige perfil de administrador de organização).
6. **LLM:** a curadoria será humano parametriza / LLM executa. Prioridade para modelos gratuitos ou
   locais; se o custo for alto, o MVP entrega apenas a interface de integração.
7. **Stack:** adiada. Haverá uma conversa dedicada com o cliente durante o desenho.

## Consequências
- Nenhuma tecnologia está fixada ainda; as decisões de stack virão em ADRs próprios.
- O extrator depende de uma chave de API do cliente (perfil Consumidor).
- A premissa 5 exige separar o modelo da nossa camada curada do modelo espelhado do portal.
