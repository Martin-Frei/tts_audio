from src.factcheck_apply import dropped_items, remove_items, remove_orphan_transitions

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
