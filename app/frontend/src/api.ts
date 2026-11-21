export type Saude = {
  status: "ok" | "degradado";
  banco: "ok" | "indisponivel";
  versao: string;
};

/** Consulta a saúde da API. A API publicada em /api é servida pelo nginx do contêiner web. */
export async function fetchSaude(signal?: AbortSignal): Promise<Saude> {
  const response = await fetch("/api/v1/saude", { signal });
  // 503 também traz um corpo válido (status "degradado"), então só falha em erros inesperados.
  if (!response.ok && response.status !== 503) {
    throw new Error(`Falha ao consultar a API (HTTP ${response.status})`);
  }
  return (await response.json()) as Saude;
}
