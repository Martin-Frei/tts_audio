from src.classify import filter_evidence, load_json, load_text, save_classify, validate_batch


def test_load_json_umlauts(tmp_path):
    path = tmp_path / "sample.json"
    path.write_text('{"title": "Hochwasser in Passau, Brücke gesperrt"}', encoding="utf-8")
    assert load_json(path) == {"title": "Hochwasser in Passau, Brücke gesperrt"}


def test_load_text(tmp_path):
    path = tmp_path / "prompt.md"
    path.write_text("Ordne jeder Meldung eine Rubrik zu.", encoding="utf-8")
    assert load_text(path) == "Ordne jeder Meldung eine Rubrik zu."


BATCH = [
    {"id": "m001", "title": "Hochwasser in Passau", "teaser": "3 Tote, Altstadt evakuiert."},
    {"id": "m002", "title": "Bayern gewinnt gegen Dortmund", "teaser": None},
]
CATEGORIES = {"sports", "national_security", "world"}


def ok_results():
    return [
        {"id": "m001", "category": "national_security", "evidence": ["Tote", "evakuiert"]},
        {"id": "m002", "category": "sports", "evidence": ["gewinnt"]},
    ]


def test_validate_batch_ok():
    assert validate_batch(BATCH, ok_results(), CATEGORIES) == []


def test_validate_batch_missing_id():
    results = ok_results()[:1]
    assert validate_batch(BATCH, results, CATEGORIES) == [{"id": "m002", "check": "missing_id"}]


def test_validate_batch_duplicate_id():
    results = ok_results() + [ok_results()[1]]
    assert validate_batch(BATCH, results, CATEGORIES) == [{"id": "m002", "check": "duplicate_id"}]


def test_validate_batch_unknown_id():
    results = ok_results() + [{"id": "m999", "category": "sports", "evidence": ["Tor"]}]
    assert validate_batch(BATCH, results, CATEGORIES) == [{"id": "m999", "check": "unknown_id"}]


def test_validate_batch_unknown_category():
    results = ok_results()
    results[1]["category"] = "football"
    assert validate_batch(BATCH, results, CATEGORIES) == [
        {"id": "m002", "check": "unknown_category", "value": "football"}
    ]


def test_validate_batch_no_evidence():
    results = ok_results()
    results[1]["evidence"] = []
    assert validate_batch(BATCH, results, CATEGORIES) == [{"id": "m002", "check": "no_evidence"}]


def test_filter_evidence_ok_unchanged():
    cleaned, warnings = filter_evidence(BATCH, ok_results())
    assert cleaned == ok_results()
    assert warnings == []


def test_filter_evidence_drops_invalid_word():
    results = ok_results()
    results[0]["evidence"] = ["Tote", "Dammbruch"]
    cleaned, warnings = filter_evidence(BATCH, results)
    assert cleaned[0]["evidence"] == ["Tote"]
    assert warnings == [{"id": "m001", "check": "evidence_dropped", "value": "Dammbruch"}]


def test_filter_evidence_only_invalid_word_leads_to_no_evidence():
    results = ok_results()
    results[1]["evidence"] = ["Tor"]
    cleaned, _ = filter_evidence(BATCH, results)
    assert validate_batch(BATCH, cleaned, CATEGORIES) == [{"id": "m002", "check": "no_evidence"}]


def test_save_classify(tmp_path):
    path = tmp_path / "run_classify.json"
    items = [{"id": "m001", "title": "Brücke gesperrt", "category": "national_security", "evidence": ["gesperrt"]}]
    save_classify(path, "2026-10-28_1100", "ok", None, items, [], [])
    text = path.read_text(encoding="utf-8")
    assert "Brücke" in text
    data = load_json(path)
    assert data["stage"] == "classify"
    assert data["status"] == "ok"
    assert data["items"] == items
