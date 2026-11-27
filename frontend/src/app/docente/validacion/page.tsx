"use client";

import Link from "next/link";
import { useState } from "react";
import { api, type ContentDetail, type ContentSummary, errorMessage, post, type ReinforcementItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi, usePolling } from "@/lib/hooks";
import { btnDanger, btnGhost, btnPrimary, Card, Chip, Empty, ErrorBox, formatDate, input, Notice, PageHeader, Spinner, StatusChip } from "@/lib/ui";

const QUEUE = "pendiente,generando,error_ia,requiere_docente";

function ContentReview({ summary, canAct, onDone }: { summary: ContentSummary; canAct: boolean; onDone: () => void }) {
  const [c, setC] = useState<ContentDetail | null>(null);
  const [open, setOpen] = useState(false);
  const [showBase, setShowBase] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function toggle() {
    if (!open && !c) {
      try {
        setC(await api<ContentDetail>(`/contents/${summary.id}`));
      } catch (e) {
        setErr(errorMessage(e));
      }
    }
    setOpen(!open);
  }

  async function act(path: string, body?: unknown) {
    setBusy(true);
    setErr("");
    try {
      await post(path, body);
      onDone();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const body = c ? (showBase && c.kind === "material" ? c.base : c.adapted) : null;
  const isTest = summary.kind === "prueba_inicial";
  return (
    <Card
      title={`${summary.student_name} · ${summary.title ?? summary.topic}`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <StatusChip status={summary.status} />
          <Chip className={isTest ? "bg-violet-100 text-violet-800" : summary.origin.startsWith("orquestador") ? "bg-indigo-100 text-indigo-800" : "bg-slate-100 text-slate-700"}>
            {isTest ? "Prueba inicial" : summary.origin.startsWith("orquestador") ? `Orquestador: ${summary.origin.split(":")[1]}` : "Pedido por ti"}
          </Chip>
          {!isTest && <Chip className="bg-slate-100 text-slate-700">Dificultad {summary.difficulty}</Chip>}
          {summary.returns_count > 0 && <Chip className="bg-amber-100 text-amber-800">Devuelto {summary.returns_count}×</Chip>}
        </div>
      }
    >
      <p className="text-xs text-slate-500">
        {summary.classroom} · {summary.area} · {formatDate(summary.updated_at)}
      </p>
      {summary.status === "generando" && (
        <div className="mt-2">
          <Spinner label={summary.returns_count ? "El Agente Generador está corrigiendo con tus observaciones…" : "Los agentes están preparando el contenido…"} />
        </div>
      )}
      {summary.status === "error_ia" && (
        <div className="mt-2 space-y-2">
          <ErrorBox message={`La IA no entregó un contenido válido tras 3 intentos. ${summary.error}`} />
          {canAct && (
            <button className={btnPrimary} disabled={busy} onClick={() => act(`/contents/${summary.id}/retry`)}>
              Reintentar
            </button>
          )}
        </div>
      )}
      {summary.status === "requiere_docente" && <Notice tone="warn">Lo devolviste 3 veces: el ciclo automático se detuvo para no entrar en un bucle. Puedes pedir un material nuevo desde la ficha del estudiante.</Notice>}
      {(summary.status === "pendiente" || summary.status === "requiere_docente") && (
        <button className="mt-2 text-sm font-semibold text-indigo-700" onClick={toggle}>
          {open ? "Ocultar contenido ▲" : "Revisar contenido ▼"}
        </button>
      )}
      {open && body && c && (
        <div className="mt-3 space-y-3">
          {c.kind === "material" && (
            <div className="inline-flex rounded-xl border border-slate-200 p-0.5 text-sm">
              <button className={`rounded-lg px-3 py-1 ${!showBase ? "bg-indigo-600 text-white" : ""}`} onClick={() => setShowBase(false)}>
                Versión adaptada
              </button>
              <button className={`rounded-lg px-3 py-1 ${showBase ? "bg-indigo-600 text-white" : ""}`} onClick={() => setShowBase(true)}>
                Versión base
              </button>
            </div>
          )}
          <h3 className="font-display text-lg font-semibold">{body.title}</h3>
          <p className="text-sm leading-relaxed">{body.explanation}</p>
          {body.examples.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-slate-600">
              {body.examples.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          )}
          <ol className="space-y-2 text-sm">
            {body.exercises.map((e, i) => (
              <li key={i} className="rounded-xl bg-slate-50 p-3">
                <div className="font-semibold">
                  {i + 1}. {e.question}
                </div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {e.options.map((o, j) => (
                    <span key={j} className={`rounded-lg px-2 py-0.5 ${j === e.correct_index ? "bg-emerald-100 font-semibold text-emerald-800" : "bg-white text-slate-600"}`}>
                      {"ABCD"[j]}) {o}
                    </span>
                  ))}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {isTest ? "Evalúa: " : "Explicación: "}
                  {e.explanation} · {e.expected_seconds} s esperados
                </div>
              </li>
            ))}
          </ol>
          {!isTest && body.reinforcement_activity && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">Actividad de refuerzo: {body.reinforcement_activity}</p>}
          {!showBase && body.adaptation_notes && <p className="rounded-xl bg-indigo-50 p-3 text-sm text-indigo-900">Agente de Adaptación: {body.adaptation_notes}</p>}
          {c.reviews.length > 0 && (
            <div className="text-xs text-slate-500">
              Observaciones anteriores:
              <ul className="list-disc pl-5">
                {c.reviews.map((r, i) => (
                  <li key={i}>
                    {r.decision} · {r.note || "sin nota"}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {canAct && summary.status === "pendiente" && (
            <div className="space-y-2 border-t pt-3">
              <textarea className={input} rows={2} placeholder="Observaciones para el Agente Generador (obligatorias si lo devuelves)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={1500} />
              <div className="flex flex-wrap gap-2">
                <button className={btnPrimary} disabled={busy} onClick={() => act(`/contents/${summary.id}/review`, { decision: "aprobado", note })}>
                  Aprobar y publicar
                </button>
                <button className={btnGhost} disabled={busy || note.trim().length < 5} onClick={() => act(`/contents/${summary.id}/review`, { decision: "devuelto", note })} title="Escribe tus observaciones para devolverlo">
                  Devolver con observaciones
                </button>
                <button className={btnDanger} disabled={busy} onClick={() => act(`/contents/${summary.id}/review`, { decision: "rechazado", note })}>
                  Rechazar
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      {err && (
        <div className="mt-2">
          <ErrorBox message={err} />
        </div>
      )}
    </Card>
  );
}

function Reinforcement({ r, canAct, onDone }: { r: ReinforcementItem; canAct: boolean; onDone: () => void }) {
  const [err, setErr] = useState("");
  async function review(approve: boolean) {
    try {
      await post(`/reinforcements/${r.id}/review`, { approve });
      onDone();
    } catch (e) {
      setErr(errorMessage(e));
    }
  }
  if (!r.data) return null;
  return (
    <Card title={`${r.student_name} · ${r.data.activity_title}`}>
      <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-900">{r.data.suspected_misconception}</p>
      <details className="mt-2 text-xs text-slate-500">
        <summary className="cursor-pointer">Errores con alta confianza ({r.data.mistakes.length})</summary>
        <ul className="mt-1 list-disc pl-5">
          {r.data.mistakes.map((m, i) => (
            <li key={i}>
              {m.enunciado} → eligió «{m.respuesta}» (era «{m.correcta}»), confianza {m.confianza}/5
            </li>
          ))}
        </ul>
      </details>
      <ol className="mt-2 list-decimal pl-5 text-sm">
        {r.data.steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      {r.data.materials.length > 0 && <p className="mt-2 text-xs text-slate-500">Materiales: {r.data.materials.join(", ")}</p>}
      {err && <ErrorBox message={err} />}
      {canAct && (
        <div className="mt-3 flex gap-2">
          <button className={btnPrimary} onClick={() => review(true)}>
            La aplicaré en clase
          </button>
          <button className={btnGhost} onClick={() => review(false)}>
            Descartar
          </button>
        </div>
      )}
    </Card>
  );
}

export default function Validation() {
  const { me } = useAuth();
  const canAct = me?.user.role === "docente";
  const contents = useApi<ContentSummary[]>(`/contents?status=${QUEUE}`);
  const rfs = useApi<ReinforcementItem[]>("/reinforcements?status=pendiente,generando,error_ia");
  const reload = () => {
    contents.reload();
    rfs.reload();
  };
  usePolling(reload, !!contents.data?.some((c) => c.status === "generando") || !!rfs.data?.some((r) => r.status === "generando"));

  if (contents.error || rfs.error) return <ErrorBox message={contents.error || rfs.error} />;
  if (!contents.data || !rfs.data) return <Spinner label="Cargando pendientes…" />;
  const pendingRfs = rfs.data.filter((r) => r.status === "pendiente");
  const failedRfs = rfs.data.filter((r) => r.status === "error_ia");
  return (
    <div className="space-y-5">
      <PageHeader title="Validación docente" subtitle="Ningún material ni actividad llega al estudiante sin tu aprobación (supervisión humana, Sección 10)." />
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold">Materiales y pruebas ({contents.data.length})</h2>
        {contents.data.length === 0 ? (
          <Empty>
            No hay nada por revisar. Pide material desde la ficha de un estudiante en <Link href="/docente" className="font-semibold text-indigo-700 underline">Mis aulas</Link>.
          </Empty>
        ) : (
          contents.data.map((c) => <ContentReview key={`${c.id}-${c.status}-${c.returns_count}`} summary={c} canAct={canAct} onDone={reload} />)
        )}
      </section>
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold">Actividades de refuerzo conceptual ({pendingRfs.length})</h2>
        <p className="text-sm text-slate-500">Las propone el Agente de Refuerzo Conceptual cuando un estudiante se equivoca con mucha seguridad (Sección 21). Son para aplicar tú, en clase.</p>
        {failedRfs.length > 0 && <Notice tone="warn">{failedRfs.length} actividad(es) no se pudieron generar porque la IA no respondió.</Notice>}
        {pendingRfs.length === 0 ? (
          <Empty>Sin actividades pendientes.</Empty>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {pendingRfs.map((r) => (
              <Reinforcement key={r.id} r={r} canAct={canAct} onDone={reload} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
