from src.factcheck import apply_number_check, validate_verdicts

SENTENCES = [{"id": "s004", "item": "m067", "text": "Es soll von 300 auf 350 Euro steigen."}]
ITEMS = {"m067": {"title": "Elterngeld soll steigen", "teaser": "Von 300 auf 330 Euro."}}


def test_number_check_downgrades_belegt():
    verdicts = [{"id": "s004", "verdict": "belegt", "reason": "passt"}]
    checked = apply_number_check(SENTENCES, ITEMS, verdicts)
    assert checked[0]["verdict"] == "nicht_belegt"
    assert checked[0]["by"] == "code"


def test_number_check_never_weakens_widerspricht():
    verdicts = [{"id": "s004", "verdict": "widerspricht", "reason": "350 statt 330"}]
    checked = apply_number_check(SENTENCES, ITEMS, verdicts)
    assert checked[0]["verdict"] == "widerspricht"
    assert checked[0]["by"] == "llm"


def test_validate_verdicts_ok():
    assert validate_verdicts(["s004"], [{"id": "s004", "verdict": "belegt", "reason": "x"}]) == []


def test_validate_verdicts_unknown_verdict():
    verdicts = [{"id": "s004", "verdict": "ungenau", "reason": "x"}]
    assert validate_verdicts(["s004"], verdicts) == [{"id": "s004", "check": "unknown_verdict", "value": "ungenau"}]
    