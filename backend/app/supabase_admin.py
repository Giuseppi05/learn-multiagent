"""Cliente mínimo de la API de administración de Supabase Auth (crear cuentas y restablecer contraseñas).

Usa la clave secreta del proyecto, que solo existe en el backend.
"""

import secrets

import httpx
from fastapi import HTTPException

from app.config import get_settings


class AuthAdmin:
    def __init__(self) -> None:
        s = get_settings()
        if not s.supabase_url or not s.supabase_secret_key:
            raise HTTPException(503, "Falta configurar SUPABASE_URL y SUPABASE_SECRET_KEY en el backend")
        self._base = f"{s.supabase_url}/auth/v1/admin/users"
        self._headers = {"apikey": s.supabase_secret_key, "Authorization": f"Bearer {s.supabase_secret_key}"}

    def _call(self, method: str, url: str, body: dict | None = None) -> dict:
        r = httpx.request(method, url, headers=self._headers, json=body, timeout=15)
        if r.status_code >= 400:
            detail = r.json().get("msg") or r.json().get("message") or r.text if r.content else r.reason_phrase
            raise HTTPException(400 if r.status_code < 500 else 502, f"Supabase Auth: {detail}")
        return r.json() if r.content else {}

    def create_user(self, email: str, password: str, role: str) -> str:
        """Crea la cuenta ya confirmada (no se envían correos) y devuelve su id."""
        data = self._call("POST", self._base, {"email": email, "password": password, "email_confirm": True, "app_metadata": {"role": role}})
        return data["id"]

    def set_password(self, user_id: str, password: str) -> None:
        self._call("PUT", f"{self._base}/{user_id}", {"password": password})

    def set_banned(self, user_id: str, banned: bool) -> None:
        # Supabase no tiene "desactivar": se usa un baneo largo, reversible
        self._call("PUT", f"{self._base}/{user_id}", {"ban_duration": "876000h" if banned else "none"})

    def delete_user(self, user_id: str) -> None:
        self._call("DELETE", f"{self._base}/{user_id}")


def get_auth_admin() -> AuthAdmin:
    return AuthAdmin()


def temporary_password() -> str:
    """Contraseña temporal para docentes; se cambia en el primer ingreso."""
    return secrets.token_urlsafe(9)


def student_pin() -> str:
    # Seis dígitos: lo mínimo que acepta Supabase y algo que un niño de primaria puede recordar
    return f"{secrets.randbelow(10**6):06d}"
