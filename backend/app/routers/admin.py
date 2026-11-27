"""Coordinación: cuentas de docentes, aulas y vista institucional."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts import create_staff
from app.auth import CurrentUser, require
from app.db import get_db
from app.models import Classroom, Content, Reinforcement, ResponseEvent, Student, User
from app.rules import traffic_light
from app.schemas import ClassroomCreate, ClassroomUpdate, TeacherCreate
from app.serializers import classroom_view, user_view
from app.supabase_admin import AuthAdmin, get_auth_admin, temporary_password

router = APIRouter(prefix="/admin", tags=["coordinación"])
admin_only = require("admin")


@router.get("/teachers")
def teachers(_: CurrentUser = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.role == "docente").order_by(User.full_name)).all()
    rooms = db.scalars(select(Classroom)).all()
    return [{**user_view(u), "classrooms": [r.name for r in rooms if r.teacher_id == u.id]} for u in rows]


@router.post("/teachers", status_code=201)
def create_teacher(body: TeacherCreate, _: CurrentUser = Depends(admin_only), db: Session = Depends(get_db), admin: AuthAdmin = Depends(get_auth_admin)):
    user, password = create_staff(db, admin, body.full_name, body.email, "docente")
    # La contraseña temporal solo se devuelve aquí: no se guarda en la base del sistema
    return {"teacher": user_view(user), "temporary_password": password}


@router.post("/teachers/{user_id}/reset-password")
def reset_teacher_password(user_id: str, _: CurrentUser = Depends(admin_only), db: Session = Depends(get_db), admin: AuthAdmin = Depends(get_auth_admin)):
    user = db.get(User, user_id)
    if not user or user.role != "docente":
        raise HTTPException(404, "Docente no encontrado")
    password = temporary_password()
    admin.set_password(user.id, password)
    user.must_change_password = True
    db.commit()
    return {"temporary_password": password}


@router.post("/teachers/{user_id}/active")
def set_teacher_active(user_id: str, active: bool, _: CurrentUser = Depends(admin_only), db: Session = Depends(get_db), admin: AuthAdmin = Depends(get_auth_admin)):
    user = db.get(User, user_id)
    if not user or user.role != "docente":
        raise HTTPException(404, "Docente no encontrado")
    admin.set_banned(user.id, not active)
    user.active = active
    db.commit()
    return user_view(user)


@router.get("/classrooms")
def classrooms(_: CurrentUser = Depends(admin_only), db: Session = Depends(get_db)):
    return [classroom_view(c) for c in db.scalars(select(Classroom).order_by(Classroom.year.desc(), Classroom.grade, Classroom.section)).all()]


def _teacher_or_400(db: Session, teacher_id: str | None) -> None:
    if teacher_id is None:
        return
    t = db.get(User, teacher_id)
    if not t or t.role != "docente":
        raise HTTPException(400, "El docente indicado no existe")


@router.post("/classrooms", status_code=201)
def create_classroom(body: ClassroomCreate, _: CurrentUser = Depends(admin_only), db: Session = Depends(get_db)):
    _teacher_or_400(db, body.teacher_id)
    room = Classroom(**body.model_dump())
    db.add(room)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(409, "Esa aula ya existe para el año indicado") from err
    return classroom_view(room)


@router.patch("/classrooms/{classroom_id}")
def assign_teacher(classroom_id: int, body: ClassroomUpdate, _: CurrentUser = Depends(admin_only), db: Session = Depends(get_db)):
    room = db.get(Classroom, classroom_id)
    if not room:
        raise HTTPException(404, "Aula no encontrada")
    _teacher_or_400(db, body.teacher_id)
    room.teacher_id = body.teacher_id
    db.commit()
    return classroom_view(room)


@router.get("/overview")
def overview(_: CurrentUser = Depends(admin_only), db: Session = Depends(get_db)):
    """Vista institucional por aula: estudiantes, acierto, pendientes de validación y alertas de concepto."""
    rows = []
    for room in db.scalars(select(Classroom).order_by(Classroom.grade, Classroom.section)).all():
        sids = list(db.scalars(select(Student.id).where(Student.classroom_id == room.id)).all())
        total = db.scalar(select(func.count(ResponseEvent.id)).where(ResponseEvent.student_id.in_(sids))) or 0 if sids else 0
        ok = db.scalar(select(func.count(ResponseEvent.id)).where(ResponseEvent.student_id.in_(sids), ResponseEvent.correct.is_(True))) or 0 if sids else 0
        acc = ok / total if total else None
        rows.append(
            {
                **classroom_view(room),
                "students": len(sids),
                "answers": total,
                "accuracy": round(acc, 2) if acc is not None else None,
                "light": traffic_light(acc),
                "pending_contents": (db.scalar(select(func.count(Content.id)).where(Content.student_id.in_(sids), Content.status == "pendiente")) or 0) if sids else 0,
                "pending_reinforcements": (db.scalar(select(func.count(Reinforcement.id)).where(Reinforcement.student_id.in_(sids), Reinforcement.status == "pendiente")) or 0) if sids else 0,
                "concept_alerts": (db.scalar(select(func.count(ResponseEvent.id)).where(ResponseEvent.student_id.in_(sids), ResponseEvent.category == "entendio_mal")) or 0) if sids else 0,
            }
        )
    return {
        "teachers": db.scalar(select(func.count(User.id)).where(User.role == "docente", User.active.is_(True))) or 0,
        "students": db.scalar(select(func.count(Student.id))) or 0,
        "classrooms": rows,
    }
