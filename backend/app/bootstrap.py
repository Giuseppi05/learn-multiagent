"""Crea las cuentas de prueba: coordinación, una docente, un aula y tres estudiantes.

Uso: python -m app.bootstrap
Las credenciales se guardan en credenciales_demo.txt (ignorado por git); no se imprimen en pantalla.
"""

from datetime import date

from sqlalchemy import select

from app.accounts import create_staff, create_student
from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.models import Classroom, User
from app.supabase_admin import AuthAdmin

STUDENTS = [("Lucía Ramos Huamán", "lucia.r", "fútbol, animales"), ("Mateo Quispe Flores", "mateo.q", "videojuegos, dinosaurios"), ("Valeria Torres Mamani", "valeria.t", "dibujo, música")]


def main() -> None:
    admin = AuthAdmin()
    lines = []
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == "admin")):
            print("Ya existen cuentas: no se creó nada.")
            return
        coord, pw = create_staff(db, admin, "Coordinación Académica", "coordinacion@aprende-demo.pe", "admin")
        lines.append(f"Coordinación  correo: {coord.email}  contraseña temporal: {pw}")
        teacher, pw = create_staff(db, admin, "Rosa Quispe Mendoza", "rosa.quispe@aprende-demo.pe", "docente")
        lines.append(f"Docente       correo: {teacher.email}  contraseña temporal: {pw}")
        room = Classroom(year=date.today().year, grade=3, section="B", teacher_id=teacher.id)
        db.add(room)
        db.commit()
        for name, username, interests in STUDENTS:
            _, pin = create_student(db, admin, room, name, username, interests)
            lines.append(f"Estudiante    usuario: {username}  PIN: {pin}  ({name})")
    out = BACKEND_DIR / "credenciales_demo.txt"
    out.write_text("Cuentas de prueba (el personal cambia su contraseña en el primer ingreso)\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"Listo: {len(lines)} cuentas creadas. Credenciales en {out.name}")


if __name__ == "__main__":
    main()
