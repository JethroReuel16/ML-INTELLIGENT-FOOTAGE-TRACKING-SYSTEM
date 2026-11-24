"use client";

import { useCallback, useEffect, useState } from "react";

interface ResourceState<T> {
  data: T | undefined;
  error: string;
  loading: boolean;
}

/**
 * Loads data on mount (and whenever `fetcher` changes), ignoring stale
 * responses. `fetcher` must be stable — wrap it in useCallback.
 *
 * `loading` is true during the first load and during `reload()`; previously
 * loaded `data` is kept while reloading so lists don't flash empty.
 */
export function useResource<T>(fetcher: () => Promise<T>, enabled = true) {
  const [state, setState] = useState<ResourceState<T>>({
    data: undefined,
    error: "",
    loading: enabled,
  });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!enabled) return;

    let alive = true;

    fetcher()
      .then((data) => {
        if (alive) setState({ data, error: "", loading: false });
      })
      .catch((err: unknown) => {
        if (alive)
          setState((s) => ({
            ...s,
            error: err instanceof Error ? err.message : "Something went wrong while loading.",
            loading: false,
          }));
      });

    return () => {
      alive = false;
    };
  }, [fetcher, enabled, version]);

  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    setVersion((v) => v + 1);
  }, []);

  return { ...state, reload };
}
