export const ESTADOS_CURADORIA: Record<string, string> = {
  pendente: "Pendente",
  em_revisao: "Em revisão",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
  duplicado: "Duplicado",
};

export const ESTADOS_EXECUCAO: Record<string, string> = {
  enfileirada: "Na fila",
  em_andamento: "Em andamento",
  pausada: "Pausada",
  concluida: "Concluída",
  concluida_com_divergencias: "Concluída com divergências",
  falhou: "Falhou",
  cancelada: "Cancelada",
};

export const ESTADOS_PROPOSTA: Record<string, string> = {
  pendente: "Aguardando revisão",
  aprovada: "Aprovada",
  editada: "Editada e aplicada",
  rejeitada: "Rejeitada",
  desatualizada: "Desatualizada",
  erro: "Erro",
};

export const CAMPOS: Record<string, string> = {
  titulo: "Título",
  descricao: "Descrição",
  tags: "Palavras-chave",
  temas: "Temas",
  periodicidade: "Periodicidade",
  licenca: "Licença",
};

export const ESFERAS: Record<string, string> = { federal: "Federal", estadual: "Estadual", municipal: "Municipal" };

export function fmtDate(value: string | null | undefined, withTime = false): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("pt-BR", withTime ? { dateStyle: "short", timeStyle: "short" } : { dateStyle: "short" });
}

export const fmtNum = (n: number | string | null | undefined): string =>
  n === null || n === undefined ? "—" : Number(n).toLocaleString("pt-BR");

export function nota(value: number | string | null | undefined): number | null {
  return value === null || value === undefined ? null : Number(value);
}

export function toneOfNota(value: number | null): "bom" | "medio" | "ruim" | "neutro" {
  if (value === null) return "neutro";
  if (value >= 70) return "bom";
  if (value >= 40) return "medio";
  return "ruim";
}

export function fmtValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "(vazio)";
  return Array.isArray(value) ? value.join(", ") : String(value);
}

export function minutesUntil(iso: string | null): number | null {
  if (!iso) return null;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 60000));
}
