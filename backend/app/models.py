"""Modelo de datos (Supabase PostgreSQL). Solo el Orquestador y los servicios del backend escriben aquí."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """Perfil de la aplicación ligado a la cuenta de Supabase Auth (mismo id).

    El rol vive aquí y no en el token: el docente o la coordinación lo asignan, el usuario no puede cambiarlo.
    """

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))  # admin | docente | estudiante
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    username: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Classroom(Base):
    __tablename__ = "classrooms"
    __table_args__ = (UniqueConstraint("year", "grade", "section", name="uq_classroom"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    grade: Mapped[int] = mapped_column(Integer)  # 1 a 6 de primaria
    section: Mapped[str] = mapped_column(String(5))
    teacher_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    teacher: Mapped[User | None] = relationship()

    @property
    def name(self) -> str:
        return f"{self.grade}.º {self.section}"


class Student(Base):
    """El código interno es lo único que identifica al estudiante ante el LLM (Sección 10: protección de datos)."""

    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    interests: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    user: Mapped[User] = relationship()
    classroom: Mapped[Classroom] = relationship()


class LearningProfile(Base):
    """Salida del Agente de Diagnóstico (CU-IA-01). Se conserva el historial: el último es el vigente."""

    __tablename__ = "learning_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    source: Mapped[str] = mapped_column(String(30))  # prueba_inicial | docente | orquestador
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Content(Base):
    """Material o prueba inicial generados por los agentes.

    Estados: generando → pendiente → aprobado | devuelto (se regenera) | rechazado.
    También: error_ia (el modelo no respondió), requiere_docente (3 devoluciones) y reemplazado.
    """

    __tablename__ = "contents"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="material")  # material | prueba_inicial
    area: Mapped[str] = mapped_column(String(60))
    topic: Mapped[str] = mapped_column(String(120))
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(20), default="generando", index=True)
    origin: Mapped[str] = mapped_column(String(40), default="docente")
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    base: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    adapted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    returns_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student] = relationship()
    reviews: Mapped[list["ContentReview"]] = relationship(order_by="ContentReview.id", back_populates="content")


class ContentReview(Base):
    """Cada decisión del docente queda registrada (trazabilidad de aprobaciones, Sección 20.1)."""

    __tablename__ = "content_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(20))  # aprobado | devuelto | rechazado
    note: Mapped[str] = mapped_column(Text, default="")
    # Versión revisada: al devolver, el material se regenera y sin esta copia se perdería lo que vio el docente
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    content: Mapped[Content] = relationship(back_populates="reviews")


class Submission(Base):
    """Un envío completo del estudiante. La retroalimentación del Evaluador llega después, en segundo plano."""

    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"), index=True)
    environment: Mapped[str] = mapped_column(String(10), default="web")
    status: Mapped[str] = mapped_column(String(20), default="procesando")  # procesando | listo | error_ia
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    next_content_id: Mapped[int | None] = mapped_column(ForeignKey("contents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ResponseEvent(Base):
    """Misma estructura que el mensaje del mando físico (Sección 16), más entorno y actividad."""

    __tablename__ = "response_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    content_id: Mapped[int | None] = mapped_column(ForeignKey("contents.id"), nullable=True)
    submission_id: Mapped[int | None] = mapped_column(ForeignKey("submissions.id"), nullable=True, index=True)
    # La pasarela reenvía los mensajes al recuperar conexión: la restricción única evita duplicados (Sección 20.5)
    message_id: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    device_id: Mapped[str] = mapped_column(String(60), default="")
    topic: Mapped[str] = mapped_column(String(120), index=True)
    question_index: Mapped[int] = mapped_column(Integer, default=0)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(String(200))
    correct: Mapped[bool] = mapped_column(Boolean)
    time_ms: Mapped[int] = mapped_column(Integer)
    expected_ms: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[int] = mapped_column(Integer)
    changes: Mapped[int] = mapped_column(Integer, default=0)
    environment: Mapped[str] = mapped_column(String(10), default="web")
    activity: Mapped[str] = mapped_column(String(40), default="")
    category: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Reinforcement(Base):
    """Propuesta del Agente de Refuerzo Conceptual (Sección 21): una por envío, con todos sus errores de concepto."""

    __tablename__ = "reinforcements"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    submission_id: Mapped[int | None] = mapped_column(ForeignKey("submissions.id"), nullable=True)
    topic: Mapped[str] = mapped_column(String(120))
    event_ids: Mapped[list] = mapped_column(JSON, default=list)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generando", index=True)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Report(Base):
    """Reporte de avance (CU-IA-06)."""

    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generando")
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentRun(Base):
    """Trazabilidad: cada llamada a un agente queda registrada con su entrada, salida, modelo e intentos."""

    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent: Mapped[str] = mapped_column(String(40))
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    content_id: Mapped[int | None] = mapped_column(ForeignKey("contents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(10))  # ok | error
    model: Mapped[str] = mapped_column(String(60))
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
