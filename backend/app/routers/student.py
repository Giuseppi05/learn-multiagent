"""Estudiante: su prueba inicial, sus materiales aprobados, el envío de respuestas y el asistente de dudas."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import orchestrator as orch
from app.access import own_material
from app.auth import CurrentUser, require
from app.db import get_db
from app.llm import AgentError
from app.models import Content, Submission
from app.schemas import AssistantIn, SubmissionIn
from app.serializers import category_label, material_student_view

router = APIRouter(prefix="/my", tags=["estudiante"])
student_only = require("estudiante")


@router.get("/home")
def home(me: CurrentUser = Depends(student_only), db: Session = Depends(get_db)):
    st = me.student
    approved = db.scalars(select(Content).where(Content.student_id == st.id, Content.status == "aprobado").order_by(Content.id.desc())).all()
    done = set(db.scalars(select(Submission.content_id).where(Submission.student_id == st.id)).all())
    items = [{**material_student_view(c), "completed": c.id in done, "exercise_count": len((c.adapted or {}).get("exercises", []))} for c in approved]
    for i in items:
        i.pop("exercises")
    return {
        "name": me.user.full_name,
        "classroom": st.classroom.name,
        "has_profile": orch.latest_profile(db, st.id) is not None,
        # La prueba inicial pendiente va primero: sin ella el sistema no conoce al estudiante
        "initial_tests": [i for i in items if i["kind"] == "prueba_inicial" and not i["completed"]],
        "materials": [i for i in items if i["kind"] == "material"],
    }


@router.get("/materials/{content_id}")
def material(content_id: int, me: CurrentUser = Depends(student_only), db: Session = Depends(get_db)):
    c = own_material(db, me, content_id)
    return material_student_view(c)


@router.post("/materials/{content_id}/submit", status_code=201)
def submit(content_id: int, body: SubmissionIn, tasks: BackgroundTasks, me: CurrentUser = Depends(student_only), db: Session = Depends(get_db)):
    c = own_material(db, me, content_id)
    n = len(c.adapted["exercises"])
    if any(a.index >= n for a in body.answers):
        raise HTTPException(422, "Hay una respuesta para un ejercicio que no existe")
    if c.kind == "prueba_inicial":
        if len(body.answers) != n:
            raise HTTPException(422, "La prueba inicial se envía completa")
        if db.scalar(select(Submission.id).where(Submission.content_id == c.id)):
            raise HTTPException(409, "Ya rendiste esta prueba inicial")
    sub, events = orch.record_answers(db, me.student, c, [a.model_dump() for a in body.answers], body.environment)
    tasks.add_task(orch.submission_job, sub.id)
    return {"submission_id": sub.id, "results": _results(c, events)}


def _results(c: Content, events) -> list[dict]:
    show_answers = c.kind == "material"
    out = []
    for e in events:
        ex = c.adapted["exercises"][e.question_index]
        item = {"index": e.question_index, "correct": e.correct, "category": category_label(e.category), "category_key": e.category}
        # En la prueba inicial no se muestran las respuestas: es una medición, no una práctica
        if show_answers:
            item["correct_option"] = ex["options"][ex["correct_index"]]
            item["explanation"] = ex["explanation"]
        out.append(item)
    return out


@router.get("/submissions/{submission_id}")
def submission_status(submission_id: int, me: CurrentUser = Depends(student_only), db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub or sub.student_id != me.student.id:
        raise HTTPException(404, "Envío no encontrado")
    feedback = sub.feedback if sub.feedback and "error" not in sub.feedback else None
    return {
        "status": sub.status,
        "feedback": feedback,
        "has_next_material": sub.next_content_id is not None,
        "decision": (sub.decision or {}).get("action"),
    }


@router.get("/materials/{content_id}/assistant")
def assistant_log(content_id: int, me: CurrentUser = Depends(student_only), db: Session = Depends(get_db)):
    c = own_material(db, me, content_id)
    return orch.assistant_history(db, me.student.id, c.id)


@router.post("/materials/{content_id}/assistant")
def ask(content_id: int, body: AssistantIn, me: CurrentUser = Depends(student_only), db: Session = Depends(get_db)):
    """CU-IA-05: explicación alternativa sobre el material en pantalla."""
    c = own_material(db, me, content_id)
    if c.kind == "prueba_inicial":
        raise HTTPException(403, "El asistente no está disponible durante la prueba inicial")
    try:
        return orch.ask_assistant(db, me.student, c, body.question)
    except AgentError as err:
        raise HTTPException(502, "El asistente no pudo responder ahora. Intenta de nuevo en un momento.") from err
