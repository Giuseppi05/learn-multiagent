"use client";

import type { Session } from "@supabase/supabase-js";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, type Me, type Role } from "./api";
import { loginEmail, supabase } from "./supabase";

interface AuthState {
  /** undefined mientras se consulta la sesión guardada; null si no hay sesión */
  me: Me | null | undefined;
  error: string;
  signIn: (identifier: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export const HOME_BY_ROLE: Record<Role, string> = { admin: "/admin", docente: "/docente", estudiante: "/estudiante" };

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [error, setError] = useState("");
  const loadedUser = useRef<string | null>(null);

  const loadMe = useCallback(async (session: Session | null) => {
    if (!session) {
      setMe(null);
      return;
    }
    loadedUser.current = session.user.id;
    try {
      setMe(await api<Me>("/me"));
      setError("");
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        // Sesión válida en Supabase pero sin cuenta habilitada en el sistema: se cierra para no quedar a medias
        setError(e.message);
        await supabase().auth.signOut();
      } else {
        // Si la API no responde se conserva la sesión: basta con reintentar cuando vuelva
        setError("No se pudo conectar con el servidor del sistema. Inténtalo de nuevo en un momento.");
      }
      loadedUser.current = null;
      setMe(null);
    }
  }, []);

  useEffect(() => {
    const sb = supabase();
    sb.auth.getSession().then(({ data }) => loadMe(data.session));
    const { data } = sb.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        loadedUser.current = null;
        setMe(null);
      }
      // Supabase repite SIGNED_IN cada vez que la pestaña recupera el foco: solo se recarga si cambió el usuario
      if (event === "SIGNED_IN" && session?.user.id !== loadedUser.current) loadMe(session);
    });
    return () => data.subscription.unsubscribe();
  }, [loadMe]);

  const value = useMemo<AuthState>(
    () => ({
      me,
      error,
      async signIn(identifier, password) {
        setError("");
        const { data, error: err } = await supabase().auth.signInWithPassword({ email: loginEmail(identifier), password });
        if (err) throw new Error(err.message === "Invalid login credentials" ? "Usuario o contraseña incorrectos" : err.message);
        await loadMe(data.session);
      },
      async signOut() {
        await supabase().auth.signOut();
        setMe(null);
      },
      async refresh() {
        const { data } = await supabase().auth.getSession();
        await loadMe(data.session);
      },
    }),
    [me, error, loadMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
