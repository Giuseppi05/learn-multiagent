import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

/** Cliente de Supabase solo para autenticación: los datos se leen siempre a través de la API (Orquestador). */
export function supabase(): SupabaseClient {
  if (!client) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    if (!url || !key) throw new Error("Faltan NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY en .env.local");
    client = createClient(url, key, { auth: { persistSession: true, autoRefreshToken: true } });
  }
  return client;
}

/** Los estudiantes no tienen correo: su usuario se traduce al correo interno que creó el backend. */
export function loginEmail(identifier: string): string {
  const id = identifier.trim().toLowerCase();
  if (id.includes("@")) return id;
  return `${id}@${process.env.NEXT_PUBLIC_STUDENT_EMAIL_DOMAIN ?? "estudiantes.aprende.invalid"}`;
}
