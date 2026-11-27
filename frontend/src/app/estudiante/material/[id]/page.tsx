"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, errorMessage, post, type StudentMaterial, type SubmissionStatus, type SubmitResult } from "@/lib/api";
import { useApi, usePolling } from "@/lib/hooks";
import { btnPrimary, CategoryChip, ErrorBox, input, Spinner } from "@/lib/ui";

interface Answer {
  index: number;
  selected: number;
  time_ms: number;
  confidence: number;
  changes: number;
}

const FACES = ["😟", "🙁", "😐", "🙂", "😄"];

function Assistant({ id }: { id: string }) {
  const hist = useApi<{ pregunta: string; respuesta: string; seguimiento: string }[]>(`/my/materials/${id}/assistant`);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setErr("");
    try {
      await post(`/my/materials/${id}/assistant`, { question: q.trim() });
      setQ("");
      hist.reload();
    } catch (e2) {
      setErr(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="rounded-2xl border-2 border-indigo-100 bg-white p-4">
      <h2 className="font-display text-lg font-semibold text-indigo-700">Asistente de dudas</h2>
      <div className="mt-2 max-h-96 space-y-2 overflow-y-auto text-sm">
        <p className="mr-6 rounded-xl bg-indigo-50 px-3 py-2">¿Tienes una duda sobre este material? Te lo explico de otra forma.</p>
        {hist.data?.map((m, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-6 rounded-xl bg-amber-100 px-3 py-2">{m.pregunta}</p>
            <p className="mr-6 rounded-xl bg-indigo-50 px-3 py-2">
              {m.respuesta} {m.seguimiento}
            </p>
          </div>
        ))}
        {busy && <Spinner label="Pensando…" />}
      </div>
      {err && <ErrorBox message={err} />}
      <form onSubmit={send} className="mt-3 flex gap-2">
        <input className={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Escribe tu duda…" maxLength={500} />
        <button className={btnPrimary} disabled={busy}>
          Enviar
        </button>
      </form>
    </aside>
  );
}

export default function MaterialPage() {
  const { id } = useParams<{ id: string }>();
  const { data: m, error } = useApi<StudentMaterial>(`/my/materials/${id}`);
  const [step, setStep] = useState(-1);
  const [sel, setSel] = useState<number | null>(null);
  const [changes, setChanges] = useState(0);
  const [conf, setConf] = useState(3);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [status, setStatus] = useState<SubmissionStatus | null>(null);
  const [err, setErr] = useState("");
  const [sending, setSending] = useState(false);
  const started = useRef(0);

  useEffect(() => {
    // Igual que el mando físico: el tiempo se mide desde que aparece cada pregunta
    started.current = performance.now();
    setSel(null);
    setChanges(0);
    setConf(3);
  }, [step]);

  // La retroalimentación del Agente Evaluador llega en segundo plano
  usePolling(async () => result && setStatus(await api<SubmissionStatus>(`/my/submissions/${result.submission_id}`)), !!result && status?.status !== "listo" && status?.status !== "error_ia");

  async function next() {
    if (!m || sel === null) return;
    const a = { index: step, selected: sel, time_ms: Math.max(1, Math.round(performance.now() - started.current)), confidence: conf, changes };
    const all = answers.some((x) => x.index === step) ? answers : [...answers, a];
    setAnswers(all);
    if (step + 1 < m.exercises.length) return setStep(step + 1);
    setSending(true);
    setErr("");
    try {
      setResult(await post<SubmitResult>(`/my/materials/${id}/submit`, { answers: all, environment: "web" }));
    } catch (e) {
      setErr(`${errorMessage(e)} Tus respuestas siguen guardadas; vuelve a presionar «Terminar».`);
    } finally {
      setSending(false);
    }
  }

  if (error) return <ErrorBox message={error} />;
  if (!m) return <Spinner label="Abriendo material…" />;
  const ex = step >= 0 ? m.exercises[step] : null;
  const isTest = m.kind === "prueba_inicial";

  return (
    <div className={`grid gap-5 ${isTest ? "" : "lg:grid-cols-[1fr_320px]"}`}>
      <div className="space-y-4">
        <Link href="/estudiante" className="text-sm text-indigo-700 hover:underline">
          ← Mis materiales
        </Link>
        <h1 className="font-display text-3xl font-bold">{m.title}</h1>
        {step === -1 && !result && (
          <div className="space-y-4 rounded-3xl bg-white p-6 text-lg leading-relaxed">
            <p>{m.explanation}</p>
            {m.examples.map((x) => (
              <p key={x} className="rounded-2xl bg-amber-50 px-4 py-2">
                💡 {x}
              </p>
            ))}
            <button className={btnPrimary} onClick={() => setStep(0)}>
              ¡Empezar!
            </button>
          </div>
        )}
        {ex && !result && (
          <div className="space-y-5 rounded-3xl bg-white p-6">
            <p className="text-sm font-semibold text-slate-500">
              Pregunta {step + 1} de {m.exercises.length}
            </p>
            <p className="text-xl font-semibold">{ex.question}</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {ex.options.map((o, i) => (
                <button
                  key={i}
                  onClick={() => {
                    if (sel !== null && sel !== i) setChanges((c) => c + 1);
                    setSel(i);
                  }}
                  className={`rounded-2xl border-2 px-4 py-3 text-left text-lg font-semibold ${sel === i ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-200 hover:border-indigo-300"}`}
                >
                  <span className="mr-2 text-sm opacity-70">{"ABCD"[i]}</span>
                  {o}
                </button>
              ))}
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-600">¿Qué tan seguro estás?</p>
              <div className="mt-2 flex gap-2">
                {FACES.map((f, i) => (
                  <button key={i} onClick={() => setConf(i + 1)} aria-label={`Confianza ${i + 1}`} className={`h-12 w-12 rounded-full text-2xl ${conf === i + 1 ? "scale-110 bg-amber-300" : "bg-white"}`}>
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <button className={btnPrimary} onClick={next} disabled={sel === null || sending}>
              {sending ? "Enviando…" : step + 1 < m.exercises.length ? "Siguiente" : "Terminar"}
            </button>
            {err && <ErrorBox message={err} />}
          </div>
        )}
        {result && (
          <div className="space-y-4">
            <div className="rounded-3xl bg-indigo-600 p-6 text-white">
              {isTest ? (
                <p className="font-display text-2xl font-bold">¡Gracias! Con esto tu profesora preparará material para ti.</p>
              ) : status?.feedback ? (
                <p className="font-display text-2xl font-bold">{status.feedback.overall}</p>
              ) : status?.status === "error_ia" ? (
                <p className="font-display text-2xl font-bold">¡Terminaste!</p>
              ) : (
                <Spinner label="El Agente Evaluador está revisando tus respuestas…" />
              )}
            </div>
            {!isTest &&
              result.results.map((r) => {
                const fb = status?.feedback?.items.find((i) => i.index === r.index);
                return (
                  <div key={r.index} className={`rounded-2xl border-2 bg-white p-4 ${r.correct ? "border-emerald-200" : "border-rose-200"}`}>
                    <div className="flex justify-between gap-2">
                      <b>
                        {r.correct ? "✓" : "✗"} Pregunta {r.index + 1}
                      </b>
                      <CategoryChip k={r.category_key} />
                    </div>
                    <p className="mt-1 text-slate-700">{fb?.message ?? r.explanation}</p>
                    {!r.correct && <p className="mt-1 text-sm text-slate-500">Respuesta correcta: {r.correct_option}</p>}
                  </div>
                );
              })}
            <Link href="/estudiante" className={btnPrimary}>
              Volver a mis materiales
            </Link>
          </div>
        )}
      </div>
      {!isTest && <Assistant id={id} />}
    </div>
  );
}
