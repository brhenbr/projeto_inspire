import type { ReactNode } from "react";

import { ESTADOS_CURADORIA, fmtNum, nota, toneOfNota } from "./format";

export function Badge({ tone = "neutro", children, title }: { tone?: string; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}

export function Nota({ value }: { value: number | string | null | undefined }) {
  const n = nota(value);
  return (
    <Badge tone={toneOfNota(n)} title="Nota de qualidade dos metadados (0 a 100)">
      {n === null ? "sem nota" : `Nota ${n.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}`}
    </Badge>
  );
}

export function EstadoCuradoria({ value }: { value: string }) {
  const tone = { aprovado: "bom", em_revisao: "medio", rejeitado: "ruim", duplicado: "ruim" }[value] ?? "neutro";
  return <Badge tone={tone}>{ESTADOS_CURADORIA[value] ?? value}</Badge>;
}

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="cartao">
      {(title || actions) && (
        <header className="cartao-topo">
          {title && <h2>{title}</h2>}
          {actions && <div className="acoes">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Loading({ text = "Carregando…" }: { text?: string }) {
  return (
    <p className="carregando" role="status">
      {text}
    </p>
  );
}

export function ErrorBox({ error, onRetry }: { error: Error | string | null | undefined; onRetry?: () => void }) {
  if (!error) return null;
  return (
    <div className="erro" role="alert">
      <span>{typeof error === "string" ? error : error.message}</span>
      {onRetry && (
        <button type="button" className="botao botao-sec" onClick={onRetry}>
          Tentar de novo
        </button>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="vazio">{children}</p>;
}

export function Pagination({
  page,
  total,
  size,
  onChange,
}: {
  page: number;
  total: number;
  size: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav className="paginacao" aria-label="Paginação">
      <button type="button" className="botao botao-sec" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Anterior
      </button>
      <span>
        Página {fmtNum(page)} de {fmtNum(pages)}
      </span>
      <button type="button" className="botao botao-sec" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Próxima →
      </button>
    </nav>
  );
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: T; label: string }[];
  active: T;
  onChange: (key: T) => void;
}) {
  return (
    <div className="abas" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          role="tab"
          aria-selected={t.key === active}
          className={t.key === active ? "aba ativa" : "aba"}
          onClick={() => onChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Bar({ value, max = 100, tone }: { value: number; max?: number; tone?: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="barra" role="img" aria-label={`${pct}%`}>
      <div className={`barra-preench ${tone ? `barra-${tone}` : ""}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Kpi({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="kpi">
      <div className="kpi-valor">{value}</div>
      <div className="kpi-rotulo">{label}</div>
      {hint && <div className="kpi-dica">{hint}</div>}
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="campo">
      <span className="campo-rotulo">{label}</span>
      {children}
      {hint && <span className="campo-dica">{hint}</span>}
    </label>
  );
}
