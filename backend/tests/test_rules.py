import pytest

from app.rules import classify, decide_next, traffic_light


@pytest.mark.parametrize(
    "correct,conf,ms,expected,changes,cat",
    [
        (False, 5, 1000, 20000, 0, "entendio_mal"),  # regla 1: error con alta confianza
        (False, 4, 90000, 20000, 3, "entendio_mal"),  # la regla 1 gana aunque sea lenta e indecisa
        (False, 3, 1000, 20000, 0, "no_sabe"),
        (False, 1, 1000, 20000, 0, "no_sabe"),
        (True, 5, 20000, 20000, 1, "lo_domina"),  # tiempo igual al esperado cuenta como rápido
        (True, 4, 25000, 20000, 0, "falta_practica"),  # lenta
        (True, 3, 1000, 20000, 0, "falta_practica"),  # confianza intermedia
        (True, 5, 1000, 20000, 2, "falta_practica"),  # indecisa
    ],
)
def test_classify_follows_section_16(correct, conf, ms, expected, changes, cat):
    assert classify(correct, conf, ms, expected, changes) == cat


@pytest.mark.parametrize("acc,light", [(None, "sin_datos"), (0.8, "verde"), (0.79, "ambar"), (0.6, "ambar"), (0.59, "rojo")])
def test_traffic_light_thresholds(acc, light):
    assert traffic_light(acc) == light


def test_decide_raises_difficulty_when_mastered():
    d = decide_next(["lo_domina", "lo_domina", "falta_practica"], 2)
    assert d.action == "subir" and d.difficulty == 3


def test_decide_never_exceeds_limits():
    assert decide_next(["lo_domina"] * 3, 4).difficulty == 4
    assert decide_next(["no_sabe"] * 3, 1).difficulty == 1


def test_decide_simplifies_when_does_not_know():
    d = decide_next(["no_sabe", "no_sabe", "falta_practica"], 3)
    assert d.action == "simplificar" and d.difficulty == 2


def test_decide_reinforces_repeated_misconceptions():
    assert decide_next(["entendio_mal", "lo_domina", "entendio_mal"], 2).action == "reforzar"


def test_decide_uses_window_not_single_answer():
    # Un solo "Lo domina" entre prácticas no basta para subir
    assert decide_next(["falta_practica", "falta_practica", "lo_domina"], 2).action == "mantener"


def test_decide_waits_for_three_answers():
    # Sección 20.4: con menos de 3 respuestas del tema no se decide
    assert decide_next(["entendio_mal", "entendio_mal"], 2).action == "esperar"


def test_decide_marks_topic_consolidated_at_top_level():
    d = decide_next(["lo_domina", "lo_domina", "falta_practica", "lo_domina"], 4)
    assert d.action == "consolidado" and d.difficulty == 4
