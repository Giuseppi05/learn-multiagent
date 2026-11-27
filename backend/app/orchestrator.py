"""Orquestador (LangGraph). Coordina a los agentes y es el único componente que escribe en la base.

Las tareas que llaman al modelo corren en segundo plano (jobs) con su propia sesión de base de datos;
la API responde de inmediato y el frontend consulta el estado.
"""

import logging
import time
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import agents
from app.config import get_settings
from app.db import SessionLocal
from app.llm import AgentError, LLMResult
from app.models import AgentRun, Content, ContentReview, LearningProfile, Reinforcement, Report, ResponseEvent, Student, Submission, now
from app.rules import CATEGORIES, classify, decide_next, traffic_light
from app.schemas import ContentOut

log = logging.getLogger("aprende.orchestrator")

# ---------- utilidades ----------


def call_agent(db: Session, agent: str, student_id: int | None, content_id: int | None, inp: dict, fn: Callable[[], LLMResult]) -> LLMResult:
    """Ejecuta un agente y deja la traza, haya funcionado o no (trazabilidad, Sección 10)."""
    started = time.perf_counter()
    try:
        res = fn()
    except AgentError as err:
        db.add(
            AgentRun(
                agent=agent,
                student_id=student_id,
                content_id=content_id,
                status="error",
                model=get_settings().gemini_model,
                attempts=err.attempts,
                latency_ms=int((time.perf_counter() - started) * 1000),
                input=inp,
                error=str(err),
            )
        )
        db.flush()
        raise
    db.add(
        AgentRun(
            agent=agent,
            student_id=student_id,
            content_id=content_id,
            status="ok",
            model=res.model,
            attempts=res.attempts,
            latency_ms=res.latency_ms,
            input=inp,
            output=res.output.model_dump(),
        )
    )
    return res


def latest_profile(db: Session, student_id: int) -> dict | None:
    row = db.scalars(select(LearningProfile).where(LearningProfile.student_id == student_id).order_by(LearningProfile.id.desc())).first()
    return row.data if row else None


def topic_history(db: Session, student_id: int, topic: str) -> list[str]:
    n = get_settings().decision_window
    rows = db.scalars(select(ResponseEvent).where(ResponseEvent.student_id == student_id, ResponseEvent.topic == topic).order_by(ResponseEvent.id.desc()).limit(n)).all()
    return [r.category for r in reversed(rows)]


def topic_summary(db: Session, student_id: int) -> list[dict]:
    events = db.scalars(select(ResponseEvent).where(ResponseEvent.student_id == student_id).order_by(ResponseEvent.id)).all()
    topics: dict[str, list[ResponseEvent]] = {}
    for e in events:
        topics.setdefault(e.topic, []).append(e)
    out = []
    for topic, evs in topics.items():
        acc = sum(e.correct for e in evs) / len(evs)
        out.append(
            {
                "topic": topic,
                "answers": len(evs),
                "accuracy": round(acc, 2),
                "light": traffic_light(acc),
                "avg_time_s": round(sum(e.time_ms for e in evs) / len(evs) / 1000, 1),
                "categories": {CATEGORIES[k]["label"]: sum(e.category == k for e in evs) for k in CATEGORIES},
            }
        )
    return out


def correct_option(content: Content, index: int) -> str:
    ex = content.adapted["exercises"][index]
    return ex["options"][ex["correct_index"]]


def _run_job(name: str, fn: Callable[[Session], None]) -> None:
    db = SessionLocal()
    try:
        fn(db)
    except Exception:
        log.exception("Falló el job %s", name)
        db.rollback()
    finally:
        db.close()


# ---------- Grafo 1: generación de contenido (CU-IA-02 y 03, o prueba inicial) ----------


class ContentState(TypedDict, total=False):
    db: Session
    content: Content
    student: Student
    profile: dict
    teacher_notes: str
    base: ContentOut


def _generate(s: ContentState) -> dict:
    c, st = s["content"], s["student"]
    grade = st.classroom.grade
    if c.kind == "prueba_inicial":
        inp = {"kind": "prueba_inicial", "area": c.area, "notes": s["teacher_notes"]}
        res = call_agent(s["db"], "generador", st.id, c.id, inp, lambda: agents.initial_test(c.area, grade, st.interests, s["teacher_notes"]))
    else:
        inp = {"topic": c.topic, "difficulty": c.difficulty, "profile": s["profile"], "notes": s["teacher_notes"]}
        res = call_agent(s["db"], "generador", st.id, c.id, inp, lambda: agents.generate(c.area, c.topic, grade, c.difficulty, s["profile"], s["teacher_notes"]))
    return {"base": res.output}


def _needs_adaptation(s: ContentState) -> str:
    # La prueba inicial mide al estudiante tal como está: no se adapta a un perfil que todavía no existe
    return "publish" if s["content"].kind == "prueba_inicial" else "adapt"


def _adapt(s: ContentState) -> dict:
    c, st = s["content"], s["student"]
    res = call_agent(s["db"], "adaptacion", st.id, c.id, {"profile": s["profile"]}, lambda: agents.adapt(s["base"], s["profile"], s["teacher_notes"]))
    c.adapted = res.output.model_dump()
    return {}


def _publish_for_review(s: ContentState) -> dict:
    c = s["content"]
    c.base = s["base"].model_dump()
    if c.kind == "prueba_inicial":
        c.adapted = {**c.base, "adaptation_notes": ""}
    c.status = "pendiente"
    c.error = ""
    return {}


def _build_content_graph():
    g = StateGraph(ContentState)
    g.add_node("generate", _generate)
    g.add_node("adapt", _adapt)
    g.add_node("publish", _publish_for_review)
    g.add_edge(START, "generate")
    g.add_conditional_edges("generate", _needs_adaptation, {"adapt": "adapt", "publish": "publish"})
    g.add_edge("adapt", "publish")
    g.add_edge("publish", END)
    return g.compile()


content_graph = _build_content_graph()


def create_content(db: Session, student: Student, kind: str, area: str, topic: str, difficulty: int, origin: str, requested_by: str | None) -> Content:
    c = Content(student_id=student.id, kind=kind, area=area, topic=topic, difficulty=difficulty, origin=origin, requested_by=requested_by, status="generando")
    db.add(c)
    db.flush()
    return c


def generate_content(db: Session, content_id: int, teacher_notes: str = "") -> None:
    """Corre el grafo de generación sobre un contenido en estado 'generando'."""
    c = db.get(Content, content_id)
    if not c or c.status != "generando":
        return
    st = c.student
    try:
        content_graph.invoke({"db": db, "content": c, "student": st, "profile": latest_profile(db, st.id) or {}, "teacher_notes": teacher_notes})
    except AgentError as err:
        # Sección 20.5: se detiene la generación y el docente decide si reintenta
        c.status = "error_ia"
        c.error = str(err)
    db.commit()


def content_job(content_id: int, teacher_notes: str = "") -> None:
    _run_job(f"contenido {content_id}", lambda db: generate_content(db, content_id, teacher_notes))


def review_content(db: Session, c: Content, reviewer_id: str, decision: str, note: str) -> bool:
    """Registra la decisión del docente. Devuelve True si hay que regenerar en segundo plano."""
    db.add(ContentReview(content_id=c.id, reviewer_id=reviewer_id, decision=decision, note=note, snapshot=c.adapted))
    regenerate = False
    if decision == "aprobado":
        c.status = "aprobado"
        c.published_at = now()
    elif decision == "rechazado":
        c.status = "rechazado"
    else:
        c.returns_count += 1
        if c.returns_count >= get_settings().max_teacher_returns:
            # Tras 3 devoluciones se corta el ciclo para no entrar en un bucle sin fin
            c.status = "requiere_docente"
        else:
            c.status = "generando"
            regenerate = True
    db.commit()
    return regenerate


# ---------- Grafo 2: respuestas del estudiante (CU-IA-04, refuerzo, CU-IA-01 y CU-IA-07) ----------


class AnswerState(TypedDict, total=False):
    db: Session
    submission: Submission
    content: Content
    student: Student
    events: list[ResponseEvent]
    decision: dict


def _evaluate(s: AnswerState) -> dict:
    sub, c, st = s["submission"], s["content"], s["student"]
    items = [
        {
            "index": e.question_index,
            "question": e.question,
            "selected": e.answer,
            "correct_option": correct_option(c, e.question_index),
            "correct": e.correct,
            "confidence": e.confidence,
            "category": CATEGORIES[e.category]["label"],
        }
        for e in s["events"]
    ]
    try:
        res = call_agent(s["db"], "evaluador", st.id, c.id, {"answers": items}, lambda: agents.evaluate(c.topic, items))
        sub.feedback = res.output.model_dump()
    except AgentError as err:
        # Sin retroalimentación el estudiante igual ve su resultado; el resto del ciclo continúa
        sub.feedback = {"error": str(err)}
    return {}


def _route_after_evaluate(s: AnswerState) -> str:
    if s["content"].kind == "prueba_inicial":
        return "diagnose"
    return "reinforce" if any(e.category == "entendio_mal" for e in s["events"]) else "decide"


def _diagnose_from_test(s: AnswerState) -> dict:
    """CU-IA-01 con la prueba inicial rendida en la plataforma (Sección 20, pasos 4 y 5)."""
    c, st = s["content"], s["student"]
    results = [
        {
            "pregunta": e.question,
            "tema_evaluado": c.adapted["exercises"][e.question_index]["explanation"],
            "correcta": e.correct,
            "tiempo_s": round(e.time_ms / 1000, 1),
            "confianza": e.confidence,
        }
        for e in s["events"]
    ]
    try:
        res = call_agent(s["db"], "diagnostico", st.id, c.id, {"initial_test": results}, lambda: agents.diagnose(st.code, st.classroom.grade, st.interests, results, "", []))
        s["db"].add(LearningProfile(student_id=st.id, source="prueba_inicial", data=res.output.model_dump()))
        decision = {"action": "diagnosticado", "difficulty": 0, "reason": "Perfil de aprendizaje creado a partir de la prueba inicial.", "window": []}
    except AgentError as err:
        decision = {"action": "error_ia", "difficulty": 0, "reason": f"No se pudo crear el perfil: {err}", "window": []}
    return {"decision": decision}


def _reinforce(s: AnswerState) -> dict:
    # Solo los errores con alta confianza consumen IA (Sección 21.4); se agrupan en una sola actividad por envío
    sub, c, st = s["submission"], s["content"], s["student"]
    wrong = [e for e in s["events"] if e.category == "entendio_mal"]
    mistakes = [{"enunciado": e.question, "respuesta": e.answer, "correcta": correct_option(c, e.question_index), "confianza": e.confidence} for e in wrong]
    rf = Reinforcement(student_id=st.id, submission_id=sub.id, topic=c.topic, event_ids=[e.id for e in wrong], status="generando")
    s["db"].add(rf)
    try:
        history = topic_history(s["db"], st.id, c.topic)
        res = call_agent(s["db"], "refuerzo_conceptual", st.id, c.id, {"mistakes": mistakes}, lambda: agents.reinforce(c.topic, mistakes, history))
        rf.data = {**res.output.model_dump(), "mistakes": mistakes}
        rf.status = "pendiente"
    except AgentError as err:
        rf.status = "error_ia"
        rf.error = str(err)
    return {}


def _decide(s: AnswerState) -> dict:
    history = topic_history(s["db"], s["student"].id, s["content"].topic)
    d = decide_next(history, s["content"].difficulty)
    return {"decision": {"action": d.action, "difficulty": d.difficulty, "reason": d.reason, "window": history}}


def _route_after_decide(s: AnswerState) -> str:
    action = s["decision"]["action"]
    if action == "consolidado":
        return "report"
    return "end" if action == "esperar" else "prepare_next"


def _prepare_next(s: AnswerState) -> dict:
    db, c, st, d = s["db"], s["content"], s["student"], s["decision"]
    # Solo vale la propuesta con la decisión más reciente; las anteriores sin revisar salen de la cola del docente
    stale = select(Content).where(Content.student_id == st.id, Content.topic == c.topic, Content.status == "pendiente", Content.origin.startswith("orquestador"))
    for old in db.scalars(stale).all():
        old.status = "reemplazado"
    nxt = create_content(db, st, "material", c.area, c.topic, d["difficulty"], f"orquestador:{d['action']}", None)
    s["submission"].next_content_id = nxt.id
    db.commit()
    generate_content(db, nxt.id)
    return {}


def _auto_report(s: AnswerState) -> dict:
    # Sección 20.4: tema consolidado → se genera el reporte para que el docente decida el siguiente tema
    rep = Report(student_id=s["student"].id, requested_by=None, status="generando")
    s["db"].add(rep)
    s["db"].flush()
    build_report(s["db"], rep)
    return {}


def _build_answer_graph():
    g = StateGraph(AnswerState)
    g.add_node("evaluate", _evaluate)
    g.add_node("diagnose", _diagnose_from_test)
    g.add_node("reinforce", _reinforce)
    g.add_node("decide", _decide)
    g.add_node("prepare_next", _prepare_next)
    g.add_node("report", _auto_report)
    g.add_edge(START, "evaluate")
    g.add_conditional_edges("evaluate", _route_after_evaluate, {"diagnose": "diagnose", "reinforce": "reinforce", "decide": "decide"})
    g.add_edge("diagnose", END)
    g.add_edge("reinforce", "decide")
    g.add_conditional_edges("decide", _route_after_decide, {"prepare_next": "prepare_next", "report": "report", "end": END})
    g.add_edge("prepare_next", END)
    g.add_edge("report", END)
    return g.compile()


answer_graph = _build_answer_graph()


def build_event(student: Student, content: Content, index: int, selected: int, time_ms: int, confidence: int, changes: int, environment: str) -> ResponseEvent:
    """Calcula el acierto en el servidor (Sección 20, paso 14) y aplica las reglas de la Sección 16."""
    ex = content.adapted["exercises"][index]
    correct = selected == ex["correct_index"]
    expected_ms = ex["expected_seconds"] * 1000
    return ResponseEvent(
        student_id=student.id,
        content_id=content.id,
        topic=content.topic,
        question_index=index,
        question=ex["question"],
        answer=ex["options"][selected],
        correct=correct,
        time_ms=time_ms,
        expected_ms=expected_ms,
        confidence=confidence,
        changes=changes,
        environment=environment,
        activity=f"{content.kind}-{content.id}",
        category=classify(correct, confidence, time_ms, expected_ms, changes),
    )


def record_answers(db: Session, student: Student, content: Content, answers: list[dict], environment: str) -> tuple[Submission, list[ResponseEvent]]:
    """Paso síncrono, sin IA: el estudiante ve de inmediato si acertó y la categoría de cada respuesta."""
    sub = Submission(student_id=student.id, content_id=content.id, environment=environment, status="procesando")
    db.add(sub)
    db.flush()
    events = []
    for a in answers:
        ev = build_event(student, content, a["index"], a["selected"], a["time_ms"], a["confidence"], a["changes"], environment)
        ev.submission_id = sub.id
        db.add(ev)
        events.append(ev)
    db.commit()
    return sub, events


def process_submission(db: Session, submission_id: int) -> None:
    sub = db.get(Submission, submission_id)
    if not sub or sub.status != "procesando":
        return
    c = db.get(Content, sub.content_id)
    events = db.scalars(select(ResponseEvent).where(ResponseEvent.submission_id == sub.id).order_by(ResponseEvent.question_index)).all()
    result = answer_graph.invoke({"db": db, "submission": sub, "content": c, "student": c.student, "events": list(events)})
    sub.decision = result.get("decision")
    sub.status = "error_ia" if (sub.feedback or {}).get("error") else "listo"
    db.commit()


def submission_job(submission_id: int) -> None:
    _run_job(f"envío {submission_id}", lambda db: process_submission(db, submission_id))


def device_reinforcement_job(event_id: int) -> None:
    """Un error de concepto llegado desde el mando también activa al Agente de Refuerzo Conceptual."""

    def run(db: Session) -> None:
        e = db.get(ResponseEvent, event_id)
        c = db.get(Content, e.content_id)
        mistakes = [{"enunciado": e.question, "respuesta": e.answer, "correcta": correct_option(c, e.question_index), "confianza": e.confidence}]
        rf = Reinforcement(student_id=e.student_id, topic=e.topic, event_ids=[e.id], status="generando")
        db.add(rf)
        try:
            history = topic_history(db, e.student_id, e.topic)
            res = call_agent(db, "refuerzo_conceptual", e.student_id, c.id, {"mistakes": mistakes}, lambda: agents.reinforce(e.topic, mistakes, history))
            rf.data = {**res.output.model_dump(), "mistakes": mistakes}
            rf.status = "pendiente"
        except AgentError as err:
            rf.status = "error_ia"
            rf.error = str(err)
        db.commit()

    _run_job(f"refuerzo evento {event_id}", run)


# ---------- Diagnóstico por el docente, reportes y asistente ----------


def diagnose_by_teacher(db: Session, st: Student, teacher_notes: str, external_test: str) -> dict:
    history = [e.category for e in db.scalars(select(ResponseEvent).where(ResponseEvent.student_id == st.id).order_by(ResponseEvent.id.desc()).limit(10))]
    inp = {"teacher_notes": teacher_notes, "external_test": external_test, "history": history}
    try:
        res = call_agent(db, "diagnostico", st.id, None, inp, lambda: agents.diagnose(st.code, st.classroom.grade, st.interests, external_test, teacher_notes, history))
    finally:
        db.commit()
    db.add(LearningProfile(student_id=st.id, source="docente", data=res.output.model_dump()))
    db.commit()
    return res.output.model_dump()


def build_report(db: Session, rep: Report) -> None:
    st = db.get(Student, rep.student_id)
    topics = topic_summary(db, st.id)
    profile = latest_profile(db, st.id) or {}
    try:
        res = call_agent(db, "reporte", st.id, None, {"topics": topics}, lambda: agents.report(st.code, st.classroom.grade, profile, topics))
        rep.data = {**res.output.model_dump(), "topics": topics}
        rep.status = "listo"
    except AgentError as err:
        rep.status = "error_ia"
        rep.error = str(err)
    db.commit()


def report_job(report_id: int) -> None:
    def run(db: Session) -> None:
        rep = db.get(Report, report_id)
        if rep and rep.status == "generando":
            build_report(db, rep)

    _run_job(f"reporte {report_id}", run)


def assistant_history(db: Session, student_id: int, content_id: int) -> list[dict[str, Any]]:
    q = select(AgentRun).where(AgentRun.agent == "asistente", AgentRun.student_id == student_id, AgentRun.content_id == content_id, AgentRun.status == "ok").order_by(AgentRun.id)
    return [{"pregunta": r.input.get("question"), "respuesta": (r.output or {}).get("answer"), "seguimiento": (r.output or {}).get("follow_up")} for r in db.scalars(q).all()]


def ask_assistant(db: Session, st: Student, c: Content, question: str) -> dict:
    history = [{"pregunta": h["pregunta"], "respuesta": h["respuesta"]} for h in assistant_history(db, st.id, c.id)]
    profile = latest_profile(db, st.id) or {}
    try:
        res = call_agent(db, "asistente", st.id, c.id, {"question": question}, lambda: agents.assist(question, c.adapted, profile, history))
    finally:
        db.commit()
    return res.output.model_dump()
