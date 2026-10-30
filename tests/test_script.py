from src.script import validate_script

ITEMS = [{"id": "m001"}, {"id": "m002"}]


def ok_results():
    return [
        {"item": "m001", "sentences": ["Satz eins.", "Satz zwei."]},
        {"item": "m002", "sentences": ["Satz drei."]},
    ]


def test_validate_script_ok():
    assert validate_script(ITEMS, ok_results()) == []


def test_validate_script_missing_item():
    assert validate_script(ITEMS, ok_results()[:1]) == [{"item": "m002", "check": "missing_item"}]


def test_validate_script_unknown_item():
    results = ok_results() + [{"item": "m999", "sentences": ["Erfunden."]}]
    assert validate_script(ITEMS, results) == [{"item": "m999", "check": "unknown_item"}]


def test_validate_script_empty_sentence():
    results = ok_results()
    results[0]["sentences"] = ["Satz eins.", "   "]
    assert validate_script(ITEMS, results) == [{"item": "m001", "check": "empty_sentence", "value": 2}]
