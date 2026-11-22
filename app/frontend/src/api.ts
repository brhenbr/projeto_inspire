/** Cliente da API própria (/api/v1). A tela nunca fala com o portal nem com o banco. */

export class ApiError extends Error {
  status: number;
  detail: string;
  data: unknown;
  constructor(status: number, detail: string, data?: unknown) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

const CURATOR_KEY = "inspire.curador";
export const getCurator = (): string => localStorage.getItem(CURATOR_KEY) ?? "";
export const setCurator = (name: string): void => localStorage.setItem(CURATOR_KEY, name.trim());

export type Params = Record<string, string | number | boolean | null | undefined>;

export function qs(params: Params = {}): string {
  const out = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === "") continue;
    out.set(k, String(v));
  }
  const s = out.toString();
  return s ? `?${s}` : "";
}

function messageFrom(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const d = data as { detail?: unknown; motivo?: unknown };
    if (typeof d.detail === "string") return d.detail;
    if (Array.isArray(d.detail)) {
      return d.detail
        .map((x: { msg?: string; loc?: unknown[] }) => `${(x.loc ?? []).slice(1).join(".")}: ${x.msg ?? ""}`)
        .join("; ");
    }
    if (typeof d.motivo === "string") return d.motivo;
  }
  return `Erro ${status}`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const curator = getCurator();
  if (curator) headers["X-Curador"] = curator;
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  // 503 do /saude traz corpo válido; os demais erros viram ApiError.
  if (!response.ok && !(response.status === 503 && path === "/saude")) {
    throw new ApiError(response.status, messageFrom(data, response.status), data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path + qs(params)),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body ?? {}),
  del: <T>(path: string) => request<T>("DELETE", path),
  /** Endereço (relativo) de um download, para usar em <a href>. */
  url: (path: string, params?: Params) => `/api/v1${path}${qs(params)}`,
};

// ------------------------------------------------------------------ tipos

export type Saude = { status: "ok" | "degradado"; banco: "ok" | "indisponivel"; versao: string };

export type Faceta = { valor: string; rotulo: string; n: number };
export type Facetas = Record<string, Faceta[]>;

export type ConjuntoResumo = {
  id: string;
  titulo: string;
  resumo: string | null;
  organizacao_slug: string | null;
  organizacao_titulo: string | null;
  esfera: string | null;
  uf: string | null;
  temas: string[];
  formatos: string[];
  tags: string[];
  licenca: string | null;
  periodicidade: string | null;
  nota_qualidade: number | string | null;
  prioridade: number | string | null;
  estado_curadoria: string;
  curado: boolean;
  selo_portal: string | null;
  sem_detalhe: boolean;
  removido: boolean;
  qtd_recursos: number;
  metadados_atualizados_em: string | null;
};

export type Busca = {
  total: number;
  pagina: number;
  tamanho: number;
  aproximada: boolean;
  itens: ConjuntoResumo[];
  facetas: Facetas;
};

export type Efetivo = {
  titulo: string;
  descricao: string | null;
  licenca: string | null;
  periodicidade: string | null;
  tags: string[];
  temas: string[];
};

export type Recurso = {
  id: string;
  titulo: string | null;
  descricao: string | null;
  formato: string | null;
  link: string | null;
  tamanho: number | null;
  downloads: number | null;
};

export type RegraDetalhe = {
  regra: string;
  nome: string;
  dimensao: string;
  peso: number;
  ativa: boolean;
  avaliavel: boolean;
  passou: boolean | null;
  mensagem: string;
};

export type Alteracao = {
  id: number;
  campo: string;
  valor: unknown;
  origem: string;
  autor: string;
  comentario: string | null;
  em: string;
  proposta_id: number | null;
};

export type ConjuntoDetalhe = {
  id: string;
  slug: string | null;
  link_portal: string | null;
  sem_detalhe: boolean;
  removido_em: string | null;
  efetivo: Efetivo | null;
  original: Efetivo;
  organizacao: { slug: string | null; titulo: string | null; esfera: string | null; uf: string | null; municipio: string | null };
  portal: Record<string, string | number | boolean | null>;
  recursos: Recurso[];
  associados: string[];
  estado_curadoria: string;
  alteracoes: Alteracao[];
  propostas_pendentes: number;
  colecoes: { id: number; nome: string }[];
  qualidade: { nota: number; dimensoes: Record<string, number>; detalhes: RegraDetalhe[]; calculada_em: string } | null;
  historico: { evento: string; em: string; execucao_id: number }[];
};

export type Tema = { slug: string; titulo: string; conjuntos: number };

export type Extracao = {
  id: number;
  tipo: string;
  estado: string;
  forcada: boolean;
  solicitada_por: string | null;
  criada_em: string;
  iniciada_em: string | null;
  finalizada_em: string | null;
  cancelamento_solicitado: boolean;
  totais: Record<string, unknown>;
  erro: string | null;
};
export type Disponibilidade = { pode_pedir: boolean; motivo: string | null; disponivel_em: string | null };
export type EstadoExtracao = {
  ativa: Extracao | null;
  incremental: Disponibilidade;
  completa: Disponibilidade;
  ultima_completa_em: string | null;
  dias_desde_ultima_completa: number | null;
  sugerir_completa: boolean;
};

export type Colecao = {
  id: number;
  nome: string;
  descricao: string | null;
  responsavel: string | null;
  tipo: "manual" | "dinamica";
  regra_filtro: Record<string, unknown>;
  conjuntos: number;
  diff: { entraram: string[]; sairam: string[] } | null;
};

export type LlmEstado = {
  habilitado: boolean;
  motivo: string | null;
  externo: boolean;
  simulado: boolean;
  provedor: string | null;
  modelo: string | null;
  host?: string | null;
  limite_por_execucao: number;
};
export type LlmTarefa = { chave: string; nome: string; descricao: string; campo_alvo: string };
export type LlmExecucao = {
  id: number;
  tarefa_chave: string;
  estado: string;
  conjuntos: number;
  provedor: string | null;
  modelo: string | null;
  externo: boolean | null;
  criada_em: string;
  finalizada_em: string | null;
  totais: Record<string, number>;
  erro: string | null;
  pendentes: number;
};
export type LlmProposta = {
  id: number;
  execucao_id: number;
  conjunto_id: string;
  conjunto_titulo: string | null;
  campo: string;
  valor_original: unknown;
  valor_proposto: unknown;
  valor_final: unknown;
  estado: string;
  erro: string | null;
  provedor: string | null;
  modelo: string | null;
  externo: boolean | null;
  tarefa_chave: string;
};

export type Regra = {
  chave: string;
  dimensao: string;
  framework: string;
  nome: string;
  descricao: string;
  peso: number;
  fonte: string;
  ativa: boolean;
};

export type Interpretacao = {
  filtros: Record<string, string | number | boolean>;
  explicacao: string;
  ignorados: string[];
  organizacao: { slug: string; titulo: string } | null;
};
export type RespostaChat = Interpretacao & {
  pergunta: string;
  filtros_removidos: string[];
  provedor: { nome: string; modelo: string; externo: boolean; simulado: boolean };
  resultado: Omit<Busca, "facetas">;
};
export type PropostaColecao = Interpretacao & {
  nome_sugerido: string;
  provedor: { nome: string; externo: boolean; simulado: boolean };
  resultado: Omit<Busca, "facetas">;
};
