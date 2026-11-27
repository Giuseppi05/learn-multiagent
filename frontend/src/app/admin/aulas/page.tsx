"use client";

import { useState } from "react";
import { type AppUser, type Classroom, errorMessage, patch, post } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { btnPrimary, Card, Empty, ErrorBox, input, label, PageHeader, Spinner } from "@/lib/ui";

export default function Classrooms() {
  const rooms = useApi<Classroom[]>("/admin/classrooms");
  const teachers = useApi<AppUser[]>("/admin/teachers");
  const [form, setForm] = useState({ year: new Date().getFullYear(), grade: 3, section: "A", teacher_id: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await post("/admin/classrooms", { ...form, teacher_id: form.teacher_id || null });
      rooms.reload();
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  }

  async function assign(id: number, teacher_id: string) {
    setErr("");
    try {
      await patch(`/admin/classrooms/${id}`, { teacher_id: teacher_id || null });
      rooms.reload();
    } catch (e2) {
      setErr(errorMessage(e2));
    }
  }

  if (rooms.error || teachers.error) return <ErrorBox message={rooms.error || teachers.error} />;
  if (!rooms.data || !teachers.data) return <Spinner label="Cargando aulas…" />;
  const active = teachers.data.filter((t) => t.active);
  return (
    <div className="space-y-5">
      <PageHeader title="Aulas" subtitle="Cada aula tiene un docente responsable; solo él ve y gestiona a sus estudiantes." />
      {err && <ErrorBox message={err} />}
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Card title={`Aulas (${rooms.data.length})`}>
          {rooms.data.length === 0 ? (
            <Empty>Crea la primera aula con el formulario.</Empty>
          ) : (
            <ul className="divide-y">
              {rooms.data.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="font-semibold">
                    {r.name} <span className="text-sm font-normal text-slate-500">· {r.year}</span>
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <span className="text-slate-500">Docente</span>
                    <select className={`${input} w-56`} value={r.teacher?.id ?? ""} onChange={(e) => assign(r.id, e.target.value)}>
                      <option value="">Sin asignar</option>
                      {active.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.full_name}
                        </option>
                      ))}
                    </select>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Nueva aula">
          <form onSubmit={create} className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className={label} htmlFor="year">
                  Año
                </label>
                <input id="year" type="number" className={`${input} mt-1`} value={form.year} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })} />
              </div>
              <div>
                <label className={label} htmlFor="grade">
                  Grado
                </label>
                <select id="grade" className={`${input} mt-1`} value={form.grade} onChange={(e) => setForm({ ...form, grade: Number(e.target.value) })}>
                  {[1, 2, 3, 4, 5, 6].map((g) => (
                    <option key={g} value={g}>
                      {g}.º
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={label} htmlFor="section">
                  Sección
                </label>
                <input id="section" className={`${input} mt-1`} value={form.section} maxLength={5} onChange={(e) => setForm({ ...form, section: e.target.value })} />
              </div>
            </div>
            <div>
              <label className={label} htmlFor="teacher">
                Docente
              </label>
              <select id="teacher" className={`${input} mt-1`} value={form.teacher_id} onChange={(e) => setForm({ ...form, teacher_id: e.target.value })}>
                <option value="">Asignar después</option>
                {active.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.full_name}
                  </option>
                ))}
              </select>
            </div>
            <button className={`${btnPrimary} w-full`} disabled={busy}>
              {busy ? "Creando…" : "Crear aula"}
            </button>
          </form>
        </Card>
      </div>
    </div>
  );
}
