"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ProgressPoint } from "@/lib/api";

const INK = "#4f46e5"; // una sola serie por gráfico: un solo tono, el del sistema
const GRID = "#e2e8f0";
const AXIS = "#64748b";

function Chart({ data, dataKey, unit, domain, title }: { data: (ProgressPoint & { label: string })[]; dataKey: "accuracy_pct" | "avg_time_s"; unit: string; domain?: [number, number]; title: string }) {
  return (
    <figure>
      <figcaption className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</figcaption>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={{ stroke: GRID }} />
            <YAxis domain={domain} tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={false} unit={unit} width={48} />
            <Tooltip
              cursor={{ stroke: AXIS, strokeDasharray: "3 3" }}
              contentStyle={{ borderRadius: 12, borderColor: GRID, fontSize: 12 }}
              formatter={(v) => [`${v}${unit}`, title]}
              labelFormatter={(_, p) => {
                const d = p?.[0]?.payload as (ProgressPoint & { label: string }) | undefined;
                return d ? `${d.label} · ${d.topic} · dificultad ${d.difficulty}` : "";
              }}
            />
            <Line type="monotone" dataKey={dataKey} stroke={INK} strokeWidth={2} dot={{ r: 4, fill: INK, stroke: "#fff", strokeWidth: 2 }} activeDot={{ r: 6 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

/** Sección 17.2: avance del acierto y de la velocidad entre sesiones. Dos gráficos, nunca dos ejes en uno. */
export function ProgressCharts({ points }: { points: ProgressPoint[] }) {
  const data = points.map((p, i) => ({ ...p, label: `S${i + 1}`, accuracy_pct: Math.round(p.accuracy * 100) }));
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Chart data={data} dataKey="accuracy_pct" unit=" %" domain={[0, 100]} title="Acierto por sesión" />
      <Chart data={data} dataKey="avg_time_s" unit=" s" title="Tiempo promedio por pregunta" />
    </div>
  );
}
