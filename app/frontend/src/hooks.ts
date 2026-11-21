import { useCallback, useEffect, useRef, useState } from "react";

type State<T> = { key: string; data?: T; error?: Error };

/**
 * Busca dados quando `deps` mudam. `loading` é derivado da chave (sem setState síncrono em efeito).
 * `reload()` força uma nova busca; `refreshMs` repete a busca de tempos em tempos (acompanhar progresso).
 */
export function useApi<T>(fn: () => Promise<T>, deps: readonly unknown[], refreshMs?: number) {
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<State<T>>({ key: "" });
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });
  const key = JSON.stringify(deps) + ":" + tick;

  useEffect(() => {
    let alive = true;
    fnRef
      .current()
      .then((data) => alive && setState({ key, data }))
      .catch((error: unknown) => alive && setState({ key, error: error instanceof Error ? error : new Error(String(error)) }));
    return () => {
      alive = false;
    };
  }, [key]);

  useEffect(() => {
    if (!refreshMs) return;
    const id = setInterval(() => setTick((t) => t + 1), refreshMs);
    return () => clearInterval(id);
  }, [refreshMs]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  const loading = state.key !== key;
  // Mantém o dado anterior enquanto recarrega, para a tela não piscar.
  return { data: state.data, error: loading ? undefined : state.error, loading: loading && state.data === undefined, refreshing: loading, reload };
}

/** Executa uma ação (botão) com estado de "em andamento" e erro legível. */
export function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async <R,>(action: () => Promise<R>): Promise<R | undefined> => {
    setPending(true);
    setError(null);
    try {
      return await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return undefined;
    } finally {
      setPending(false);
    }
  }, []);
  return { pending, error, run, clearError: () => setError(null) };
}
