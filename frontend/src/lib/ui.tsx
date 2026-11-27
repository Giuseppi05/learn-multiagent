"use client";

import { useEffect, useRef } from "react";
import type { CategoryKey, ContentStatus, Light } from "./api";

export const CATEGORY: Record<CategoryKey, { label: string; cls: string }> = {
  lo_domina: { label: "Lo domina", cls: "bg-emerald-100 text-emerald-800" },
  falta_practica: { label: "Le falta práctica", cls: "bg-amber-100 text-amber-800" },
  no_sabe: { label: "No sabe el tema", cls: "bg-violet-100 text-violet-800" },
  entendio_mal: { label: "Entendió mal", cls: "bg-rose-100 text-rose-800" },
};

const LIGHT: Record<Light, { dot: string; label: string }> = {
  verde: { dot: "bg-emerald-500", label: "Domina" },
  ambar: { dot: "bg-amber-500", label: "En práctica" },
  rojo: { dot: "bg-rose-500", label: "Refuerzo" },
  sin_datos: { dot: "bg-slate-300", label: "Sin datos" },
};

const STATUS: Record<ContentStatus, { label: string; cls: string }> = {
  generando: { label: "Generando…", cls: "bg-sky-100 text-sky-800" },
  pendiente: { label: "Por validar", cls: "bg-amber-100 text-amber-800" },
  aprobado: { label: "Publicado", cls: "bg-emerald-100 text-emerald-800" },
  rechazado: { label: "Rechazado", cls: "bg-slate-200 text-slate-600" },
  reemplazado: { label: "Reemplazado", cls: "bg-slate-100 text-slate-500" },
  error_ia: { label: "Falló la IA", cls: "bg-rose-100 text-rose-800" },
  requiere_docente: { label: "Requiere tu ajuste", cls: "bg-orange-100 text-orange-800" },
};

export const LEVEL: Record<string, string> = { inicio: "En inicio", en_proceso: "En proceso", logrado: "Logrado", destacado: "Destacado" };

export const AGENT_LABEL: Record<string, string> = {
  diagnostico: "Diagnóstico",
  generador: "Generador",
  adaptacion: "Adaptación",
  evaluador: "Evaluador",
  refuerzo_conceptual: "Refuerzo conceptual",
  asistente: "Asistente",
  reporte: "Reporte",
};

export function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}>{children}</span>;
}

export function CategoryChip({ k }: { k: CategoryKey }) {
  return <Chip className={CATEGORY[k].cls}>{CATEGORY[k].label}</Chip>;
}

export function StatusChip({ status }: { status: ContentStatus }) {
  return <Chip className={STATUS[status].cls}>{STATUS[status].label}</Chip>;
}

export function TrafficLight({ light, accuracy }: { light: Light; accuracy: number | null }) {
  return (
    <span className="inline-flex items-center gap-2 tabular-nums">
      <span className={`h-2.5 w-2.5 rounded-full ${LIGHT[light].dot}`} aria-hidden />
      {accuracy === null ? "—" : `${Math.round(accuracy * 100)} %`}
      <span className="text-xs text-slate-500">{LIGHT[light].label}</span>
    </span>
  );
}

export function LightDot({ light, title }: { light: Light; title?: string }) {
  return <span title={title} className={`inline-block h-2.5 w-2.5 rounded-full ${LIGHT[light].dot}`} />;
}

export function Card({ title, children, actions, className = "" }: { title?: string; children: React.ReactNode; actions?: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="font-display text-lg font-semibold text-slate-900">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Kpi({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="font-display text-2xl font-bold tabular-nums text-slate-900">{value}</div>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}

export function ErrorBox({ message, children }: { message: string; children?: React.ReactNode }) {
  return (
    <div role="alert" className="space-y-2 rounded-xl bg-rose-50 p-4 text-sm text-rose-700">
      <p>{message}</p>
      {children}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: React.ReactNode; tone?: "info" | "ok" | "warn" }) {
  const cls = { info: "bg-sky-50 text-sky-900", ok: "bg-emerald-50 text-emerald-900", warn: "bg-amber-50 text-amber-900" }[tone];
  return <div className={`rounded-xl p-3 text-sm ${cls}`}>{children}</div>;
}

export function Spinner({ label = "Procesando…" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
      {label}
    </span>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-sm text-slate-500">{children}</p>;
}

/** Diálogo modal accesible basado en <dialog>. */
export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} className="w-[min(32rem,calc(100vw-2rem))] rounded-2xl p-0 backdrop:bg-slate-900/40">
      <div className="space-y-4 p-6">
        <h2 className="font-display text-xl font-semibold text-slate-900">{title}</h2>
        {children}
      </div>
    </dialog>
  );
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export const btn = "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";
export const btnPrimary = `${btn} bg-indigo-600 text-white hover:bg-indigo-700`;
export const btnGhost = `${btn} border border-slate-300 bg-white text-slate-700 hover:bg-slate-50`;
export const btnDanger = `${btn} border border-rose-200 bg-white text-rose-700 hover:bg-rose-50`;
export const input = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";
export const label = "block text-xs font-semibold uppercase tracking-wide text-slate-500";
