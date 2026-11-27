"""Agentes especializados. No acceden a la base de datos: reciben datos y devuelven salida validada.

Solo el Orquestador lee y escribe en la base (Sección 6). Cada función devuelve un LLMResult con la salida,
el modelo, los intentos y la latencia, para la trazabilidad.
"""

import json

from app.agents import prompts as P
from app.llm import LLMResult, run_structured
from app.schemas import AdaptedContentOut, AssistantOut, ContentOut, FeedbackOut, LearningProfileOut, ReinforcementOut, ReportOut


def _j(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _none(text: str) -> str:
    return text.strip() or "ninguna"


def diagnose(code: str, grade: int, interests: str, initial_test: list[dict] | str, teacher_notes: str, history: list[str]) -> LLMResult:
    prompt = P.DIAGNOSIS_PROMPT.format(
        code=code,
        grade=grade,
        interests=interests or "no indicados",
        initial_test=_j(initial_test) if isinstance(initial_test, list) else _none(initial_test),
        teacher_notes=_none(teacher_notes),
        history=history or "sin historial",
    )
    return run_structured(P.DIAGNOSIS_SYSTEM, prompt, LearningProfileOut)


def initial_test(area: str, grade: int, interests: str, teacher_notes: str) -> LLMResult:
    prompt = P.INITIAL_TEST_PROMPT.format(area=area, grade=grade, interests=interests or "no indicados", teacher_notes=_none(teacher_notes))
    return run_structured(P.INITIAL_TEST_SYSTEM, prompt, ContentOut)


def generate(area: str, topic: str, grade: int, difficulty: int, profile: dict, teacher_notes: str) -> LLMResult:
    prompt = P.GENERATOR_PROMPT.format(area=area, topic=topic, grade=f"{grade}.º de primaria", difficulty=difficulty, profile=_j(profile), teacher_notes=_none(teacher_notes))
    return run_structured(P.GENERATOR_SYSTEM, prompt, ContentOut)


def adapt(base: ContentOut, profile: dict, teacher_notes: str = "") -> LLMResult:
    def same_answers(out: AdaptedContentOut) -> str | None:
        # Salvaguarda: el Adaptador reformula, pero no puede cambiar qué alternativa es la correcta
        if len(out.exercises) != len(base.exercises):
            return "El adaptador cambió la cantidad de ejercicios"
        for i, (a, b) in enumerate(zip(out.exercises, base.exercises, strict=True)):
            if a.correct_index != b.correct_index:
                return f"El adaptador cambió la respuesta correcta del ejercicio {i + 1}"
        return None

    prompt = P.ADAPTER_PROMPT.format(profile=_j(profile), teacher_notes=_none(teacher_notes), base=base.model_dump_json())
    return run_structured(P.ADAPTER_SYSTEM, prompt, AdaptedContentOut, check=same_answers)


def evaluate(topic: str, answers: list[dict]) -> LLMResult:
    expected = {a["index"] for a in answers}

    def covers_all(out: FeedbackOut) -> str | None:
        return None if {i.index for i in out.items} == expected else "La retroalimentación no cubre exactamente las preguntas respondidas"

    prompt = P.EVALUATOR_PROMPT.format(topic=topic, answers=_j(answers))
    return run_structured(P.EVALUATOR_SYSTEM, prompt, FeedbackOut, check=covers_all)


def reinforce(topic: str, mistakes: list[dict], history: list[str]) -> LLMResult:
    prompt = P.REINFORCEMENT_PROMPT.format(topic=topic, mistakes=_j(mistakes), history=history)
    return run_structured(P.REINFORCEMENT_SYSTEM, prompt, ReinforcementOut)


def assist(question: str, material: dict, profile: dict, history: list[dict]) -> LLMResult:
    visible = {k: material.get(k) for k in ("title", "explanation", "examples")}
    # El asistente ve los enunciados, pero no las respuestas correctas, para que no las revele
    visible["exercises"] = [{"question": e["question"], "options": e["options"]} for e in material.get("exercises", [])]
    prompt = P.ASSISTANT_PROMPT.format(material=_j(visible), profile=_j(profile), history=_j(history[-6:]), question=question)
    return run_structured(P.ASSISTANT_SYSTEM, prompt, AssistantOut)


def report(code: str, grade: int, profile: dict, topics: list[dict]) -> LLMResult:
    prompt = P.REPORT_PROMPT.format(code=code, grade=grade, profile=_j(profile), topics=_j(topics))
    return run_structured(P.REPORT_SYSTEM, prompt, ReportOut)
