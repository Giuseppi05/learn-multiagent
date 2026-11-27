"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { errorMessage, post } from "@/lib/api";
import { HOME_BY_ROLE, useAuth } from "@/lib/auth";
import { btnPrimary, ErrorBox, input, label, Spinner } from "@/lib/ui";

export default function ChangePassword() {
  const { me, refresh } = useAuth();
  const router = useRouter();
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (me === null) router.replace("/login");
    else if (me && !me.user.must_change_password) router.replace(HOME_BY_ROLE[me.user.role]);
  }, [me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pw.length < 8) return setErr("Usa al menos 8 caracteres.");
    if (pw !== pw2) return setErr("Las contraseñas no coinciden.");
    setBusy(true);
    setErr("");
    try {
      await post("/me/password", { password: pw });
      await refresh();
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  }

  if (!me) return <Spinner label="Cargando…" />;
  return (
    <main className="grid min-h-screen place-items-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h1 className="font-display text-2xl font-bold">Crea tu contraseña</h1>
        <p className="text-sm text-slate-500">Hola, {me.user.full_name}. Ingresaste con una contraseña temporal; elige una propia para continuar.</p>
        <div>
          <label className={label} htmlFor="pw">
            Nueva contraseña
          </label>
          <input id="pw" type="password" className={`${input} mt-1`} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" minLength={8} required />
        </div>
        <div>
          <label className={label} htmlFor="pw2">
            Repítela
          </label>
          <input id="pw2" type="password" className={`${input} mt-1`} value={pw2} onChange={(e) => setPw2(e.target.value)} autoComplete="new-password" required />
        </div>
        {err && <ErrorBox message={err} />}
        <button className={`${btnPrimary} w-full`} disabled={busy}>
          {busy ? "Guardando…" : "Guardar y continuar"}
        </button>
      </form>
    </main>
  );
}
