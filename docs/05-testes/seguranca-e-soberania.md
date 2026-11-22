# Checklist de segurança e soberania (US-066)

**Em palavras simples:** a lista do que prometemos sobre segurança e privacidade ([ADR-0002](../03-decisoes/0002-seguranca-e-soberania.md),
[ADR-0004](../03-decisoes/0004-provedor-de-llm-externo-controlado.md)), com a **prova** de cada item e a data em que foi
conferido. Verificado em 2026-11-22.

| # | Promessa | Como foi verificado | Situação |
|---|---|---|---|
| 1 | Nada sai da infraestrutura sem ADR | Só dois destinos externos: o portal (extração) e o LLM (opcional, ADR-0004/0014). O frontend não carrega nenhuma URL externa (fontes, rastreadores): varredura do código | ✔ |
| 2 | LLM externo desligado por padrão, com aviso na tela | Padrão do compose é o modo **simulado**; o provedor real exige `LLM_PROVIDER=roteador` e chaves; faixa de aviso fixa na tela (teste E2E e de unidade) | ✔ |
| 3 | Hosts de LLM fixos e aprovados | Endereços dos provedores estão no código; a lista no `.env` só escolhe entre eles | ✔ |
| 4 | Só campos públicos vão ao LLM | Lista fixa de campos no código e teste que falha se algo fora dela entrar; o chat só envia o texto digitado e o vocabulário público | ✔ |
| 5 | Contatos de responsáveis não são guardados | Removidos na extração, antes do hash. Banco real: 0 de 19.658 detalhes com campo pessoal (13.363 tinham responsável no portal) | ✔ |
| 6 | Segredos fora do repositório | `.env` ignorado pelo git. Varredura do **histórico inteiro**: nenhuma das 5 chaves do `.env` aparece, e nenhum padrão de chave (Groq, Google, OpenAI/OpenRouter, JWT) | ✔ |
| 7 | Documentos contratuais fora do repositório | `docs/00-descoberta/restrito/` ignorado; busca por termos financeiros nos arquivos versionados: nenhum | ✔ |
| 8 | Dependências fixadas e sem vulnerabilidades conhecidas | `uv.lock` (47 pacotes) e `package-lock.json` fixados. `pip-audit`: nenhuma vulnerabilidade; `npm audit`: 0 (com e sem dependências de desenvolvimento) | ✔ (manual) |
| 9 | Sem telemetria externa | Nenhum código de telemetria; nada de CDN; o único tráfego de saída é o do item 1 | ✔ |
| 10 | Contêineres endurecidos | Sem root, capacidades removidas, sistema de arquivos somente leitura onde possível. Só a tela é publicada (`127.0.0.1:8080`); API, trabalhador e banco ficam na rede interna | ✔ |
| 11 | Cabeçalhos de segurança na tela | `X-Content-Type-Options`, `X-Frame-Options: DENY` e `Referrer-Policy: no-referrer` | ✔ |
| 12 | Exportação segura | O CSV protege contra fórmulas de planilha; o DCAT-BR não inclui contato de responsável | ✔ (testes) |
| 13 | Banco de teste isolado | Os testes de integração recusam rodar fora de um banco `*_test` | ✔ |
| 14 | Ferramenta de testes | Sem login nem senha (decisão do cliente): porta só em `127.0.0.1`; texto sempre como texto; CSV protegido | ✔ com ressalva |

## Pendências e ressalvas
- **Varredura automática recorrente (CI):** hoje as varreduras (itens 6 e 8) são manuais. Quando houver repositório remoto,
  vale automatizá-las. Proposta de pipeline em [ci-proposta.md](../06-deploy/ci-proposta.md).
- **Termos de uso dos provedores de LLM:** decisão do cliente: avaliar na fase 2; por ora usamos como estão. Lembrete:
  planos gratuitos costumam permitir que o provedor retenha os textos enviados; por isso só vão textos públicos.
- **Licença do repositório:** decisão do cliente: fase 2.
- **PDF de terceiros no repositório:** `docs/00-descoberta/Projeto_INSPIRE_Dossie_Detalhado.pdf` está versionado. Se o
  repositório ficar público, confirmar se pode ser redistribuído; senão, mover para `docs/00-descoberta/restrito/`.
- **Descrições do portal** podem conter e-mails institucionais (ouvidoria, diretoria); são texto público do portal e
  não o campo de contato do responsável. Constam do pacote de teste.
- **A pausa por cota do roteador** vive na memória de cada processo (não é compartilhada); aceitável no MVP.
