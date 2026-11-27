"""Entrada del mando físico (AWS IoT Core → Lambda) y de los entornos inmersivos (Secciones 16 y 20)."""

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import orchestrator as orch
from app.config import get_settings
from app.db import get_db
from app.models import Content, ResponseEvent, Student
from app.schemas import DeviceEventIn
from app.serializers import category_label

router = APIRouter(prefix="/devices", tags=["dispositivos"])


def device_key(x_device_key: str | None = Header(default=None)) -> None:
    expected = get_settings().device_api_key
    # Comparación en tiempo constante; sin clave configurada el endpoint queda cerrado
    if not expected or not x_device_key or not secrets.compare_digest(x_device_key, expected):
        raise HTTPException(401, "Dispositivo no autorizado")


@router.post("/events", status_code=201, dependencies=[Depends(device_key)])
def ingest(body: DeviceEventIn, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    dup = db.scalar(select(ResponseEvent).where(ResponseEvent.message_id == body.message_id))
    if dup:
        # La pasarela reenvía al recuperar conexión: se responde igual y no se duplica (Sección 20.5)
        return {"id": dup.id, "duplicate": True, "category": category_label(dup.category)}
    st = db.scalar(select(Student).where(Student.code == body.student_code))
    c = db.get(Content, body.content_id)
    if not st or not c or c.student_id != st.id or c.status != "aprobado":
        raise HTTPException(422, "El estudiante o el material no coinciden con un material aprobado")
    if body.question_index >= len(c.adapted["exercises"]):
        raise HTTPException(422, "La pregunta no existe en ese material")
    ev = orch.build_event(st, c, body.question_index, "ABCD".index(body.selected), body.time_ms, body.confidence, body.changes, body.environment)
    ev.message_id = body.message_id
    ev.device_id = body.device_id
    if body.activity:
        ev.activity = body.activity
    db.add(ev)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        dup = db.scalar(select(ResponseEvent).where(ResponseEvent.message_id == body.message_id))
        return {"id": dup.id, "duplicate": True, "category": category_label(dup.category)}
    if ev.category == "entendio_mal":
        tasks.add_task(orch.device_reinforcement_job, ev.id)
    d = orch.decide_next(orch.topic_history(db, st.id, c.topic), c.difficulty)
    return {"id": ev.id, "duplicate": False, "correct": ev.correct, "category": category_label(ev.category), "decision": {"action": d.action, "reason": d.reason}}
