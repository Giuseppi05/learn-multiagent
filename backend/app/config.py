from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Rutas fijas a la carpeta backend para que el servidor funcione igual desde cualquier directorio
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuración leída del entorno o del archivo .env. Ninguna credencial vive en el código."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # Modelo de lenguaje (Sección 7): sin clave el sistema no genera contenido, no hay modo simulado
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    # Respaldo ante picos de demanda (503) o cuota (429) del modelo principal
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
    # Sección 20.5: hasta 3 intentos por salida JSON inválida o error temporal del proveedor
    llm_max_attempts: int = 3
    llm_backoff_seconds: float = 1.5

    # Supabase: PostgreSQL (DATABASE_URL) y autenticación (URL y clave secreta para la API de administración)
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'aprende.db').as_posix()}"
    supabase_url: str = ""
    supabase_secret_key: str = ""
    # Solo para proyectos con la firma JWT antigua (HS256); los proyectos nuevos se verifican con JWKS
    supabase_jwt_secret: str = ""
    # Los estudiantes no tienen correo: se les asigna uno interno no entregable (TLD reservado)
    student_email_domain: str = "estudiantes.aprende.invalid"

    # Mando físico y entornos inmersivos (Sección 16): se autentican con una clave de dispositivo
    device_api_key: str = ""

    cors_origins: str = "http://localhost:3000"
    # Ventana de respuestas que usa el Orquestador para decidir (Sección 16: últimas 3 a 5)
    decision_window: int = 5
    # Sección 20.5: tras 3 devoluciones del docente el material pasa a su cargo
    max_teacher_returns: int = 3

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
