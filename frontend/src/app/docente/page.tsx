"use client";

import Link from "next/link";
import type { Classroom } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { Empty, ErrorBox, PageHeader, Spinner } from "@/lib/ui";

export default function TeacherHome() {
  const { me } = useAuth();
  const { data, error } = useApi<Classroom[]>("/classrooms");
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Cargando tus aulas…" />;
  return (
    <div className="space-y-5">
      <PageHeader title={`Hola, ${me?.user.full_name.split(" ")[0] ?? ""}`} subtitle="Elige un aula para ver el avance de tus estudiantes." />
      {data.length === 0 ? (
        <Empty>Todavía no tienes aulas asignadas. Pídele a la coordinación que te asigne una.</Empty>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((c) => (
            <Link key={c.id} href={`/docente/aulas/${c.id}`} className="group rounded-2xl border-2 border-slate-200 bg-white p-5 hover:border-indigo-400">
              <div className="text-xs font-semibold uppercase tracking-wide text-indigo-600">Año {c.year}</div>
              <div className="mt-1 font-display text-3xl font-bold group-hover:text-indigo-700">{c.name}</div>
              <div className="mt-2 text-sm text-slate-500">Ver panel del aula →</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
