"""Reglas de acceso a los datos: un docente solo ve a los estudiantes de sus aulas; la coordinación ve todo."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Classroom, Content, Student


def visible_classroom_ids(db: Session, me: CurrentUser) -> list[int]:
    q = select(Classroom.id)
    if me.role == "docente":
        q = q.where(Classroom.teacher_id == me.id)
    return list(db.scalars(q).all())


def classroom_for(db: Session, me: CurrentUser, classroom_id: int) -> Classroom:
    room = db.get(Classroom, classroom_id)
    # 404 y no 403: no se revela la existencia de aulas ajenas
    if not room or (me.role == "docente" and room.teacher_id != me.id):
        raise HTTPException(404, "Aula no encontrada")
    return room


def student_for(db: Session, me: CurrentUser, student_id: int) -> Student:
    st = db.get(Student, student_id)
    if not st or (me.role == "docente" and st.classroom.teacher_id != me.id):
        raise HTTPException(404, "Estudiante no encontrado")
    return st


def content_for(db: Session, me: CurrentUser, content_id: int) -> Content:
    c = db.get(Content, content_id)
    if not c:
        raise HTTPException(404, "Contenido no encontrado")
    student_for(db, me, c.student_id)
    return c


def own_material(db: Session, me: CurrentUser, content_id: int) -> Content:
    """Material visible para el estudiante: suyo y aprobado por el docente."""
    c = db.get(Content, content_id)
    if not me.student or not c or c.student_id != me.student.id:
        raise HTTPException(404, "Material no encontrado")
    if c.status != "aprobado":
        raise HTTPException(403, "Este material todavía no fue aprobado por tu docente")
    return c
