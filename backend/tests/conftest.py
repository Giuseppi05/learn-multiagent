import os
import tempfile
import time
import uuid

# La configuración se lee al importar la app: el entorno de prueba se fija antes de cualquier import de app
_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_db}",
        "GEMINI_API_KEY": "clave-de-prueba",
        "SUPABASE_URL": "https://proyecto-de-prueba.supabase.co",
        "SUPABASE_SECRET_KEY": "secreto-de-prueba",
        "SUPABASE_JWT_SECRET": "",
        "DEVICE_API_KEY": "clave-dispositivo",
        "LLM_BACKOFF_SECONDS": "0",
    }
)

import jwt  # noqa: E402
import pytest  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, llm  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.supabase_admin import get_auth_admin  # noqa: E402
from tests.fakes import FakeAuthAdmin, FakeLLM  # noqa: E402

# Misma familia de claves que usa Supabase (ECC P-256), generada solo para las pruebas
_private_key = ec.generate_private_key(ec.SECP256R1())


class _Key:
    key = _private_key.public_key()


class _FakeJWKS:
    def get_signing_key_from_jwt(self, token: str) -> _Key:
        return _Key()


auth._jwks_client = lambda: _FakeJWKS()


def token_for(user_id: str, expired: bool = False) -> str:
    now = int(time.time())
    claims = {"sub": user_id, "aud": "authenticated", "role": "authenticated", "iat": now, "exp": now - 10 if expired else now + 3600}
    return jwt.encode(claims, _private_key, algorithm="ES256")


def headers_for(user_id: str) -> dict:
    return {"Authorization": f"Bearer {token_for(user_id)}"}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def fake_llm():
    backend = FakeLLM()
    llm.set_backend(backend)
    yield backend
    llm.set_backend(None)


@pytest.fixture
def auth_admin():
    fake = FakeAuthAdmin()
    app.dependency_overrides[get_auth_admin] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_auth_admin, None)


@pytest.fixture
def client(fake_llm, auth_admin):
    return TestClient(app)


@pytest.fixture
def admin_headers():
    uid = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(User(id=uid, role="admin", full_name="Coordinación", email="coordinacion@ie.edu.pe"))
        db.commit()
    return headers_for(uid)
