"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { CredentialModal } from "@/components/CredentialModal";
import { type ClassroomDashboard, errorMessage, post, type StudentInfo } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { btnPrimary, Card, Chip, Empty, ErrorBox, formatDate, input, Kpi, label, LightDot, Notice, PageHeader, Spinner, TrafficLight } from "@/lib/ui";

const ALERT_STYLE = { concepto: "bg-rose-50 text-rose-800", tiempo: "bg-amber-50 text-amber-800", indecision: "bg-violet-50 text-violet-800" };
const ALERT_LABEL = { concepto: "Error de concepto", tiempo: "Tiempo excesivo", indecision: "Indecisión" };

function AddStudent({ roomId, onDone }: { roomId: string; onDone: () => void }) {
  const [form, setForm] = useState({ full_name: "", username: "", interests: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [cred, setCred] = useState<{ who: string; login: string; secret: string } | null>(null);

  function suggest(name: string) {
    // Sugerencia de usuario: primer nombre + inicial del apellido, sin tildes
    const parts = name
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z\s]/g, "")
      .split(/\s+/)
      .filter(Boolean);
    return parts.length >= 2 ? `${parts[0]}.${parts[1][0]}` : (parts[0] ?? "");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const r = await post<{ student: StudentInfo; pin: string }>(`/classrooms/${roomId}/students`, form);
      setCred({ who: r.student.full_name, login: r.student.username, secret: r.pin });
      setForm({ full_name: "", username: "", interests: "" });
      onDone();
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Registrar estudiante">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className={label} htmlFor="fn">
            Nombre completo
          </label>
          <input
            id="fn"
            className={`${input} mt-1`}
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value, username: form.username || "" })}
            onBlur={() => !form.username && setForm((f) => ({ ...f, username: suggest(f.full_name) }))}
            required
            minLength={3}
          />
          <p className="mt-1 text-xs text-slate-500">Solo lo ves tú. A la IA le llega un código interno, nunca el nombre.</p>
        </div>
        <div>
          <label className={label} htmlFor="un">
            Usuario para ingresar
          </label>
          <input id="un" className={`${input} mt-1 font-mono`} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase() })} required pattern="[a-z0-9][a-z0-9._\-]{2,29}" />
        </div>
        <div>
          <label className={label} htmlFor="it">
            Intereses
          </label>
          <input id="it" className={`${input} mt-1`} placeholder="fútbol, dibujo, animales" value={form.interests} onChange={(e) => setForm({ ...form, interests: e.target.value })} />
        </div>
        {err && <ErrorBox message={err} />}
        <button className={`${btnPrimary} w-full`} disabled={busy}>
          {busy ? "Creando cuenta…" : "Registrar y generar PIN"}
        </button>
      </form>
      <CredentialModal open={!!cred} onClose={() => setCred(null)} title="Cuenta del estudiante" who={cred?.who ?? ""} login={cred?.login ?? ""} secret={cred?.secret ?? ""} secretLabel="PIN" />
    </Card>
  );
}

export default function ClassroomPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const { data, error, reload } = useApi<ClassroomDashboard>(`/classrooms/${id}/dashboard`);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Cargando el aula…" />;
  const k = data.kpis;
  const isTeacher = me?.user.role === "docente";
  const withoutProfile = data.students.filter((s) => !s.has_profile).length;

  return (
    <div className="space-y-5">
      <PageHeader
        title={`Aula ${data.classroom.name}`}
        subtitle={`${data.classroom.year} · ${data.classroom.teacher?.full_name ?? "sin docente"} · Semáforo y alertas de la Sección 17`}
        actions={
          isTeacher && k.to_review > 0 ? (
            <Link href="/docente/validacion" className={btnPrimary}>
              {k.to_review} por validar
            </Link>
          ) : undefined
        }
      />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi value={k.students} label="estudiantes" />
        <Kpi value={k.answers} label="respuestas" />
        <Kpi value={k.accuracy === null ? "—" : `${Math.round(k.accuracy * 100)} %`} label="acierto del aula" />
        <Kpi value={k.avg_time_s === null ? "—" : `${k.avg_time_s} s`} label="tiempo promedio" />
      </div>
      {withoutProfile > 0 && isTeacher && (
        <Notice tone="warn">
          {withoutProfile} estudiante(s) todavía no tienen perfil de aprendizaje. Entra a cada uno y aplica la prueba inicial para que los agentes puedan personalizar su material.
        </Notice>
      )}
      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        <div className="space-y-5">
          <Card title="Estudiantes">
            {data.students.length === 0 ? (
              <Empty>Registra a tus estudiantes con el formulario de la derecha.</Empty>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="py-2">Estudiante</th>
                      <th>Acierto</th>
                      <th>Por tema</th>
                      <th>Última categoría</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.students.map((s) => (
                      <tr key={s.id}>
                        <td className="py-2">
                          <Link href={`/docente/estudiantes/${s.id}`} className="font-semibold text-indigo-700 hover:underline">
                            {s.full_name}
                          </Link>
                          <div className="font-mono text-xs text-slate-400">
                            {s.username} · {s.code}
                          </div>
                        </td>
                        <td>{s.answers ? <TrafficLight light={s.light} accuracy={s.accuracy} /> : <Chip className="bg-slate-100 text-slate-600">{s.has_profile ? "Sin respuestas" : "Sin perfil"}</Chip>}</td>
                        <td>
                          <div className="flex flex-wrap gap-2">
                            {s.topics.map((t) => (
                              <span key={t.topic} className="inline-flex items-center gap-1 text-xs text-slate-600">
                                <LightDot light={t.light} title={`${Math.round(t.accuracy * 100)} %`} />
                                {t.topic}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="text-slate-600">{s.last_category ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
          <Card title="Respuestas por entorno">
            <div className="grid grid-cols-5 gap-2 text-center">
              {Object.entries(data.by_environment).map(([env, n]) => (
                <div key={env} className="rounded-xl bg-slate-50 p-3">
                  <div className="font-display text-xl font-bold tabular-nums">{n}</div>
                  <div className="text-xs font-semibold text-slate-500">{env === "mando" ? "Mando" : env}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
        <div className="space-y-5">
          {isTeacher && <AddStudent roomId={id} onDone={reload} />}
          <Card title="Alertas">
            {data.alerts.length === 0 ? (
              <Empty>Sin alertas por ahora.</Empty>
            ) : (
              <ul className="space-y-2">
                {data.alerts.map((a, i) => (
                  <li key={i} className={`rounded-xl p-3 text-sm ${ALERT_STYLE[a.type]}`}>
                    <div className="flex justify-between gap-2 text-xs font-semibold uppercase">
                      <span>{ALERT_LABEL[a.type]}</span>
                      <span className="font-normal normal-case opacity-70">{formatDate(a.created_at)}</span>
                    </div>
                    <Link href={`/docente/estudiantes/${a.student_id}`} className="font-semibold hover:underline">
                      {a.student}
                    </Link>{" "}
                    · {a.topic}
                    <div>{a.detail}</div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
