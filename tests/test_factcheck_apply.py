import json
from pathlib import Path

from src.factcheck_apply import dropped_items, factcheck_apply, remove_items, remove_orphan_transitions

SENTENCES = [
    {"id": "s001", "kind": "greeting", "item": None},
    {"id": "s002", "kind": "transition", "item": None},
    {"id": "s003", "kind": "source", "item": "m001"},
    {"id": "s004", "kind": "content", "item": "m001"},
    {"id": "s005", "kind": "transition", "item": None},
    {"id": "s006", "kind": "source", "item": "m066"},
    {"id": "s007", "kind": "content", "item": "m066"},
    {"id": "s008", "kind": "content", "item": "m066"},
    {"id": "s009", "kind": "ai_note", "item": None},
]


def ids(lines):
    return [line["id"] for line in lines]


def test_dropped_items_one_unsupported_sentence_drops_the_item():
    verdicts = [{"id": "s004", "verdict": "belegt"}, {"id": "s007", "verdict": "belegt"},
                {"id": "s008", "verdict": "nicht_belegt"}]
    assert dropped_items(verdicts, SENTENCES) == ["m066"]


def test_remove_items_keeps_lines_without_item():
    assert ids(remove_items(SENTENCES, ["m066"])) == ["s001", "s002", "s003", "s004", "s005", "s009"]


def test_items_first_then_transitions():
    lines = remove_orphan_transitions(remove_items(SENTENCES, ["m066"]))
    assert ids(lines) == ["s001", "s002", "s003", "s004", "s009"]


def test_transitions_first_leaves_an_orphan():
    lines = remove_items(remove_orphan_transitions(SENTENCES), ["m066"])
    assert "s005" in ids(lines)


def test_dropped_items_includes_contradiction():
    verdicts = [{"id": "s004", "verdict": "belegt"}, {"id": "s007", "verdict": "widerspricht"},
                {"id": "s008", "verdict": "belegt"}]
    assert dropped_items(verdicts, SENTENCES) == ["m066"]


def test_reviewed_contradiction_is_removed(tmp_path: Path):
    sentences = [
        {"id": "s001", "item": None, "kind": "greeting", "text": "Guten Tag."},
        {"id": "s002", "item": None, "kind": "transition", "text": "Und nun zur Politik."},
        {"id": "s003", "item": "m001", "kind": "source", "text": "Wie die Tagesschau berichtet."},
        {"id": "s004", "item": "m001", "kind": "content", "text": "Das Elterngeld steigt auf 330 Euro."},
        {"id": "s005", "item": None, "kind": "transition", "text": "Zum Thema Wirtschaft."},
        {"id": "s006", "item": "m002", "kind": "source", "text": "Wie das Handelsblatt berichtet."},
        {"id": "s007", "item": "m002", "kind": "content", "text": "Die Miete steigt um 380 Euro."},
        {"id": "s008", "item": None, "kind": "ai_note", "text": "Dieses Briefing wurde mit KI erstellt."},
    ]
    items = [{"id": "m001"}, {"id": "m002"}]
    verdicts = [
        {"id": "s004", "verdict": "belegt", "reason": "matches source", "by": "llm"},
        {"id": "s007", "verdict": "widerspricht", "reason": "source says 330 Euro", "by": "human"},
    ]
    run_id = "2026-10-28_1429"
    base = {"run_id": run_id, "sentences": sentences, "items": items, "verdicts": verdicts}

    input_path = tmp_path / f"news_{run_id}_factcheck.json"
    reviewed = tmp_path / f"news_{run_id}_factcheck_reviewed.json"
    output_path = tmp_path / f"news_{run_id}_factcheck_apply.json"
    input_path.write_text(json.dumps({**base, "stage": "factcheck", "status": "stop"}), encoding="utf-8")
    reviewed.write_text(json.dumps({**base, "stage": "review", "status": "ok"}), encoding="utf-8")

    status, path = factcheck_apply(input_path, output_path, run_id)
    result = json.loads(path.read_text(encoding="utf-8"))
    remaining_ids = [sentence["id"] for sentence in result["sentences"]]

    assert status == "ok"
    assert result["used_file"] == reviewed.name
    assert remaining_ids == ["s001", "s002", "s003", "s004", "s008"]
    assert result["removed"] == [{"item": "m002", "reasons": ["source says 330 Euro"]}]
