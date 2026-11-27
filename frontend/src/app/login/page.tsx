"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { HOME_BY_ROLE, useAuth } from "@/lib/auth";
import { btnPrimary, ErrorBox, input, label, Spinner } from "@/lib/ui";

type Mode = "estudiante" | "personal";

function PinPad({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "borrar", "0", "listo"];
  return (
    <div>
      <div className="mb-3 flex justify-center gap-2" aria-label={`PIN, ${value.length} de 6 dígitos`}>
        {Array.from({ length: 6 }, (_, i) => (
          <span key={i} className={`grid h-12 w-10 place-items-center rounded-xl border-2 text-2xl ${i < value.length ? "border-indigo-500 bg-indigo-50" : "border-slate-200"}`}>
            {i < value.length ? "●" : ""}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {keys.map((k) =>
          k === "listo" ? (
            <button key={k} type="submit" className="rounded-xl bg-emerald-500 py-3 text-lg font-bold text-white hover:bg-emerald-600 disabled:opacity-50" disabled={value.length !== 6}>
              Entrar
            </button>
          ) : (
            <button
              key={k}
              type="button"
              className="rounded-xl bg-white py-3 font-display text-2xl font-semibold text-slate-800 shadow-sm ring-1 ring-slate-200 hover:bg-amber-50"
              onClick={() => onChange(k === "borrar" ? value.slice(0, -1) : (value + k).slice(0, 6))}
              aria-label={k === "borrar" ? "Borrar último dígito" : k}
            >
              {k === "borrar" ? "⌫" : k}
            </button>
          ),
        )}
      </div>
    </div>
  );
}

function LoginForm() {
  const { me, signIn, error: authError } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [mode, setMode] = useState<Mode>("estudiante");
  const [id, setId] = useState("");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!me) return;
    const next = params.get("next");
    router.replace(me.user.must_change_password ? "/cambiar-clave" : next && next.startsWith("/") ? next : HOME_BY_ROLE[me.user.role]);
  }, [me, router, params]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!id.trim() || !secret) return;
    if (mode === "estudiante" && id.includes("@")) {
      setErr("Escribe tu usuario, no un correo. Si eres docente, usa la pestaña «Docente o coordinación».");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await signIn(id, secret);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "No se pudo iniciar sesión");
      setSecret("");
    } finally {
      setBusy(false);
    }
  }

  if (me === undefined) return <Spinner label="Cargando…" />;

  return (
    <div className="w-full max-w-md space-y-5">
      <div className="text-center">
        <h1 className="font-display text-3xl font-bold text-indigo-700">
          Aprende <span className="text-amber-500">Multiagente</span>
        </h1>
        <p className="mt-1 text-sm text-slate-500">Contenido pedagógico personalizado para primaria</p>
      </div>
      <div className="grid grid-cols-2 rounded-2xl bg-slate-100 p-1 text-sm font-semibold" role="tablist">
        {(["estudiante", "personal"] as Mode[]).map((m) => (
          <button
            key={m}
            role="tab"
            aria-selected={mode === m}
            className={`rounded-xl py-2 ${mode === m ? "bg-white text-indigo-700 shadow-sm" : "text-slate-500"}`}
            onClick={() => {
              setMode(m);
              setSecret("");
              setErr("");
            }}
          >
            {m === "estudiante" ? "Soy estudiante" : "Docente o coordinación"}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className={`space-y-4 rounded-3xl p-6 shadow-sm ${mode === "estudiante" ? "bg-amber-50 ring-1 ring-amber-200" : "bg-white ring-1 ring-slate-200"}`}>
        <div>
          <label className={label} htmlFor="id">
            {mode === "estudiante" ? "Tu usuario" : "Correo"}
          </label>
          <input
            id="id"
            className={`${input} mt-1 ${mode === "estudiante" ? "py-3 text-lg" : ""}`}
            value={id}
            onChange={(e) => setId(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            type={mode === "estudiante" ? "text" : "email"}
            placeholder={mode === "estudiante" ? "por ejemplo: lucia.r" : "nombre@institucion.edu.pe"}
            required
          />
        </div>
        {mode === "estudiante" ? (
          <div>
            <span className={label}>Tu PIN secreto</span>
            <div className="mt-2">
              <PinPad value={secret} onChange={setSecret} />
            </div>
          </div>
        ) : (
          <div>
            <label className={label} htmlFor="pw">
              Contraseña
            </label>
            <input id="pw" className={`${input} mt-1`} type="password" value={secret} onChange={(e) => setSecret(e.target.value)} autoComplete="current-password" required />
          </div>
        )}
        {(err || authError) && <ErrorBox message={err || authError} />}
        {mode === "personal" && (
          <button className={`${btnPrimary} w-full`} disabled={busy}>
            {busy ? "Ingresando…" : "Ingresar"}
          </button>
        )}
        {mode === "estudiante" && busy && <Spinner label="Entrando…" />}
        <p className="text-center text-xs text-slate-500">
          {mode === "estudiante" ? "¿Olvidaste tu PIN? Pídele uno nuevo a tu profesora o profesor." : "¿Olvidaste tu contraseña? La coordinación puede darte una temporal."}
        </p>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-gradient-to-b from-indigo-50 to-slate-50 px-4 py-10">
      <Suspense fallback={<Spinner label="Cargando…" />}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
