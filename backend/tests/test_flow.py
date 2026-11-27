"""Flujo completo por rol: coordinación, docente y estudiante, con el Orquestador y los agentes (modelo simulado)."""

import uuid

from app.db import SessionLocal
from app.models import AgentRun, LearningProfile, User
from tests.conftest import headers_for, token_for

# ---------- ayudantes ----------


def _setup_classroom(client, admin_headers, email="docente@ie.edu.pe", section="B"):
    t = client.post("/admin/teachers", json={"full_name": "Rosa Quispe", "email": email}, headers=admin_headers).json()
    room = client.post("/admin/classrooms", json={"year": 2026, "grade": 3, "section": section, "teacher_id": t["teacher"]["id"]}, headers=admin_headers).json()
    return headers_for(t["teacher"]["id"]), room["id"]


def _add_student(client, th, room_id, username="lucia.r"):
    r = client.post(f"/classrooms/{room_id}/students", json={"full_name": "Lucía Ramos", "username": username, "interests": "fútbol"}, headers=th)
    assert r.status_code == 201, r.text
    body = r.json()
    with SessionLocal() as db:
        uid = db.query(User).filter(User.username == username).one().id
    return body["student"]["id"], headers_for(uid), body


def _with_profile(sid):
    with SessionLocal() as db:
        db.add(LearningProfile(student_id=sid, source="docente", data={"level": "en_proceso", "reading_level": "intermedio", "interests": ["fútbol"]}))
        db.commit()


def _approved_material(client, th, sid, topic="multiplicación", difficulty=2):
    c = client.post(f"/students/{sid}/contents", json={"topic": topic, "difficulty": difficulty}, headers=th)
    assert c.status_code == 202, c.text
    cid = c.json()["id"]
    assert client.get(f"/contents/{cid}", headers=th).json()["status"] == "pendiente"
    assert client.post(f"/contents/{cid}/review", json={"decision": "aprobado"}, headers=th).json()["status"] == "aprobado"
    return cid


# ---------- autenticación y roles ----------


def test_requests_without_valid_session_are_rejected(client, admin_headers):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer basura"}).status_code == 401
    uid = str(uuid.uuid4())
    assert client.get("/me", headers={"Authorization": f"Bearer {token_for(uid, expired=True)}"}).status_code == 401
    # Token válido de Supabase, pero sin perfil en el sistema
    assert client.get("/me", headers=headers_for(uid)).status_code == 403


def test_roles_are_enforced(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    assert client.get("/admin/teachers", headers=th).status_code == 403
    assert client.get("/admin/teachers", headers=sh).status_code == 403
    assert client.get(f"/students/{sid}", headers=sh).status_code == 403
    assert client.get("/my/home", headers=th).status_code == 403
    assert client.get("/me", headers=sh).json()["student"]["code"] == "E263B-01"


def test_admin_creates_teacher_with_temporary_password(client, admin_headers, auth_admin):
    r = client.post("/admin/teachers", json={"full_name": "Rosa Quispe", "email": "Rosa@IE.edu.pe"}, headers=admin_headers).json()
    assert r["teacher"]["email"] == "rosa@ie.edu.pe" and r["teacher"]["must_change_password"]
    assert auth_admin.users[r["teacher"]["id"]]["password"] == r["temporary_password"]
    th = headers_for(r["teacher"]["id"])
    assert client.post("/me/password", json={"password": "nueva-clave-segura"}, headers=th).status_code == 204
    assert client.get("/me", headers=th).json()["user"]["must_change_password"] is False
    assert client.post("/admin/teachers", json={"full_name": "Otra", "email": "rosa@ie.edu.pe"}, headers=admin_headers).status_code == 409


def test_teacher_only_sees_own_classroom(client, admin_headers):
    th1, room1 = _setup_classroom(client, admin_headers)
    th2, _ = _setup_classroom(client, admin_headers, email="otro@ie.edu.pe", section="C")
    sid, _, _ = _add_student(client, th1, room1)
    assert client.get(f"/classrooms/{room1}/dashboard", headers=th2).status_code == 404
    assert client.get(f"/students/{sid}", headers=th2).status_code == 404
    assert client.post(f"/classrooms/{room1}/students", json={"full_name": "X Y", "username": "xy.z"}, headers=th2).status_code == 404
    assert [c["id"] for c in client.get("/classrooms", headers=th1).json()] == [room1]


def test_student_account_gets_pin_and_internal_email(client, admin_headers, auth_admin):
    th, room = _setup_classroom(client, admin_headers)
    _, _, body = _add_student(client, th, room)
    assert len(body["pin"]) == 6 and body["pin"].isdigit()
    emails = [u["email"] for u in auth_admin.users.values() if u["role"] == "estudiante"]
    assert emails == ["lucia.r@estudiantes.aprende.invalid"]
    assert client.post(f"/classrooms/{room}/students", json={"full_name": "Otra", "username": "lucia.r"}, headers=th).status_code == 409
    assert client.post(f"/classrooms/{room}/students", json={"full_name": "Otra", "username": "Con Espacios"}, headers=th).status_code == 422


# ---------- prueba inicial y diagnóstico ----------


def test_material_requires_a_learning_profile(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, _ = _add_student(client, th, room)
    assert client.post(f"/students/{sid}/contents", json={"topic": "fracciones"}, headers=th).status_code == 409


def test_initial_test_creates_the_profile(client, admin_headers, fake_llm):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    cid = client.post(f"/students/{sid}/initial-test", json={"area": "Matemática"}, headers=th).json()["id"]
    test = client.get(f"/contents/{cid}", headers=th).json()
    assert test["status"] == "pendiente" and test["kind"] == "prueba_inicial" and len(test["adapted"]["exercises"]) == 6
    # Nada llega al estudiante sin aprobación
    assert client.get("/my/home", headers=sh).json()["initial_tests"] == []
    client.post(f"/contents/{cid}/review", json={"decision": "aprobado"}, headers=th)
    home = client.get("/my/home", headers=sh).json()
    assert [t["id"] for t in home["initial_tests"]] == [cid] and home["has_profile"] is False
    assert client.post(f"/my/materials/{cid}/assistant", json={"question": "¿qué es?"}, headers=sh).status_code == 403
    answers = [{"index": i, "selected": i % 2, "time_ms": 9000, "confidence": 3} for i in range(6)]
    r = client.post(f"/my/materials/{cid}/submit", json={"answers": answers[:3]}, headers=sh)
    assert r.status_code == 422
    r = client.post(f"/my/materials/{cid}/submit", json={"answers": answers}, headers=sh).json()
    assert all("correct_option" not in x for x in r["results"])
    status = client.get(f"/my/submissions/{r['submission_id']}", headers=sh).json()
    assert status["status"] == "listo" and status["decision"] == "diagnosticado"
    detail = client.get(f"/students/{sid}", headers=th).json()
    assert detail["profile"]["level"] == "en_proceso" and detail["profile_history"][0]["source"] == "prueba_inicial"
    # El diagnóstico recibe el código interno, nunca el nombre del estudiante
    prompt = fake_llm.prompts_for("LearningProfileOut")[0]
    assert "E263B-01" in prompt and "Lucía" not in prompt
    assert client.post(f"/my/materials/{cid}/submit", json={"answers": answers}, headers=sh).status_code == 409


def test_teacher_diagnosis_with_notes(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, _ = _add_student(client, th, room)
    assert client.post(f"/students/{sid}/diagnosis", json={}, headers=th).status_code == 422
    r = client.post(f"/students/{sid}/diagnosis", json={"teacher_notes": "Confunde numerador y denominador"}, headers=th)
    assert r.status_code == 200 and r.json()["profile"]["gaps"] == ["fracciones"]


# ---------- validación docente ----------


def test_returned_material_is_regenerated_with_the_notes(client, admin_headers, fake_llm):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = client.post(f"/students/{sid}/contents", json={"topic": "fracciones"}, headers=th).json()["id"]
    assert client.post(f"/contents/{cid}/review", json={"decision": "devuelto", "note": ""}, headers=th).status_code == 422
    client.post(f"/contents/{cid}/review", json={"decision": "devuelto", "note": "Usa ejemplos con panes"}, headers=th)
    c = client.get(f"/contents/{cid}", headers=th).json()
    assert c["status"] == "pendiente" and c["returns_count"] == 1 and c["reviews"][0]["note"] == "Usa ejemplos con panes"
    assert "Usa ejemplos con panes" in fake_llm.prompts_for("ContentOut")[-1]


def test_third_return_hands_the_material_to_the_teacher(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = client.post(f"/students/{sid}/contents", json={"topic": "fracciones"}, headers=th).json()["id"]
    for _ in range(3):
        client.post(f"/contents/{cid}/review", json={"decision": "devuelto", "note": "Más sencillo, por favor"}, headers=th)
    assert client.get(f"/contents/{cid}", headers=th).json()["status"] == "requiere_docente"


def test_model_failure_stops_and_can_be_retried(client, admin_headers, fake_llm):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, _ = _add_student(client, th, room)
    _with_profile(sid)
    fake_llm.fail_schemas.add("ContentOut")
    cid = client.post(f"/students/{sid}/contents", json={"topic": "fracciones"}, headers=th).json()["id"]
    c = client.get(f"/contents/{cid}", headers=th).json()
    assert c["status"] == "error_ia" and c["base"] is None
    with SessionLocal() as db:
        run = db.query(AgentRun).filter(AgentRun.content_id == cid).one()
        assert run.status == "error" and run.attempts == 3
    fake_llm.fail_schemas.clear()
    assert client.post(f"/contents/{cid}/retry", headers=th).status_code == 202
    assert client.get(f"/contents/{cid}", headers=th).json()["status"] == "pendiente"


def test_adapter_cannot_change_correct_answers(client, admin_headers, fake_llm):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, _ = _add_student(client, th, room)
    _with_profile(sid)
    fake_llm.adapter_changes_answer = True
    cid = client.post(f"/students/{sid}/contents", json={"topic": "fracciones"}, headers=th).json()["id"]
    c = client.get(f"/contents/{cid}", headers=th).json()
    assert c["status"] == "error_ia" and "respuesta correcta" in c["error"]


# ---------- trabajo del estudiante ----------


def test_confident_mistakes_create_one_grouped_reinforcement_and_next_material(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = _approved_material(client, th, sid)
    m = client.get(f"/my/materials/{cid}", headers=sh).json()
    assert "correct_index" not in m["exercises"][0] and "explanation" not in m["exercises"][0]
    answers = [{"index": i, "selected": 1, "time_ms": 5000, "confidence": 5} for i in range(len(m["exercises"]))]
    r = client.post(f"/my/materials/{cid}/submit", json={"answers": answers}, headers=sh).json()
    assert all(x["category_key"] == "entendio_mal" and x["correct_option"] for x in r["results"])
    status = client.get(f"/my/submissions/{r['submission_id']}", headers=sh).json()
    assert status["status"] == "listo" and status["decision"] == "reforzar" and status["has_next_material"]
    assert status["feedback"]["overall"]
    rfs = client.get("/reinforcements?status=pendiente", headers=th).json()
    assert len(rfs) == 1 and len(rfs[0]["data"]["mistakes"]) == len(answers)
    pending = client.get("/contents?status=pendiente", headers=th).json()
    assert len(pending) == 1 and pending[0]["origin"] == "orquestador:reforzar"


def test_repeated_submissions_keep_a_single_pending_proposal(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = _approved_material(client, th, sid)
    answers = [{"index": i, "selected": 0, "time_ms": 40000, "confidence": 3} for i in range(4)]
    for _ in range(2):
        client.post(f"/my/materials/{cid}/submit", json={"answers": answers}, headers=sh)
    assert len(client.get("/contents?status=pendiente", headers=th).json()) == 1
    assert len(client.get("/contents?status=reemplazado", headers=th).json()) == 1


def test_mastery_at_top_level_consolidates_and_reports(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = _approved_material(client, th, sid, difficulty=4)
    answers = [{"index": i, "selected": 0, "time_ms": 3000, "confidence": 5} for i in range(4)]
    r = client.post(f"/my/materials/{cid}/submit", json={"answers": answers}, headers=sh).json()
    assert client.get(f"/my/submissions/{r['submission_id']}", headers=sh).json()["decision"] == "consolidado"
    reports = client.get(f"/students/{sid}", headers=th).json()["reports"]
    assert reports[0]["status"] == "listo" and reports[0]["automatic"]


def test_student_cannot_reach_other_or_pending_materials(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    _, other, _ = _add_student(client, th, room, username="mateo.q")
    _with_profile(sid)
    cid = _approved_material(client, th, sid)
    assert client.get(f"/my/materials/{cid}", headers=other).status_code == 404
    pending = client.post(f"/students/{sid}/contents", json={"topic": "resta"}, headers=th).json()["id"]
    assert client.get(f"/my/materials/{pending}", headers=sh).status_code == 403
    bad = [{"index": 0, "selected": 0, "time_ms": 1, "confidence": 3}] * 2
    assert client.post(f"/my/materials/{cid}/submit", json={"answers": bad}, headers=sh).status_code == 422
    assert client.post(f"/my/materials/{cid}/submit", json={"answers": [{"index": 9, "selected": 0, "time_ms": 1, "confidence": 3}]}, headers=sh).status_code == 422


def test_assistant_keeps_the_conversation_and_hides_answers(client, admin_headers, fake_llm):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = _approved_material(client, th, sid)
    client.post(f"/my/materials/{cid}/assistant", json={"question": "¿Qué es multiplicar?"}, headers=sh)
    r = client.post(f"/my/materials/{cid}/assistant", json={"question": "¿Y con 3 grupos?"}, headers=sh)
    assert r.status_code == 200 and r.json()["follow_up"]
    second = fake_llm.prompts_for("AssistantOut")[1]
    assert "¿Qué es multiplicar?" in second and "correct_index" not in second
    assert len(client.get(f"/my/materials/{cid}/assistant", headers=sh).json()) == 2


# ---------- mando físico ----------


def test_device_events_are_authenticated_and_deduplicated(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, _, body = _add_student(client, th, room)
    _with_profile(sid)
    cid = _approved_material(client, th, sid)
    event = {"message_id": "m-1", "device_id": "mando-07", "student_code": body["student"]["code"], "content_id": cid, "question_index": 0, "selected": "B", "time_ms": 4000, "confidence": 5}
    assert client.post("/devices/events", json=event).status_code == 401
    key = {"X-Device-Key": "clave-dispositivo"}
    r = client.post("/devices/events", json=event, headers=key).json()
    assert r["duplicate"] is False and r["correct"] is False and r["category"] == "Entendió mal"
    assert client.post("/devices/events", json=event, headers=key).json()["duplicate"] is True
    assert len(client.get(f"/students/{sid}", headers=th).json()["events"]) == 1
    assert len(client.get("/reinforcements?status=pendiente", headers=th).json()) == 1


def test_dashboard_and_trace(client, admin_headers):
    th, room = _setup_classroom(client, admin_headers)
    sid, sh, _ = _add_student(client, th, room)
    _with_profile(sid)
    cid = _approved_material(client, th, sid)
    answers = [{"index": i, "selected": 1, "time_ms": 5000, "confidence": 5} for i in range(4)]
    client.post(f"/my/materials/{cid}/submit", json={"answers": answers}, headers=sh)
    d = client.get(f"/classrooms/{room}/dashboard", headers=th).json()
    assert d["kpis"]["answers"] == 4 and d["students"][0]["light"] == "rojo" and d["alerts"][0]["type"] == "concepto"
    assert len(client.get(f"/students/{sid}/progress", headers=th).json()) == 1
    agents = {r["agent"] for r in client.get("/agent-runs", headers=th).json()}
    assert {"generador", "adaptacion", "evaluador", "refuerzo_conceptual"} <= agents
    overview = client.get("/admin/overview", headers=admin_headers).json()
    assert overview["classrooms"][0]["concept_alerts"] == 4
