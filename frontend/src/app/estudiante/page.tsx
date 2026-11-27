"use client";

import Link from "next/link";
import type { StudentHome } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Empty, ErrorBox, Spinner } from "@/lib/ui";

export default function Home() {
  const { data, error } = useApi<StudentHome>("/my/home");
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Cargando tus materiales…" />;
  const items = [...data.initial_tests, ...data.materials];
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="rounded-3xl bg-amber-400 p-6">
        <h1 className="font-display text-3xl font-bold">¡Hola, {data.name.split(" ")[0]}!</h1>
        <p>{data.initial_tests.length ? "Primero, una prueba corta para conocerte mejor." : "Estos son tus materiales."}</p>
      </div>
      {items.length === 0 && <Empty>Tu profesora está preparando tu primera actividad. Vuelve pronto.</Empty>}
      <div className="grid gap-4 sm:grid-cols-2">
        {items.map((m) => (
          <Link key={m.id} href={`/estudiante/material/${m.id}`} className="rounded-2xl border-2 border-slate-200 bg-white p-5 hover:border-indigo-400">
            <div className="text-xs font-semibold uppercase text-indigo-600">{m.kind === "prueba_inicial" ? "Prueba inicial" : m.area}</div>
            <h2 className="mt-1 font-display text-xl font-semibold">{m.title}</h2>
            <div className="mt-2 text-sm font-semibold text-indigo-700">
              {m.exercise_count} preguntas {m.completed && "· ✓ hecho"}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
