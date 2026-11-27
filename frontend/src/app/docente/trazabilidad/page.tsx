"use client";

import { useState } from "react";
import type { AgentRunRow } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { AGENT_LABEL, Card, Chip, Empty, ErrorBox, formatDate, PageHeader, Spinner } from "@/lib/ui";

export default function Trace() {
  const { data, error } = useApi<AgentRunRow[]>("/agent-runs?limit=150");
  const [open, setOpen] = useState<number | null>(null);
  const [agent, setAgent] = useState("");
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Cargando registro…" />;
  const rows = agent ? data.filter((r) => r.agent === agent) : data;
  const failed = data.filter((r) => r.status === "error").length;
  return (
    <div className="space-y-4">
      <PageHeader
        title="Trazabilidad de los agentes"
        subtitle="Cada llamada al modelo queda registrada con su entrada, su salida, los intentos y el tiempo (Sección 10)."
        actions={
          <select className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm" value={agent} onChange={(e) => setAgent(e.target.value)} aria-label="Filtrar por agente">
            <option value="">Todos los agentes</option>
            {Object.entries(AGENT_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        }
      />
      {failed > 0 && <p className="text-sm text-rose-700">{failed} llamada(s) fallaron tras agotar los reintentos.</p>}
      <Card>
        {rows.length === 0 ? (
          <Empty>Todavía no hay actividad de los agentes.</Empty>
        ) : (
          <ul className="divide-y text-sm">
            {rows.map((r) => (
              <li key={r.id} className="py-2">
                <button className="flex w-full flex-wrap items-center gap-2 text-left" onClick={() => setOpen(open === r.id ? null : r.id)} aria-expanded={open === r.id}>
                  <Chip className="bg-indigo-100 text-indigo-800">{AGENT_LABEL[r.agent] ?? r.agent}</Chip>
                  <Chip className={r.status === "ok" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}>{r.status === "ok" ? "OK" : "Error"}</Chip>
                  <span className="text-slate-600">{r.student_name ?? "—"}</span>
                  <span className="text-xs text-slate-400">
                    {r.model} · {r.attempts} intento(s) · {(r.latency_ms / 1000).toFixed(1)} s
                  </span>
                  <span className="ml-auto text-xs text-slate-400">{formatDate(r.created_at)}</span>
                </button>
                {open === r.id && (
                  <div className="mt-2 grid gap-2 lg:grid-cols-2">
                    <div>
                      <div className="mb-1 text-xs font-semibold uppercase text-slate-500">Entrada</div>
                      <pre className="max-h-80 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(r.input, null, 2)}</pre>
                    </div>
                    <div>
                      <div className="mb-1 text-xs font-semibold uppercase text-slate-500">{r.status === "ok" ? "Salida validada" : "Error"}</div>
                      <pre className="max-h-80 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-100">{r.status === "ok" ? JSON.stringify(r.output, null, 2) : r.error}</pre>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
