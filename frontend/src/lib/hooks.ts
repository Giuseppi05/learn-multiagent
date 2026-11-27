"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "./api";

/** Carga un recurso de la API con estado de error y recarga manual. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    if (!path) return;
    try {
      setData(await api<T>(path));
      setError("");
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [path]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { data, error, reload, setData };
}

/**
 * Repite `fn` cada `ms` mientras `active` sea verdadero.
 * Los agentes trabajan en segundo plano: así la pantalla se actualiza sola cuando terminan.
 */
export function usePolling(fn: () => void, active: boolean, ms = 2500) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => saved.current(), ms);
    return () => clearInterval(id);
  }, [active, ms]);
}
