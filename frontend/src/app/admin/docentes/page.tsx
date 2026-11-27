"use client";

import { useState } from "react";
import { type AppUser, errorMessage, post } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { CredentialModal } from "@/components/CredentialModal";
import { btnDanger, btnGhost, btnPrimary, Card, Chip, Empty, ErrorBox, input, label, PageHeader, Spinner } from "@/lib/ui";

type Teacher = AppUser & { classrooms: string[] };

export default function Teachers() {
  const { data, error, reload } = useApi<Teacher[]>("/admin/teachers");
  const [form, setForm] = useState({ full_name: "", email: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [cred, setCred] = useState<{ who: string; login: string; secret: string } | null>(null);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const r = await post<{ teacher: AppUser; temporary_password: string }>("/admin/teachers", form);
      setCred({ who: r.teacher.full_name, login: r.teacher.email, secret: r.temporary_password });
      setForm({ full_name: "", email: "" });
      reload();
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  }

  async function action(t: Teacher, kind: "reset" | "toggle") {
    setErr("");
    try {
      if (kind === "reset") {
        const r = await post<{ temporary_password: string }>(`/admin/teachers/${t.id}/reset-password`);
        setCred({ who: t.full_name, login: t.email, secret: r.temporary_password });
      } else {
        await post(`/admin/teachers/${t.id}/active?active=${!t.active}`);
      }
      reload();
    } catch (e2) {
      setErr(errorMessage(e2));
    }
  }

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Cargando docentes…" />;
  return (
    <div className="space-y-5">
      <PageHeader title="Docentes" subtitle="Crea las cuentas del personal docente. Cada uno elige su contraseña en el primer ingreso." />
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Card title={`Cuentas (${data.length})`}>
          {data.length === 0 ? (
            <Empty>Aún no hay docentes registrados.</Empty>
          ) : (
            <ul className="divide-y">
              {data.map((t) => (
                <li key={t.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div>
                    <div className="font-semibold">
                      {t.full_name} {!t.active && <Chip className="bg-slate-200 text-slate-600">Desactivado</Chip>}
                      {t.must_change_password && t.active && <Chip className="ml-1 bg-amber-100 text-amber-800">Aún no ingresa</Chip>}
                    </div>
                    <div className="text-sm text-slate-500">
                      {t.email} · {t.classrooms.length ? t.classrooms.join(", ") : "sin aula asignada"}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button className={btnGhost} onClick={() => action(t, "reset")} disabled={!t.active}>
                      Contraseña temporal
                    </button>
                    <button className={t.active ? btnDanger : btnGhost} onClick={() => action(t, "toggle")}>
                      {t.active ? "Desactivar" : "Reactivar"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Nuevo docente">
          <form onSubmit={create} className="space-y-3">
            <div>
              <label className={label} htmlFor="name">
                Nombre completo
              </label>
              <input id="name" className={`${input} mt-1`} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required minLength={3} />
            </div>
            <div>
              <label className={label} htmlFor="email">
                Correo institucional
              </label>
              <input id="email" type="email" className={`${input} mt-1`} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
            {err && <ErrorBox message={err} />}
            <button className={`${btnPrimary} w-full`} disabled={busy}>
              {busy ? "Creando…" : "Crear cuenta"}
            </button>
          </form>
        </Card>
      </div>
      <CredentialModal open={!!cred} onClose={() => setCred(null)} title="Cuenta lista" who={cred?.who ?? ""} login={cred?.login ?? ""} secret={cred?.secret ?? ""} secretLabel="Contraseña temporal" />
    </div>
  );
}
