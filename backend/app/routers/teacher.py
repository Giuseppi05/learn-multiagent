"""Docente (y coordinación en modo lectura y supervisión): aulas, estudiantes, generación, validación y reportes."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import orchestrator as orch
from app.access import classroom_for, content_for, student_for, visible_classroom_ids
from app.accounts import create_student
from app.auth import CurrentUser, require
from app.db import get_db
from app.llm import AgentError
from app.models import AgentRun, Classroom, Content, LearningProfile, Reinforcement, Report, ResponseEvent, Student, Submission
from app.rules import CATEGORIES, traffic_light
from app.schemas import DiagnosisRequest, GenerateRequest, InitialTestRequest, ReinforcementReview, ReviewRequest, StudentCreate, StudentUpdate
from app.serializers import category_label, classroom_view, content_summary, content_teacher_view, reinforcement_view, student_view
from app.supabase_admin import AuthAdmin, get_auth_admin, student_pin

router = APIRouter(tags=["docente"])
staff = require("docente", "admin")
teacher_only = require("docente")


def _busy(db: Session, student_id: int, kind: str) -> bool:
    return db.scalar(select(Content.id).where(Content.student_id == student_id, Content.kind == kind, Content.status == "generando")) is not None


# ---------- aulas y estudiantes ----------


@router.get("/classrooms")
def my_classrooms(me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    ids = visible_classroom_ids(db, me)
    rooms = db.scalars(select(Classroom).where(Classroom.id.in_(ids)).order_by(Classroom.grade, Classroom.section)).all() if ids else []
    return [classroom_view(r) for r in rooms]


@router.get("/classrooms/{classroom_id}/dashboard")
def classroom_dashboard(classroom_id: int, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    """Sección 17: lista con semáforo por tema, alertas y respuestas por entorno."""
    room = classroom_for(db, me, classroom_id)
    students = db.scalars(select(Student).where(Student.classroom_id == room.id).order_by(Student.code)).all()
    sids = [s.id for s in students]
    events = db.scalars(select(ResponseEvent).where(ResponseEvent.student_id.in_(sids)).order_by(ResponseEvent.id)).all() if sids else []
    by_student: dict[int, list[ResponseEvent]] = {}
    for e in events:
        by_student.setdefault(e.student_id, []).append(e)
    rows = []
    for st in students:
        evs = by_student.get(st.id, [])
        acc = sum(e.correct for e in evs) / len(evs) if evs else None
        topics: dict[str, list[ResponseEvent]] = {}
        for e in evs:
            topics.setdefault(e.topic, []).append(e)
        rows.append(
            {
                **student_view(st),
                "has_profile": orch.latest_profile(db, st.id) is not None,
                "answers": len(evs),
                "accuracy": round(acc, 2) if acc is not None else None,
                "light": traffic_light(acc),
                "topics": [{"topic": t, "light": traffic_light(sum(x.correct for x in te) / len(te)), "accuracy": round(sum(x.correct for x in te) / len(te), 2)} for t, te in topics.items()],
                "last_category": category_label(evs[-1].category) if evs else None,
            }
        )
    name = {s.id: s.user.full_name for s in students}
    alerts = []
    for e in reversed(events[-300:]):
        if e.category == "entendio_mal":
            alerts.append(
                {
                    "type": "concepto",
                    "student_id": e.student_id,
                    "student": name[e.student_id],
                    "topic": e.topic,
                    "detail": f"Eligió «{e.answer}» con confianza {e.confidence} de 5.",
                    "created_at": e.created_at,
                }
            )
        elif e.time_ms > 2 * e.expected_ms or e.changes >= 3:
            why = f"tardó {round(e.time_ms / 1000)} s (esperado {round(e.expected_ms / 1000)} s)" if e.time_ms > 2 * e.expected_ms else f"cambió {e.changes} veces de respuesta"
            alerts.append(
                {
                    "type": "tiempo" if e.time_ms > 2 * e.expected_ms else "indecision",
                    "student_id": e.student_id,
                    "student": name[e.student_id],
                    "topic": e.topic,
                    "detail": why.capitalize() + ".",
                    "created_at": e.created_at,
                }
            )
    total = len(events)
    ok = sum(e.correct for e in events)
    pending_c = db.scalars(select(Content.id).where(Content.student_id.in_(sids), Content.status.in_(["pendiente", "error_ia", "requiere_docente"]))).all() if sids else []
    pending_r = db.scalars(select(Reinforcement.id).where(Reinforcement.student_id.in_(sids), Reinforcement.status == "pendiente")).all() if sids else []
    return {
        "classroom": classroom_view(room),
        "kpis": {
            "students": len(students),
            "answers": total,
            "accuracy": round(ok / total, 2) if total else None,
            "avg_time_s": round(sum(e.time_ms for e in events) / total / 1000, 1) if total else None,
            "to_review": len(pending_c) + len(pending_r),
        },
        "students": rows,
        "alerts": alerts[:20],
        "by_environment": {env: sum(e.environment == env for e in events) for env in ["web", "mando", "AR", "VR", "MV"]},
    }


@router.post("/classrooms/{classroom_id}/students", status_code=201)
def add_student(classroom_id: int, body: StudentCreate, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db), admin: AuthAdmin = Depends(get_auth_admin)):
    room = classroom_for(db, me, classroom_id)
    st, pin = create_student(db, admin, room, body.full_name, body.username, body.interests)
    # El PIN solo se muestra en esta respuesta para que el docente se lo entregue al estudiante
    return {"student": student_view(st), "pin": pin}


@router.get("/students/{student_id}")
def student_detail(student_id: int, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    st = student_for(db, me, student_id)
    profiles = db.scalars(select(LearningProfile).where(LearningProfile.student_id == st.id).order_by(LearningProfile.id.desc()).limit(5)).all()
    contents = db.scalars(select(Content).where(Content.student_id == st.id).order_by(Content.id.desc())).all()
    events = db.scalars(select(ResponseEvent).where(ResponseEvent.student_id == st.id).order_by(ResponseEvent.id.desc()).limit(40)).all()
    reports = db.scalars(select(Report).where(Report.student_id == st.id).order_by(Report.id.desc()).limit(5)).all()
    return {
        "student": student_view(st),
        "profile": profiles[0].data if profiles else None,
        "profile_history": [{"source": p.source, "level": p.data.get("level"), "created_at": p.created_at} for p in profiles],
        "topics": orch.topic_summary(db, st.id),
        "contents": [content_summary(c) for c in contents if c.status != "reemplazado"],
        "events": [
            {
                "id": e.id,
                "topic": e.topic,
                "question": e.question,
                "answer": e.answer,
                "correct": e.correct,
                "time_ms": e.time_ms,
                "expected_ms": e.expected_ms,
                "confidence": e.confidence,
                "changes": e.changes,
                "environment": e.environment,
                "category": category_label(e.category),
                "category_key": e.category,
                "created_at": e.created_at,
            }
            for e in events
        ],
        "reports": [{"id": r.id, "status": r.status, "data": r.data, "error": r.error, "created_at": r.created_at, "automatic": r.requested_by is None} for r in reports],
    }


@router.get("/students/{student_id}/progress")
def student_progress(student_id: int, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    """Sección 17.2: avance del acierto y de la velocidad de respuesta entre sesiones."""
    st = student_for(db, me, student_id)
    subs = db.scalars(select(Submission).where(Submission.student_id == st.id).order_by(Submission.id)).all()
    points = []
    for s in subs:
        evs = db.scalars(select(ResponseEvent).where(ResponseEvent.submission_id == s.id)).all()
        if not evs:
            continue
        c = db.get(Content, s.content_id)
        points.append(
            {
                "submission_id": s.id,
                "date": s.created_at,
                "topic": c.topic,
                "kind": c.kind,
                "difficulty": c.difficulty,
                "accuracy": round(sum(e.correct for e in evs) / len(evs), 2),
                "avg_time_s": round(sum(e.time_ms for e in evs) / len(evs) / 1000, 1),
                "decision": (s.decision or {}).get("action"),
            }
        )
    return points


@router.patch("/students/{student_id}")
def update_student(student_id: int, body: StudentUpdate, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    st = student_for(db, me, student_id)
    st.interests = body.interests
    db.commit()
    return student_view(st)


@router.post("/students/{student_id}/reset-pin")
def reset_pin(student_id: int, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db), admin: AuthAdmin = Depends(get_auth_admin)):
    st = student_for(db, me, student_id)
    pin = student_pin()
    admin.set_password(st.user_id, pin)
    return {"pin": pin}


# ---------- diagnóstico, prueba inicial y generación ----------


@router.post("/students/{student_id}/initial-test", status_code=202)
def request_initial_test(student_id: int, body: InitialTestRequest, tasks: BackgroundTasks, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    """Sección 20, paso 4: sin perfil, el estudiante rinde una prueba inicial generada por el Agente Generador."""
    st = student_for(db, me, student_id)
    if _busy(db, st.id, "prueba_inicial"):
        raise HTTPException(409, "Ya se está generando una prueba inicial para este estudiante")
    c = orch.create_content(db, st, "prueba_inicial", body.area, f"Prueba inicial de {body.area}", 2, "docente", me.id)
    db.commit()
    tasks.add_task(orch.content_job, c.id)
    return content_summary(c)


@router.post("/students/{student_id}/diagnosis")
def diagnose(student_id: int, body: DiagnosisRequest, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    """CU-IA-01 con observaciones del docente o una prueba rendida fuera de la plataforma."""
    st = student_for(db, me, student_id)
    if not body.teacher_notes.strip() and not body.external_test.strip():
        raise HTTPException(422, "Escribe tus observaciones o los resultados de una prueba")
    try:
        return {"profile": orch.diagnose_by_teacher(db, st, body.teacher_notes, body.external_test)}
    except AgentError as err:
        raise HTTPException(502, f"El Agente de Diagnóstico no respondió: {err}") from err


@router.post("/students/{student_id}/contents", status_code=202)
def request_content(student_id: int, body: GenerateRequest, tasks: BackgroundTasks, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    """CU-IA-02 y 03. El material queda pendiente de validación docente."""
    st = student_for(db, me, student_id)
    if orch.latest_profile(db, st.id) is None:
        # Sección 20.4: sin perfil no se genera material; primero va la prueba inicial o el diagnóstico
        raise HTTPException(409, "El estudiante todavía no tiene perfil de aprendizaje: aplica la prueba inicial o registra un diagnóstico")
    c = orch.create_content(db, st, "material", body.area, body.topic.strip(), body.difficulty, "docente", me.id)
    db.commit()
    tasks.add_task(orch.content_job, c.id)
    return content_summary(c)


# ---------- validación docente ----------


@router.get("/contents")
def list_contents(status: str | None = None, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    ids = visible_classroom_ids(db, me)
    if not ids:
        return []
    q = select(Content).join(Student, Student.id == Content.student_id).where(Student.classroom_id.in_(ids)).order_by(Content.id.desc())
    if status:
        q = q.where(Content.status.in_(status.split(",")))
    return [content_summary(c) for c in db.scalars(q.limit(200)).all()]


@router.get("/contents/{content_id}")
def get_content(content_id: int, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    return content_teacher_view(content_for(db, me, content_id))


@router.post("/contents/{content_id}/review")
def review(content_id: int, body: ReviewRequest, tasks: BackgroundTasks, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    c = content_for(db, me, content_id)
    if c.status != "pendiente":
        raise HTTPException(409, f"Este contenido está «{c.status}» y no se puede revisar")
    if orch.review_content(db, c, me.id, body.decision, body.note.strip()):
        tasks.add_task(orch.content_job, c.id, body.note.strip())
    return content_summary(c)


@router.post("/contents/{content_id}/retry", status_code=202)
def retry(content_id: int, tasks: BackgroundTasks, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    """Sección 20.5: tras un fallo del modelo el docente decide si reintentar."""
    c = content_for(db, me, content_id)
    if c.status != "error_ia":
        raise HTTPException(409, "Solo se reintenta un contenido que falló al generarse")
    c.status = "generando"
    c.error = ""
    db.commit()
    last_note = c.reviews[-1].note if c.reviews and c.reviews[-1].decision == "devuelto" else ""
    tasks.add_task(orch.content_job, c.id, last_note)
    return content_summary(c)


@router.get("/reinforcements")
def list_reinforcements(status: str | None = None, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    ids = visible_classroom_ids(db, me)
    if not ids:
        return []
    q = select(Reinforcement, Student).join(Student, Student.id == Reinforcement.student_id).where(Student.classroom_id.in_(ids)).order_by(Reinforcement.id.desc())
    if status:
        q = q.where(Reinforcement.status.in_(status.split(",")))
    return [reinforcement_view(r, st) for r, st in db.execute(q.limit(200)).all()]


@router.post("/reinforcements/{rid}/review")
def review_reinforcement(rid: int, body: ReinforcementReview, me: CurrentUser = Depends(teacher_only), db: Session = Depends(get_db)):
    r = db.get(Reinforcement, rid)
    if not r:
        raise HTTPException(404, "Actividad no encontrada")
    st = student_for(db, me, r.student_id)
    if r.status != "pendiente":
        raise HTTPException(409, "Esta actividad ya fue revisada")
    r.status = "aprobado" if body.approve else "rechazado"
    r.reviewer_id = me.id
    db.commit()
    return reinforcement_view(r, st)


# ---------- reportes y trazabilidad ----------


@router.post("/students/{student_id}/reports", status_code=202)
def request_report(student_id: int, tasks: BackgroundTasks, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    st = student_for(db, me, student_id)
    rep = Report(student_id=st.id, requested_by=me.id, status="generando")
    db.add(rep)
    db.commit()
    tasks.add_task(orch.report_job, rep.id)
    return {"id": rep.id, "status": rep.status}


@router.get("/reports/{report_id}")
def get_report(report_id: int, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    rep = db.get(Report, report_id)
    if not rep:
        raise HTTPException(404, "Reporte no encontrado")
    student_for(db, me, rep.student_id)
    return {"id": rep.id, "status": rep.status, "data": rep.data, "error": rep.error, "created_at": rep.created_at}


@router.get("/agent-runs")
def agent_runs(student_id: int | None = None, limit: int = 50, me: CurrentUser = Depends(staff), db: Session = Depends(get_db)):
    ids = visible_classroom_ids(db, me)
    sids = list(db.scalars(select(Student.id).where(Student.classroom_id.in_(ids))).all()) if ids else []
    if student_id is not None:
        student_for(db, me, student_id)
        sids = [student_id]
    if not sids:
        return []
    rows = db.scalars(select(AgentRun).where(AgentRun.student_id.in_(sids)).order_by(AgentRun.id.desc()).limit(min(limit, 200))).all()
    names = {s.id: s.user.full_name for s in db.scalars(select(Student).where(Student.id.in_({r.student_id for r in rows}))).all()} if rows else {}
    return [
        {
            "id": r.id,
            "agent": r.agent,
            "student_id": r.student_id,
            "student_name": names.get(r.student_id),
            "content_id": r.content_id,
            "status": r.status,
            "model": r.model,
            "attempts": r.attempts,
            "latency_ms": r.latency_ms,
            "input": r.input,
            "output": r.output,
            "error": r.error,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/categories")
def categories(_: CurrentUser = Depends(staff)):
    return CATEGORIES
