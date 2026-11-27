"use client";

import Link from "next/link";
import type { Classroom, Light } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Card, Empty, ErrorBox, Kpi, PageHeader, Spinner, TrafficLight } from "@/lib/ui";

interface Overview {
  teachers: number;
  students: number;
  classrooms: (Classroom & {
    students: number;
    answers: number;
    accuracy: number | null;
    light: Light;
    pending_contents: number;
    pending_reinforcements: number;
    concept_alerts: number;
  })[];
}

export default function AdminHome() {
  const { data, error } = useApi<Overview>("/admin/overview");
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Cargando la institución…" />;
  return (
    <div className="space-y-5">
      <PageHeader title="Institución" subtitle="Avance de cada aula y trabajo pendiente de los docentes." />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Kpi value={data.classrooms.length} label="aulas" />
        <Kpi value={data.teachers} label="docentes activos" />
        <Kpi value={data.students} label="estudiantes" />
      </div>
      <Card title="Aulas">
        {data.classrooms.length === 0 ? (
          <Empty>
            Todavía no hay aulas. <Link href="/admin/aulas" className="font-semibold text-indigo-700 underline">Crea la primera</Link>.
          </Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-2">Aula</th>
                  <th>Docente</th>
                  <th>Estudiantes</th>
                  <th>Acierto</th>
                  <th>Por validar</th>
                  <th>Errores de concepto</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.classrooms.map((c) => (
                  <tr key={c.id}>
                    <td className="py-2 font-semibold">
                      <Link href={`/docente/aulas/${c.id}`} className="text-indigo-700 hover:underline">
                        {c.name} · {c.year}
                      </Link>
                    </td>
                    <td>{c.teacher?.full_name ?? <span className="text-amber-700">Sin docente</span>}</td>
                    <td className="tabular-nums">{c.students}</td>
                    <td>
                      <TrafficLight light={c.light} accuracy={c.accuracy} />
                    </td>
                    <td className="tabular-nums">{c.pending_contents + c.pending_reinforcements}</td>
                    <td className="tabular-nums">{c.concept_alerts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
