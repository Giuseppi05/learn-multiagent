"""Alta de cuentas en Supabase Auth y en la tabla users, siempre en pareja.

Si falla la parte local se borra la cuenta recién creada en Supabase, para no dejar usuarios huérfanos.
"""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Classroom, Student, User
from app.supabase_admin import AuthAdmin, student_pin, temporary_password


def _create(db: Session, admin: AuthAdmin, email: str, password: str, role: str, build) -> User:
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Ya existe una cuenta con ese correo o usuario")
    uid = admin.create_user(email, password, role)
    try:
        user = build(uid)
        db.add(user)
        db.flush()
        return user
    except IntegrityError as err:
        db.rollback()
        admin.delete_user(uid)
        raise HTTPException(409, "Ya existe una cuenta con ese correo o usuario") from err
    except Exception:
        db.rollback()
        admin.delete_user(uid)
        raise


def create_staff(db: Session, admin: AuthAdmin, full_name: str, email: str, role: str) -> tuple[User, str]:
    """Docente o coordinación. La contraseña temporal se muestra una sola vez y se cambia al primer ingreso."""
    password = temporary_password()
    user = _create(db, admin, email, password, role, lambda uid: User(id=uid, role=role, full_name=full_name, email=email, must_change_password=True))
    db.commit()
    return user, password


def student_email(username: str) -> str:
    return f"{username}@{get_settings().student_email_domain}"


def _next_code(db: Session, room: Classroom) -> str:
    # Código interno estable y sin datos personales: año, grado, sección y correlativo
    prefix = f"E{room.year % 100}{room.grade}{room.section}-"
    n = db.scalar(select(func.count(Student.id)).where(Student.classroom_id == room.id)) or 0
    while db.scalar(select(Student.id).where(Student.code == f"{prefix}{n + 1:02d}")):
        n += 1
    return f"{prefix}{n + 1:02d}"


def create_student(db: Session, admin: AuthAdmin, room: Classroom, full_name: str, username: str, interests: str) -> tuple[Student, str]:
    if db.scalar(select(User.id).where(User.username == username)):
        raise HTTPException(409, "Ese usuario ya está en uso")
    pin = student_pin()
    user = _create(db, admin, student_email(username), pin, "estudiante", lambda uid: User(id=uid, role="estudiante", full_name=full_name, email=student_email(username), username=username))
    st = Student(user_id=user.id, classroom_id=room.id, code=_next_code(db, room), interests=interests)
    db.add(st)
    db.commit()
    return st, pin
