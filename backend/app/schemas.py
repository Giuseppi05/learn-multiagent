"""Esquemas Pydantic: salida estructurada de cada agente y contratos de la API."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------- Salidas de los agentes (se validan antes de guardarse) ----------


class LearningProfileOut(BaseModel):
    level: Literal["inicio", "en_proceso", "logrado", "destacado"]
    reading_level: Literal["inicial", "intermedio", "avanzado"]
    pace: Literal["lento", "medio", "rapido"]
    strengths: list[str]
    gaps: list[str]
    interests: list[str]
    recommendation: str


class Exercise(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str
    expected_seconds: int = Field(ge=5, le=180)


class ContentOut(BaseModel):
    title: str
    explanation: str
    examples: list[str]
    exercises: list[Exercise] = Field(min_length=3, max_length=6)
    reinforcement_activity: str


class AdaptedContentOut(ContentOut):
    adaptation_notes: str


class QuestionFeedback(BaseModel):
    index: int
    correct: bool
    error_type: Literal["ninguno", "conceptual", "procedimental", "comprension_lectora"]
    message: str


class FeedbackOut(BaseModel):
    overall: str
    items: list[QuestionFeedback]


class ReinforcementOut(BaseModel):
    suspected_misconception: str
    activity_title: str
    steps: list[str] = Field(min_length=1)
    materials: list[str]


class AssistantOut(BaseModel):
    answer: str
    follow_up: str


class ReportOut(BaseModel):
    summary: str
    progress: list[str]
    difficulties: list[str]
    recommendations: list[str]


# ---------- Contratos de la API ----------

AREAS = ("Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social")
Environment = Literal["web", "mando", "AR", "VR", "MV"]
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,29}$")


class PasswordChange(BaseModel):
    password: str = Field(min_length=8, max_length=72)


class TeacherCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=200)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Correo inválido")
        return v


class ClassroomCreate(BaseModel):
    year: int = Field(ge=2024, le=2100)
    grade: int = Field(ge=1, le=6)
    section: str = Field(min_length=1, max_length=5)
    teacher_id: str | None = None

    @field_validator("section")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.strip().upper()


class ClassroomUpdate(BaseModel):
    teacher_id: str | None


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    username: str
    interests: str = Field(default="", max_length=200)

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_RE.fullmatch(v):
            raise ValueError("Usuario de 3 a 30 caracteres: letras minúsculas, números, punto, guion o guion bajo")
        return v


class StudentUpdate(BaseModel):
    interests: str = Field(max_length=200)


class DiagnosisRequest(BaseModel):
    teacher_notes: str = Field(default="", max_length=1500)
    external_test: str = Field(default="", max_length=3000, description="Resultados de una prueba tomada fuera de la plataforma, si existen")


class InitialTestRequest(BaseModel):
    area: Literal["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social"] = "Matemática"


class GenerateRequest(BaseModel):
    area: Literal["Matemática", "Comunicación", "Ciencia y Tecnología", "Personal Social"] = "Matemática"
    topic: str = Field(min_length=2, max_length=120)
    difficulty: int = Field(default=2, ge=1, le=4)


class ReviewRequest(BaseModel):
    decision: Literal["aprobado", "devuelto", "rechazado"]
    note: str = Field(default="", max_length=1500)

    @model_validator(mode="after")
    def note_when_returned(self) -> "ReviewRequest":
        # Devolver sin observaciones haría que el Generador repita lo mismo
        if self.decision == "devuelto" and len(self.note.strip()) < 5:
            raise ValueError("Escribe las observaciones para que el Agente Generador corrija el material")
        return self


class ReinforcementReview(BaseModel):
    approve: bool


class AnswerIn(BaseModel):
    index: int = Field(ge=0)
    selected: int = Field(ge=0, le=3)
    time_ms: int = Field(gt=0, le=3_600_000)
    confidence: int = Field(ge=1, le=5)
    changes: int = Field(default=0, ge=0, le=50)


class SubmissionIn(BaseModel):
    answers: list[AnswerIn] = Field(min_length=1)
    environment: Environment = "web"

    @model_validator(mode="after")
    def unique_indexes(self) -> "SubmissionIn":
        # Un mismo ejercicio repetido inflaría el acierto y la ventana de decisión del Orquestador
        indexes = [a.index for a in self.answers]
        if len(indexes) != len(set(indexes)):
            raise ValueError("Cada ejercicio se responde una sola vez por envío")
        return self


class DeviceEventIn(BaseModel):
    """Mensaje del mando físico (vía AWS IoT/Lambda) o de un entorno inmersivo, con los campos de la Sección 16."""

    message_id: str = Field(min_length=1, max_length=80)
    device_id: str = Field(min_length=1, max_length=60)
    student_code: str = Field(min_length=1, max_length=20)
    content_id: int
    question_index: int = Field(ge=0)
    selected: Literal["A", "B", "C", "D"]
    time_ms: int = Field(gt=0, le=3_600_000)
    confidence: int = Field(ge=1, le=5)
    changes: int = Field(default=0, ge=0, le=50)
    environment: Environment = "mando"
    activity: str = Field(default="", max_length=40)


class AssistantIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
