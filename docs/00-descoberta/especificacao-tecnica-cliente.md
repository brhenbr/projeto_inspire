# Especificação Técnica: Integração e Coleta de Catálogos (`dados.gov.br`)

**Objetivo:** Fornecer aos times de Arquitetura e Engenharia de Dados as referências técnicas, endpoints, modelos de dados e diretrizes operacionais para ingestão automatizada e curadoria do catálogo do Portal Brasileiro de Dados Abertos (`dados.gov.br`).

---

## 1. Visão Geral da Arquitetura do Portal

O Portal Brasileiro de Dados Abertos opera sob um modelo de **catálogo federado/referenciado**:
* O `dados.gov.br` atua como **repositório central de metadados** (gerido pela Controladoria-Geral da União - CGU).
* Os **recursos físicos** (arquivos CSV, JSON, XML, planilhas ou APIs setoriais) permanecem hospedados na infraestrutura dos respectivos órgãos publicadores.
* **Implicação para Curadoria:** A ingestão via API do portal extrai a camada de *metadados* (conjuntos, organizações, temas, tags e URLs dos recursos). A validação de disponibilidade, integridade e esquema real dos dados exige uma segunda etapa de verificação ativa (*healthcheck* HTTP e amostragem) diretamente nas URLs apontadas pelos recursos.

---

## 2. Ambientes e Especificação Base

* **Padrão Arquitetural:** RESTful over HTTPS
* **Formato de Intercâmbio:** `application/json` (UTF-8)
* **Documentação Interativa (OpenAPI / Swagger):**
  * **Produção:** `https://dados.gov.br/swagger-ui/index.html`
  * **Homologação:** `https://hmg.dados.gov.br/swagger-ui/index.html`
* **Base URL (Produção):** `https://dados.gov.br`
* **Autenticação:**
  * **Rotas Públicas (`GET /dados/api/publico/...` e taxonomias):** Acesso aberto, sem necessidade de token (`Bearer`) ou chave de API.
  * **Rotas Administrativas/Escrita (`POST`, `PUT`, `PATCH`, `DELETE`):** Restritas a publicadores autenticados via ecossistema **gov.br** (não aplicáveis ao fluxo de leitura/curadoria externa).

---

## 3. Catálogo de Endpoints para Ingestão e Curadoria

### 3.1. Conjuntos de Dados (Datasets)

| Método | Endpoint | Descrição | Uso na Curadoria |
| :--- | :--- | :--- | :--- |
| `GET` | `/dados/api/publico/conjuntos-dados` | Lista os conjuntos de dados cadastrados com suporte a paginação e filtros. | Varredura completa (*full scan*) ou incremental do catálogo. |
| `GET` | `/dados/api/publico/conjuntos-dados/{id}` | Retorna os metadados completos de um conjunto específico, incluindo a lista detalhada de seus **recursos**. | Extração profunda de metadados, dicionários e URLs de download. |
| `GET` | `/dados/api/publico/conjuntos-dados/{id}/tag` | Lista as tags vinculadas a um conjunto de dados específico. | Enriquecimento semântico e auditoria de indexação. |

### 3.2. Organizações (Órgãos e Entidades Publicadoras)

| Método | Endpoint | Descrição | Uso na Curadoria |
| :--- | :--- | :--- | :--- |
| `GET` | `/dados/api/publico/organizacao` | Lista as organizações publicadoras registradas no portal. | Mapeamento de governança, esfera (federal, estadual, municipal) e responsáveis. |
| `GET` | `/dados/api/publico/organizacao/{id}` | Detalha metadados de uma organização específica. | Consolidação de indicadores de qualidade e atualização por órgão. |

### 3.3. Taxonomias, Classificações e Conformidade

Estes endpoints funcionam como **tabelas de domínio (dimensões)** essenciais para normalizar dados e aplicar regras de curadoria automatizada:

| Método | Endpoint | Descrição | Uso na Curadoria |
| :--- | :--- | :--- | :--- |
| `GET` | `/dados/api/temas` | Lista os temas oficiais do catálogo. | Classificação temática e agrupamento de domínios de negócio. |
| `GET` | `/dados/api/tags` | Lista o vocabulário de tags utilizadas nos conjuntos. | Análise de dispersão, duplicidade semântica e padronização. |
| `GET` | `/dados/api/publico/conjuntos-dados/formatos` | Lista os formatos de arquivo/recurso reconhecidos pelo portal. | Avaliação de aderência a formatos abertos (ex.: CSV/JSON vs. PDF/XLS). |
| `GET` | `/dados/api/publico/conjuntos-dados/observancia-legal` | Lista os enquadramentos de observância legal/normativa. | Auditoria de conformidade regulatória e transparência ativa. |
| `GET` | `/dados/api/publico/conjuntos-dados/objetivos-desenvolvimento-sustentavel` | Lista os Objetivos de Desenvolvimento Sustentável (ODS - ONU). | Rastreabilidade de impacto e políticas públicas. |

### 3.4. Engajamento e Demanda Social (Opcional para Priorização)

| Método | Endpoint | Descrição | Uso na Curadoria |
| :--- | :--- | :--- | :--- |
| `GET` | `/dados/api/publico/reusos` | Lista aplicações, estudos e painéis que utilizam bases do portal. | Priorização de curadoria com base em relevância e uso real pela sociedade. |
| `GET` | `/dados/api/publico/reuso/{id}` | Detalha um reúso específico e os conjuntos vinculados. | Mapeamento de linhagem e impacto. |
| `GET` | `/dados/api/solicitacoes` | Lista solicitações de abertura de dados feitas por cidadãos. | Identificação de lacunas no catálogo (*gap analysis*). |

---

## 4. Modelo Conceitual de Dados para Ingestão

Para estruturar o *Data Lake* / *Catalog Store* interno, recomenda-se modelar as entidades extraídas na seguinte hierarquia:

```text
Organizacao (1) ──────< (N) ConjuntoDados (1) ──────< (N) Recurso
                                │
                                ├────── (N:N) Tema
                                ├────── (N:N) Tag
                                ├────── (N:N) ODS
                                └────── (1:N) Reuso
```

### Atributos Críticos para Curadoria
1. **Nível Conjunto (`ConjuntoDados`):**
   * Identificador único (`id`), título, descrição/resumo.
   * Organização publicadora (`organizacaoId`).
   * Datas de criação, última modificação de metadados e periodicidade declarada de atualização.
   * Licença de uso, cobertura temporal e cobertura geográfica.
   * Temas, Tags, Observância Legal e ODS vinculados.
2. **Nível Recurso (`Recurso`):**
   * Identificador único (`id`), título e descrição do recurso.
   * URL de acesso (`link` / `url`).
   * Formato declarado (ex.: `CSV`, `JSON`, `API`, `PDF`).
   * Tamanho declarado e data de última atualização do recurso.

---

## 5. Requisitos Não-Funcionais e Diretrizes de Engenharia

### 5.1. Estratégia de Coleta (Extração)
* **Paginação Controlada:** Ao consumir `/dados/api/publico/conjuntos-dados`, inspecionar os parâmetros de paginação vigentes no Swagger (ex.: `pagina`, `tamanhoPagina` ou equivalentes) e iterar até o esgotamento dos registros, registrando o total esperado vs. total coletado.
* **Resiliência e *Rate Limiting*:**
  * Implementar política de *retry* com *exponential backoff* e *jitter* para códigos HTTP `429`, `500`, `502`, `503` e `504`.
  * Configurar *timeouts* explícitos (ex.: `10s` para conexão, `30s` para leitura).
  * Limitar a concorrência (ex.: máximo de `2` a `5` requisições simultâneas) e adicionar `User-Agent` identificando a aplicação de coleta.

### 5.2. Versionamento e Rastreabilidade (*Change Data Capture* em Lote)
* Como APIs de catálogo nem sempre garantem filtros confiáveis por data de alteração em todos os sub-recursos, adote o padrão **Raw Snapshot + Hash**:
  1. Persistir o payload JSON bruto na camada *Bronze/Raw* particionado por data de execução (`YYYY/MM/DD`).
  2. Calcular um hash determinístico (ex.: `SHA-256`) sobre os campos relevantes de cada `ConjuntoDados` e `Recurso`.
  3. Comparar o hash atual com o último estado conhecido para identificar registros **Novos**, **Modificados**, **Inalterados** ou **Removidos do Catálogo** (*soft delete*).

### 5.3. Pipeline de Curadoria Automatizada (Camada Silver/Gold)
Recomenda-se que o motor de curadoria calcule um **Índice de Qualidade de Metadados e Disponibilidade** por conjunto de dados, avaliando:
* **Completude de Metadados:** Presença e tamanho mínimo de descrição, dicionário de dados, periodicidade, licença e tags.
* **Abertura Técnica (Escala 5 Estrelas de Dados Abertos):** Penalização de formatos proprietários ou não estruturados (`PDF`, `DOC`, `XLS`) em favor de formatos abertos legíveis por máquina (`CSV`, `JSON`, `XML`, `RDF`, `API`).
* **Atualidade (*Freshness*):** Cruzamento entre a periodicidade declarada (ex.: mensal, anual) e a data efetiva da última atualização do recurso.
* **Acessibilidade Ativa (*Link Rot Check*):**
  * Worker assíncrono separado da coleta do catálogo que executa requisições `HEAD` (com fallback para `GET` com leitura parcial de bytes/`Range: bytes=0-1024`) nas URLs dos recursos.
  * Registra: *Status HTTP*, *Tempo de Resposta*, *Content-Type real* (comparando com o formato declarado) e *Validade de Certificado TLS*.

---

## 6. Integração Complementar com Portais Setoriais (CKAN)

Durante a fase de descoberta, o time de engenharia deve prever extensibilidade para conectores secundários. Diversos órgãos federais indexados no `dados.gov.br` operam instâncias próprias baseadas no software **CKAN** (ex.: Tesouro Transparente, IBAMA, ANP).
* Caso a URL de um recurso ou conjunto aponte para uma instância CKAN identificada, o pipeline pode opcionalmente consultar a API nativa do CKAN (`/api/3/action/package_show?id=...`) para extrair metadados técnicos adicionais (como esquemas de colunas do *DataStore* ou hashes originais de arquivos).

---

## 7. Checklist de Próximos Passos para o Time

- [ ] **Arquitetura:** Definir a topologia de armazenamento (Camada Raw para snapshots JSON + Banco Relacional/Analítico para histórico de estados e métricas de curadoria).
- [ ] **Engenharia (Descoberta):** Consultar o Swagger (`https://dados.gov.br/swagger-ui/index.html`) para validar os nomes exatos dos parâmetros de query/paginação e o schema atualizado de resposta do endpoint `/dados/api/publico/conjuntos-dados/{id}`.
- [ ] **Engenharia (Ingestão):** Implementar o coletor de dimensões (`temas`, `tags`, `formatos`, `organizacao`) seguido pelo coletor paginado de `conjuntos-dados`.
- [ ] **Engenharia (Validação):** Construir a fila de verificação assíncrona de URLs de recursos (*Link Checker* e detecção de MIME Type real).
- [ ] **Governança/Negócio:** Definir os pesos das regras de curadoria (completude, formato aberto, disponibilidade e atualização) para geração do scorecard de qualidade.