# ADR-0002: Segurança e soberania como requisitos de projeto

- **Status:** aceita
- **Data:** 2026-11-21
- **Decisores:** cliente (dono do produto) e Claude

## Contexto
O produto trata metadados do governo federal e será avaliado por órgãos públicos. O dossiê do Inspire
destaca soberania computacional e conformidade com a LGPD. O cliente pediu que segurança e soberania
sejam mantidas desde o início.

Os metadados do portal são públicos, mas as **curadorias, prompts e propostas** geradas pelo projeto
são trabalho do projeto e podem revelar prioridades de política pública.

## Decisão
1. **Nada sai da infraestrutura controlada pelo projeto sem decisão explícita registrada em ADR.**
   Isso inclui prompts, propostas de curadoria e o conteúdo da base curada. Serviços de LLM em nuvem
   no exterior ficam **proibidos por padrão**; o provedor de LLM é configurável e o padrão é local ou
   sob controle do projeto.
2. **Software livre e auditável**, com licenças compatíveis com uso governamental. Dependências de
   origem conhecida, fixadas por versão, com varredura de vulnerabilidades no CI.
3. **Sem telemetria externa** nas ferramentas e imagens escolhidas, ou desligada por configuração.
4. **Segredos fora do código e do git**; a chave do portal só em variável de ambiente. Nunca em logs.
5. **Containers sem privilégios**, sem credenciais embutidas, rede interna entre serviços; só a
   entrada web fica exposta.
6. **Rastreabilidade de IA:** toda proposta de LLM registra modelo, versão, prompt e decisão humana.
7. **Dados pessoais:** o produto não deve coletar dados pessoais. Campos de contato de responsáveis
   (nome e e-mail do mantenedor dos conjuntos) existem no portal; o desenho deve tratá-los como
   dados pessoais (minimizar, não enviar a LLM, avaliar se precisam ser guardados).
8. **Portabilidade:** nada que prenda o produto a um fornecedor ou nuvem específicos.

## Consequências
- A escolha de LLM é limitada por onde há capacidade de execução sob controle do projeto (ver US-067).
- Alguns serviços gratuitos de nuvem ficam fora, mesmo que sejam mais fáceis ou melhores.
- Aumenta o trabalho de CI e de revisão de dependências, justificado pelo contexto institucional.
