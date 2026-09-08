"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "./api";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => void;
}

/** Small data-fetching hook with loading/error/refresh. */
export function useApiData<T>(path: string | null, deps: unknown[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  const [tick, setTick] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api<T>(path)
      .then((result) => {
        if (mounted.current) setData(result);
      })
      .catch((err: ApiError | Error) => {
        if (mounted.current) setError(err.message);
      })
      .finally(() => {
        if (mounted.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, refresh };
}

export function useDebounced<T>(value: T, delay = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
