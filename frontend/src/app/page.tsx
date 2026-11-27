"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { HOME_BY_ROLE, useAuth } from "@/lib/auth";
import { Spinner } from "@/lib/ui";

export default function Root() {
  const { me } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (me === null) router.replace("/login");
    else if (me) router.replace(me.user.must_change_password ? "/cambiar-clave" : HOME_BY_ROLE[me.user.role]);
  }, [me, router]);
  return (
    <div className="grid min-h-screen place-items-center">
      <Spinner label="Cargando…" />
    </div>
  );
}
