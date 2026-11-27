"use client";

import { useState } from "react";
import { btnGhost, btnPrimary, Modal } from "@/lib/ui";

/** Muestra una credencial una sola vez: el sistema no la guarda, así que no se puede volver a consultar. */
export function CredentialModal({ open, onClose, title, who, login, secret, secretLabel }: { open: boolean; onClose: () => void; title: string; who: string; login: string; secret: string; secretLabel: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-slate-600">
        Entrégale estos datos a <b>{who}</b>. Por seguridad no se volverán a mostrar.
      </p>
      <dl className="space-y-2 rounded-xl bg-slate-50 p-4 font-mono text-sm">
        <div>
          <dt className="text-xs uppercase text-slate-500">Usuario</dt>
          <dd className="font-semibold">{login}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase text-slate-500">{secretLabel}</dt>
          <dd className="text-lg font-bold tracking-wider">{secret}</dd>
        </div>
      </dl>
      <div className="flex justify-end gap-2">
        <button
          className={btnGhost}
          onClick={async () => {
            await navigator.clipboard.writeText(`Usuario: ${login}\n${secretLabel}: ${secret}`);
            setCopied(true);
          }}
        >
          {copied ? "Copiado" : "Copiar"}
        </button>
        <button className={btnPrimary} onClick={onClose}>
          Ya lo anoté
        </button>
      </div>
    </Modal>
  );
}
