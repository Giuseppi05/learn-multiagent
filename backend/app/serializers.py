"""Vistas de los modelos para la API. Separan lo que ve el docente de lo que ve el estudiante."""

from app.models import Classroom, Content, Reinforcement, Student, User
from app.rules import CATEGORIES


def user_view(u: User) -> dict:
    return {"id": u.id, "role": u.role, "full_name": u.full_name, "email": u.email, "username": u.username, "active": u.active, "must_change_password": u.must_change_password}


def classroom_view(c: Classroom) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "year": c.year,
        "grade": c.grade,
        "section": c.section,
        "teacher": {"id": c.teacher.id, "full_name": c.teacher.full_name} if c.teacher else None,
    }


def student_view(s: Student) -> dict:
    return {
        "id": s.id,
        "code": s.code,
        "full_name": s.user.full_name,
        "username": s.user.username,
        "active": s.user.active,
        "interests": s.interests,
        "classroom": {"id": s.classroom.id, "name": s.classroom.name, "grade": s.classroom.grade},
    }


def content_summary(c: Content) -> dict:
    return {
        "id": c.id,
        "student_id": c.student_id,
        "student_name": c.student.user.full_name,
        "classroom": c.student.classroom.name,
        "kind": c.kind,
        "area": c.area,
        "topic": c.topic,
        "difficulty": c.difficulty,
        "status": c.status,
        "origin": c.origin,
        "title": (c.adapted or {}).get("title"),
        "returns_count": c.returns_count,
        "error": c.error,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def content_teacher_view(c: Content) -> dict:
    return {
        **content_summary(c),
        "base": c.base,
        "adapted": c.adapted,
        "reviews": [{"decision": r.decision, "note": r.note, "created_at": r.created_at} for r in c.reviews],
    }


def material_student_view(c: Content) -> dict:
    # El estudiante nunca recibe las respuestas correctas ni las explicaciones antes de responder
    a = c.adapted or {}
    return {
        "id": c.id,
        "kind": c.kind,
        "area": c.area,
        "topic": c.topic,
        "difficulty": c.difficulty,
        "title": a.get("title"),
        "explanation": a.get("explanation"),
        "examples": a.get("examples", []),
        "exercises": [{"index": i, "question": e["question"], "options": e["options"]} for i, e in enumerate(a.get("exercises", []))],
    }


def reinforcement_view(r: Reinforcement, student: Student) -> dict:
    return {
        "id": r.id,
        "student_id": r.student_id,
        "student_name": student.user.full_name,
        "classroom": student.classroom.name,
        "topic": r.topic,
        "status": r.status,
        "data": r.data,
        "error": r.error,
        "created_at": r.created_at,
    }


def category_label(key: str) -> str:
    return CATEGORIES[key]["label"]
