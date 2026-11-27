"""Reglas determinísticas de la Sección 16. Se aplican antes que la IA ("reglas antes que IA")."""

from dataclasses import dataclass

CATEGORIES = {
    "entendio_mal": {"label": "Entendió mal", "action": "Explica de otra forma y corrige el error.", "rule": 1},
    "no_sabe": {"label": "No sabe el tema", "action": "Explica de nuevo, de forma más simple.", "rule": 2},
    "lo_domina": {"label": "Lo domina", "action": "Sube la dificultad.", "rule": 3},
    "falta_practica": {"label": "Le falta práctica", "action": "Da más ejercicios del mismo nivel.", "rule": 4},
}

# Sección 20.4: con menos de 3 respuestas del tema el Orquestador no decide
MIN_WINDOW = 3
MAX_DIFFICULTY = 4


def classify(correct: bool, confidence: int, time_ms: int, expected_ms: int, changes: int) -> str:
    """Clasifica una respuesta. La regla 1 va primero: un error con alta confianza indica un concepto equivocado."""
    secure = confidence >= 4
    fast = time_ms <= expected_ms
    undecided = changes >= 2
    if not correct and secure:
        return "entendio_mal"
    if not correct:
        return "no_sabe"
    if secure and fast and not undecided:
        return "lo_domina"
    return "falta_practica"


def traffic_light(accuracy: float | None) -> str:
    """Semáforo del dashboard: verde ≥ 80 %, ámbar 60–79 %, rojo < 60 %."""
    if accuracy is None:
        return "sin_datos"
    if accuracy >= 0.8:
        return "verde"
    if accuracy >= 0.6:
        return "ambar"
    return "rojo"


@dataclass
class Decision:
    action: str  # subir | mantener | simplificar | reforzar | consolidado | esperar
    difficulty: int
    reason: str


def decide_next(categories: list[str], current_difficulty: int) -> Decision:
    """Decisión del Orquestador con las últimas respuestas del tema, no con una sola (CU-IA-07)."""
    n = len(categories)
    if n < MIN_WINDOW:
        return Decision("esperar", current_difficulty, f"Hay {n} respuesta(s) del tema; se necesitan al menos {MIN_WINDOW} para decidir.")
    counts = {c: categories.count(c) for c in CATEGORIES}
    correct = counts["lo_domina"] + counts["falta_practica"]
    if counts["entendio_mal"] >= 2 or (categories[-1] == "entendio_mal" and counts["entendio_mal"] * 2 >= n):
        return Decision("reforzar", current_difficulty, "Errores con alta confianza: posible concepto equivocado.")
    if counts["no_sabe"] * 2 >= n:
        return Decision("simplificar", max(1, current_difficulty - 1), "La mayoría de errores fueron con baja confianza.")
    if correct / n >= 0.8 and current_difficulty >= MAX_DIFFICULTY:
        return Decision("consolidado", current_difficulty, "Acierto de 80 % o más en el nivel más alto: tema consolidado.")
    if counts["lo_domina"] * 2 > n and correct == n:
        return Decision("subir", min(MAX_DIFFICULTY, current_difficulty + 1), "Respuestas correctas, seguras y rápidas.")
    return Decision("mantener", current_difficulty, "Necesita más práctica en el mismo nivel.")
