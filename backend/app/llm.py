"""Acceso al modelo de lenguaje (Gemini) con salida estructurada.

Sección 20.5: si la salida no cumple el esquema o el proveedor falla de forma temporal, se reintenta con
backoff exponencial hasta 3 veces. Si sigue fallando se lanza AgentError y el Orquestador deja el caso en
manos del docente; nunca se inventa una salida.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings

log = logging.getLogger("aprende.llm")
T = TypeVar("T", bound=BaseModel)


class AgentError(Exception):
    """El agente no produjo una salida válida tras todos los intentos."""

    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


@dataclass
class LLMResult:
    output: BaseModel
    model: str
    attempts: int
    latency_ms: int


class LLMBackend(Protocol):
    model: str

    def generate(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        """Devuelve el texto JSON producido por el modelo."""
        ...


class GeminiBackend:
    def __init__(self) -> None:
        from google import genai

        settings = get_settings()
        if not settings.gemini_api_key:
            raise AgentError("Falta GEMINI_API_KEY en el backend: los agentes no pueden trabajar sin el modelo", 0)
        self.primary = settings.gemini_model
        self.fallback = settings.gemini_fallback_model
        self.model = self.primary
        # Sin reintentos internos del SDK: los reintentos y el backoff los controla run_structured (Sección 20.5)
        self._client = genai.Client(api_key=settings.gemini_api_key, http_options={"retry_options": {"attempts": 1}, "timeout": 90_000})

    def _call(self, model: str, system: str, prompt: str, schema: type[BaseModel]) -> str:
        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config={"system_instruction": system, "response_mime_type": "application/json", "response_schema": schema, "temperature": 0.4},
        )
        return response.text or ""

    def generate(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        try:
            self.model = self.primary
            return self._call(self.primary, system, prompt, schema)
        except Exception as err:
            # Picos de demanda o cuota del modelo principal: se intenta con el de respaldo antes de esperar
            if not self.fallback or not _is_transient(err):
                raise
            self.model = self.fallback
            return self._call(self.fallback, system, prompt, schema)


_backend: LLMBackend | None = None


def get_backend() -> LLMBackend:
    global _backend
    if _backend is None:
        _backend = GeminiBackend()
    return _backend


def set_backend(backend: LLMBackend | None) -> None:
    """Permite a las pruebas sustituir el proveedor sin llamar a la API real."""
    global _backend
    _backend = backend


def _is_transient(err: Exception) -> bool:
    # Cuota (429) y errores del servidor (5xx) se reintentan; una clave inválida o un modelo inexistente no
    code = getattr(err, "code", None) or getattr(err, "status_code", None)
    return code in (429, 500, 502, 503, 504) or isinstance(err, TimeoutError | ConnectionError)


def run_structured(system: str, prompt: str, schema: type[T], check: Callable[[T], str | None] | None = None) -> LLMResult:
    """Llama al modelo y valida la salida. `check` agrega reglas de negocio; si devuelve un error se reintenta."""
    settings = get_settings()
    backend = get_backend()
    started = time.perf_counter()
    last_error = ""
    for attempt in range(1, settings.llm_max_attempts + 1):
        try:
            raw = backend.generate(system, prompt, schema)
            output = schema.model_validate(json.loads(raw))
            problem = check(output) if check else None
            if problem:
                raise ValueError(problem)
            return LLMResult(output, backend.model, attempt, int((time.perf_counter() - started) * 1000))
        except (ValidationError, json.JSONDecodeError, ValueError) as err:
            last_error = f"Salida inválida: {str(err)[:300]}"
        except AgentError:
            raise
        except Exception as err:  # noqa: BLE001 - errores del SDK del proveedor
            last_error = f"{type(err).__name__}: {str(err)[:300]}"
            if not _is_transient(err):
                raise AgentError(last_error, attempt) from err
        log.warning("Intento %s/%s fallido: %s", attempt, settings.llm_max_attempts, last_error)
        if attempt < settings.llm_max_attempts:
            time.sleep(settings.llm_backoff_seconds * 2 ** (attempt - 1))
    raise AgentError(last_error, settings.llm_max_attempts)
