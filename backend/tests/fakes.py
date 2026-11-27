"""Dobles de prueba: modelo de lenguaje y API de administración de Supabase.

Las pruebas no llaman a Gemini ni a Supabase: consumirían cuota y dependerían de la red.
"""

import json
import uuid

from pydantic import BaseModel

from app.schemas import AdaptedContentOut, AssistantOut, ContentOut, FeedbackOut, LearningProfileOut, ReinforcementOut, ReportOut


def _exercises(n: int) -> list[dict]:
    return [
        {"question": f"Pregunta {i + 1}: ¿cuánto es {i + 2} × 3?", "options": [str((i + 2) * 3 + d) for d in (0, 1, 2, 3)], "correct_index": 0, "explanation": f"Tema {i + 1}", "expected_seconds": 30}
        for i in range(n)
    ]


class FakeLLM:
    model = "fake-model"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []  # (esquema, prompt)
        self.fail_schemas: set[str] = set()  # esquemas que devuelven JSON inválido
        self.adapter_changes_answer = False

    def generate(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        name = schema.__name__
        self.calls.append((name, prompt))
        if name in self.fail_schemas:
            return "{no es json"
        if schema is LearningProfileOut:
            out = {"level": "en_proceso", "reading_level": "intermedio", "pace": "medio", "strengths": ["cálculo"], "gaps": ["fracciones"], "interests": ["fútbol"], "recommendation": "Practicar."}
        elif schema is AdaptedContentOut:
            base = json.loads(prompt.split("Material base (JSON): ", 1)[1])
            if self.adapter_changes_answer:
                base["exercises"][0]["correct_index"] = 1
            out = {**base, "adaptation_notes": "Vocabulario sencillo."}
        elif schema is ContentOut:
            n = 6 if "prueba inicial" in system.lower() else 4
            out = {"title": "Material", "explanation": "Explicación.", "examples": ["Ejemplo"], "exercises": _exercises(n), "reinforcement_activity": "Tapitas."}
        elif schema is FeedbackOut:
            answers = json.loads(prompt.split("categoría): ", 1)[1])
            out = {
                "overall": "¡Buen esfuerzo!",
                "items": [{"index": a["index"], "correct": a["correct"], "error_type": "ninguno" if a["correct"] else "conceptual", "message": "Sigue así."} for a in answers],
            }
        elif schema is ReinforcementOut:
            out = {"suspected_misconception": "Confunde suma con multiplicación.", "activity_title": "Grupos con tapitas", "steps": ["Forma grupos", "Cuenta"], "materials": ["tapitas"]}
        elif schema is AssistantOut:
            out = {"answer": "Piensa en grupos iguales.", "follow_up": "¿Cuántos grupos ves?"}
        elif schema is ReportOut:
            out = {"summary": "Avanza bien.", "progress": ["multiplicación"], "difficulties": [], "recommendations": ["Seguir practicando"]}
        else:
            raise AssertionError(f"Esquema no previsto: {name}")
        return json.dumps(out, ensure_ascii=False)

    def prompts_for(self, schema_name: str) -> list[str]:
        return [p for n, p in self.calls if n == schema_name]


class FakeAuthAdmin:
    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    def create_user(self, email: str, password: str, role: str) -> str:
        uid = str(uuid.uuid4())
        self.users[uid] = {"email": email, "password": password, "role": role, "banned": False}
        return uid

    def set_password(self, user_id: str, password: str) -> None:
        self.users[user_id]["password"] = password

    def set_banned(self, user_id: str, banned: bool) -> None:
        self.users[user_id]["banned"] = banned

    def delete_user(self, user_id: str) -> None:
        self.users.pop(user_id, None)
