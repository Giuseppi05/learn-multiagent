"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { Role } from "@/lib/api";
import { HOME_BY_ROLE, useAuth } from "@/lib/auth";
import { Spinner } from "@/lib/ui";

const NAV: Record<Role, { href: string; label: string }[]> = {
  admin: [
    { href: "/admin", label: "Institución" },
    { href: "/admin/docentes", label: "Docentes" },
    { href: "/admin/aulas", label: "Aulas" },
    { href: "/docente/trazabilidad", label: "Trazabilidad" },
  ],
  docente: [
    { href: "/docente", label: "Mis aulas" },
    { href: "/docente/validacion", label: "Validación" },
    { href: "/docente/trazabilidad", label: "Trazabilidad" },
  ],
  estudiante: [{ href: "/estudiante", label: "Mis materiales" }],
};

const ROLE_LABEL: Record<Role, string> = { admin: "Coordinación", docente: "Docente", estudiante: "Estudiante" };

/** Protege una sección: exige sesión, el rol correcto y que el personal haya cambiado su contraseña temporal. */
export function AppShell({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { me, signOut } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const role = me?.user.role;
  const allowed = !!role && roles.includes(role);
  const mustChange = !!me?.user.must_change_password;

  useEffect(() => {
    if (me === null) router.replace(`/login?next=${encodeURIComponent(path)}`);
    else if (me && mustChange) router.replace("/cambiar-clave");
    else if (me && !allowed) router.replace(HOME_BY_ROLE[me.user.role]);
  }, [me, allowed, mustChange, router, path]);

  if (!me || !allowed || mustChange) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Verificando tu sesión…" />
      </div>
    );
  }

  const kid = me.user.role === "estudiante";
  return (
    <div className="min-h-screen">
      <header className={`sticky top-0 z-20 border-b ${kid ? "border-amber-200 bg-amber-50/95" : "border-slate-200 bg-white/95"} backdrop-blur`}>
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link href={HOME_BY_ROLE[me.user.role]} className="font-display text-xl font-bold text-indigo-700">
            Aprende <span className="text-amber-500">Multiagente</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-sm font-semibold" aria-label="Navegación principal">
            {NAV[me.user.role].map((n) => {
              const active = path === n.href || (n.href !== HOME_BY_ROLE[me.user.role] && path.startsWith(n.href));
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-lg px-3 py-1.5 ${active ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}
                >
                  {n.label}
                </Link>
              );
            })}
            <span className="ml-2 hidden text-right text-xs leading-tight text-slate-500 sm:block">
              <span className="block font-semibold text-slate-700">{me.user.full_name}</span>
              {ROLE_LABEL[me.user.role]}
              {me.student ? ` · ${me.student.classroom.name}` : ""}
            </span>
            <button
              className="ml-1 rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-100"
              onClick={async () => {
                await signOut();
                router.replace("/login");
              }}
            >
              Salir
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
