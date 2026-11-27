"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { CredentialModal } from "@/components/CredentialModal";
import { ProgressCharts } from "@/components/ProgressCharts";
import { AREAS, errorMessage, patch, post, type ProgressPoint, type StudentDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi, usePolling } from "@/lib/hooks";
import { btnGhost, btnPrimary, Card, CategoryChip, Chip, Empty, ErrorBox, formatDate, input, label, LEVEL, Notice, PageHeader, Spinner, StatusChip, TrafficLight } from "@/lib/ui";

const SOURCE = { prueba_inicial: "prueba inicial", docente: "diagnóstico del docente", orquestador: "Orquestador" } as Record<string, string>;

export default function StudentPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const isTeacher = me?.user.role === "docente";
  const { data: d, error, reload } = useApi<StudentDetail>(`/students/${id}`);
  const progress = useApi<ProgressPoint[]>(`/students/${id}/progress`);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<{ tone: "ok" | "err"; text: string } | null>(null);
  const [area, setArea] = useState<(typeof AREAS)[number]>("Matemática");
  const [gen, setGen] = useState({ topic: "", difficulty: 2 });
  const [notes, setNotes] = useState({ teacher_notes: "", external_test: "" });
  const [interests, setInterests] = useState<string | null>(null);
  const [pin, setPin] = useState("");

  // Mientras algún agente trabaja, la ficha se actualiza sola
  const working = !!d && (d.contents.some((c) => c.status === "generando") || d.reports.some((r) => r.status === "generando"));
  usePolling(reload, working);

  async function run(key: string, fn: () => Promise<string>) {
    setBusy(key);
    setMsg(null);
    try {
      setMsg({ tone: "ok", text: await fn() });
      reload();
      progress.reload();
    } catch (e) {
      setMsg({ tone: "err", text: errorMessage(e) });
    } finally {
      setBusy("");
    }
  }

  if (error) return <ErrorBox message={error} />;
  if (!d) return <Spinner label="Cargando estudiante…" />;
  const st = d.student;
  const p = d.profile;
  const pendingTest = d.contents.find((c) => c.kind === "prueba_inicial" && ["generando", "pendiente", "aprobado"].includes(c.status));

  return (
    <div className="space-y-5">
      <div>
        <Link href={`/docente/aulas/${st.classroom.id}`} className="text-sm text-indigo-700 hover:underline">
          ← Aula {st.classroom.name}
        </Link>
        <PageHeader
          title={st.full_name}
          subtitle={`Usuario ${st.username} · código interno ${st.code} · ${st.classroom.name}`}
          actions={
            isTeacher ? (
              <div className="flex flex-wrap gap-2">
                <button className={btnGhost} disabled={!!busy} onClick={() => run("pin", async () => (setPin((await post<{ pin: string }>(`/students/${st.id}/reset-pin`)).pin), "PIN nuevo generado."))}>
                  Nuevo PIN
                </button>
                <button className={btnPrimary} disabled={!!busy || working} onClick={() => run("report", async () => (await post(`/students/${st.id}/reports`), "El Agente Evaluador está preparando el reporte."))}>
                  Reporte de avance
                </button>
              </div>
            ) : undefined
          }
        />
      </div>
      {msg && (msg.tone === "ok" ? <Notice tone="ok">{msg.text}</Notice> : <ErrorBox message={msg.text} />)}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Perfil de aprendizaje (CU-IA-01)">
          {p ? (
            <div className="space-y-2 text-sm">
              <div className="flex flex-wrap gap-2">
                <Chip className="bg-indigo-100 text-indigo-800">{LEVEL[p.level]}</Chip>
                <Chip className="bg-slate-100 text-slate-700">Lectura {p.reading_level}</Chip>
                <Chip className="bg-slate-100 text-slate-700">Ritmo {p.pace}</Chip>
              </div>
              <p>
                <b>Fortalezas:</b> {p.strengths.join(", ") || "—"}
              </p>
              <p>
                <b>Brechas:</b> {p.gaps.join(", ") || "—"}
              </p>
              <p className="rounded-xl bg-slate-50 p-3 text-slate-600">{p.recommendation}</p>
              <p className="text-xs text-slate-400">
                Última actualización: {SOURCE[d.profile_history[0].source] ?? d.profile_history[0].source}, {formatDate(d.profile_history[0].created_at)}
              </p>
            </div>
          ) : (
            <Notice tone="warn">Sin perfil todavía. Aplica la prueba inicial (recomendado) o registra un diagnóstico con tus observaciones.</Notice>
          )}
          <div className="mt-4 space-y-2 border-t pt-4">
            <div className="flex items-center justify-between gap-2">
              <span className={label}>Intereses</span>
              {isTeacher && interests === null && (
                <button className="text-xs font-semibold text-indigo-700" onClick={() => setInterests(st.interests)}>
                  Editar
                </button>
              )}
            </div>
            {interests === null ? (
              <p className="text-sm">{st.interests || "No registrados"}</p>
            ) : (
              <div className="flex gap-2">
                <input className={input} value={interests} onChange={(e) => setInterests(e.target.value)} maxLength={200} />
                <button className={btnPrimary} onClick={() => run("int", async () => (await patch(`/students/${st.id}`, { interests }), setInterests(null), "Intereses guardados."))}>
                  Guardar
                </button>
              </div>
            )}
          </div>
        </Card>

        {isTeacher && (
          <Card title={p ? "Actualizar diagnóstico" : "Primer diagnóstico"}>
            <div className="space-y-4">
              <div className="rounded-xl bg-indigo-50 p-4">
                <p className="text-sm font-semibold text-indigo-900">Prueba inicial en la plataforma</p>
                <p className="mb-2 text-xs text-indigo-800">El Agente Generador crea 6 preguntas; tú la apruebas y el estudiante la rinde. Con sus respuestas, el Agente de Diagnóstico arma el perfil.</p>
                {pendingTest ? (
                  <p className="text-sm">
                    Prueba de {pendingTest.area}: <StatusChip status={pendingTest.status} />
                    {pendingTest.status === "pendiente" && (
                      <Link href="/docente/validacion" className="ml-2 font-semibold text-indigo-700 underline">
                        revisarla
                      </Link>
                    )}
                  </p>
                ) : (
                  <div className="flex gap-2">
                    <select className={input} value={area} onChange={(e) => setArea(e.target.value as (typeof AREAS)[number])}>
                      {AREAS.map((a) => (
                        <option key={a}>{a}</option>
                      ))}
                    </select>
                    <button className={btnPrimary} disabled={!!busy} onClick={() => run("test", async () => (await post(`/students/${st.id}/initial-test`, { area }), "Generando la prueba inicial. Aparecerá en Validación."))}>
                      Generar
                    </button>
                  </div>
                )}
              </div>
              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  run("diag", async () => (await post(`/students/${st.id}/diagnosis`, notes), setNotes({ teacher_notes: "", external_test: "" }), "Perfil actualizado por el Agente de Diagnóstico."));
                }}
              >
                <label className={label} htmlFor="obs">
                  O con tus observaciones
                </label>
                <textarea id="obs" className={input} rows={2} placeholder="Ej.: comprende bien en voz alta, se pierde con enunciados largos…" value={notes.teacher_notes} onChange={(e) => setNotes({ ...notes, teacher_notes: e.target.value })} />
                <textarea className={input} rows={2} placeholder="Resultados de una prueba en papel (opcional), ej.: 14/20, falla en fracciones" value={notes.external_test} onChange={(e) => setNotes({ ...notes, external_test: e.target.value })} />
                <button className={btnGhost} disabled={!!busy || (!notes.teacher_notes.trim() && !notes.external_test.trim())}>
                  {busy === "diag" ? "El agente está analizando…" : "Diagnosticar con mis observaciones"}
                </button>
              </form>
            </div>
          </Card>
        )}
      </div>

      {isTeacher && (
        <Card title="Generar material (CU-IA-02 y 03)">
          {!p ? (
            <Empty>Disponible cuando el estudiante tenga perfil de aprendizaje.</Empty>
          ) : (
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                run("gen", async () => (await post(`/students/${st.id}/contents`, { area, ...gen }), setGen({ ...gen, topic: "" }), "Los agentes Generador y de Adaptación están trabajando. El material aparecerá en Validación."));
              }}
            >
              <div className="min-w-40 flex-1">
                <label className={label} htmlFor="area">
                  Área
                </label>
                <select id="area" className={`${input} mt-1`} value={area} onChange={(e) => setArea(e.target.value as (typeof AREAS)[number])}>
                  {AREAS.map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </div>
              <div className="min-w-56 flex-[2]">
                <label className={label} htmlFor="topic">
                  Tema curricular
                </label>
                <input id="topic" className={`${input} mt-1`} placeholder="Ej.: fracciones homogéneas" value={gen.topic} onChange={(e) => setGen({ ...gen, topic: e.target.value })} required minLength={2} />
              </div>
              <div>
                <label className={label} htmlFor="dif">
                  Dificultad
                </label>
                <select id="dif" className={`${input} mt-1`} value={gen.difficulty} onChange={(e) => setGen({ ...gen, difficulty: Number(e.target.value) })}>
                  {[1, 2, 3, 4].map((n) => (
                    <option key={n} value={n}>
                      {n} · {["muy guiada", "básica", "intermedia", "retadora"][n - 1]}
                    </option>
                  ))}
                </select>
              </div>
              <button className={btnPrimary} disabled={!!busy}>
                {busy === "gen" ? "Enviando…" : "Generar y adaptar"}
              </button>
            </form>
          )}
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <Card title="Materiales y pruebas">
          {d.contents.length === 0 ? (
            <Empty>Sin materiales todavía.</Empty>
          ) : (
            <ul className="divide-y text-sm">
              {d.contents.map((c) => (
                <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <div>
                    <div className="font-semibold">{c.title ?? `${c.kind === "prueba_inicial" ? "Prueba inicial" : c.topic} (en preparación)`}</div>
                    <div className="text-xs text-slate-500">
                      {c.kind === "prueba_inicial" ? "Prueba inicial" : `${c.area} · dificultad ${c.difficulty}`} · {c.origin.startsWith("orquestador") ? `propuesto por el Orquestador (${c.origin.split(":")[1]})` : "pedido por ti"} · {formatDate(c.created_at)}
                    </div>
                  </div>
                  <StatusChip status={c.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Reportes de avance (CU-IA-06)">
          {d.reports.length === 0 ? (
            <Empty>Pide un reporte con el botón de arriba. También se genera solo cuando un tema queda consolidado.</Empty>
          ) : (
            <div className="space-y-3">
              {d.reports.slice(0, 2).map((r) => (
                <div key={r.id} className="rounded-xl bg-slate-50 p-3 text-sm">
                  <div className="mb-1 text-xs text-slate-500">
                    {formatDate(r.created_at)} · {r.automatic ? "automático (tema consolidado)" : "a pedido"}
                  </div>
                  {r.status === "generando" && <Spinner label="El Agente Evaluador está redactando…" />}
                  {r.status === "error_ia" && <ErrorBox message={`No se pudo generar: ${r.error}`} />}
                  {r.data && (
                    <div className="space-y-1">
                      <p>{r.data.summary}</p>
                      {r.data.progress.length > 0 && <p><b>Avances:</b> {r.data.progress.join("; ")}</p>}
                      {r.data.difficulties.length > 0 && <p><b>Por consolidar:</b> {r.data.difficulties.join("; ")}</p>}
                      {r.data.recommendations.length > 0 && <p><b>Sugerencias:</b> {r.data.recommendations.join("; ")}</p>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Avance entre sesiones">
        {progress.data && progress.data.filter((x) => x.kind === "material").length >= 2 ? (
          <ProgressCharts points={progress.data.filter((x) => x.kind === "material")} />
        ) : (
          <Empty>El gráfico aparece cuando el estudiante complete al menos dos materiales.</Empty>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <Card title="Por tema">
          {d.topics.length === 0 ? (
            <Empty>Sin respuestas.</Empty>
          ) : (
            <ul className="space-y-3 text-sm">
              {d.topics.map((t) => (
                <li key={t.topic}>
                  <div className="flex justify-between gap-2 font-semibold">
                    {t.topic} <TrafficLight light={t.light} accuracy={t.accuracy} />
                  </div>
                  <div className="text-xs text-slate-500">
                    {t.answers} respuestas · {t.avg_time_s} s en promedio
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Últimas respuestas (telemetría)">
          {d.events.length === 0 ? (
            <Empty>Sin respuestas registradas.</Empty>
          ) : (
            <div className="max-h-96 overflow-auto">
              <table className="w-full min-w-[620px] text-sm">
                <thead className="sticky top-0 bg-white text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-2">Tema</th>
                    <th>Entorno</th>
                    <th>Resultado</th>
                    <th>Tiempo</th>
                    <th>Confianza</th>
                    <th>Cambios</th>
                    <th>Categoría</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {d.events.map((e) => (
                    <tr key={e.id} title={e.question}>
                      <td className="py-1.5">{e.topic}</td>
                      <td>{e.environment}</td>
                      <td className={e.correct ? "text-emerald-700" : "text-rose-700"}>{e.correct ? "✓ correcta" : `✗ «${e.answer}»`}</td>
                      <td className="tabular-nums">{(e.time_ms / 1000).toFixed(1)} s</td>
                      <td className="tabular-nums">{e.confidence}/5</td>
                      <td className="tabular-nums">{e.changes}</td>
                      <td>
                        <CategoryChip k={e.category_key} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
      <CredentialModal open={!!pin} onClose={() => setPin("")} title="PIN nuevo" who={st.full_name} login={st.username} secret={pin} secretLabel="PIN" />
    </div>
  );
}
