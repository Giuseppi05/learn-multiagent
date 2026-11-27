"""Autenticación con Supabase Auth y autorización por rol.

El frontend inicia sesión directamente con Supabase y envía el access token. Aquí solo se verifica la firma
y se carga el perfil de la aplicación (tabla users), que es la fuente del rol.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Student, User

ROLES = ("admin", "docente", "estudiante")


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    # Los proyectos nuevos firman con claves asimétricas publicadas en el JWKS; el cliente las cachea
    return jwt.PyJWKClient(f"{get_settings().supabase_url}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=3600)


def decode_token(token: str) -> dict:
    """Valida firma, expiración y audiencia del token de Supabase. Devuelve sus claims."""
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(401, "Token no aceptado")
            return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
        key = _jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["ES256", "RS256"], audience="authenticated")
    except jwt.PyJWTError as err:
        raise HTTPException(401, "Sesión inválida o vencida") from err


@dataclass
class CurrentUser:
    user: User
    student: Student | None = None

    @property
    def id(self) -> str:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Falta iniciar sesión")
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    user = db.get(User, claims.get("sub", ""))
    if not user or not user.active:
        # Una cuenta válida en Supabase pero sin perfil (o desactivada) no tiene acceso al sistema
        raise HTTPException(403, "Tu cuenta no está habilitada en el sistema")
    student = db.query(Student).filter(Student.user_id == user.id).one_or_none() if user.role == "estudiante" else None
    return CurrentUser(user, student)


def require(*roles: str) -> Callable[..., CurrentUser]:
    def guard(me: CurrentUser = Depends(current_user)) -> CurrentUser:
        if me.role not in roles:
            raise HTTPException(403, "No tienes permiso para esta acción")
        return me

    return guard
