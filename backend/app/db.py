from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_url(url: str) -> str:
    # Supabase entrega la cadena como postgresql://; SQLAlchemy necesita saber que el driver es psycopg 3
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


settings = get_settings()
# check_same_thread solo aplica a SQLite; FastAPI atiende peticiones en varios hilos
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(_engine_url(settings.database_url), connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
