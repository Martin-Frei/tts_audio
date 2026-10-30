from stage_io import load_stage, save_stage
from preprocess_piper import preprocess_piper

RUN_ID = "2026-10-28_1429"

SENTENCES = [
    {"id": "s001", "item": None, "kind": "greeting", "text": "Guten Tag."},
    {"id": "s002", "item": None, "kind": "transition", "text": "Und nun zur Politik."},
    {"id": "s003", "item": "m067", "kind": "content", "text": "Das Elterngeld soll steigen."},
    {"id": "s004", "item": "m067", "kind": "content", "text": "Die Regierung hat sich geeinigt"},
    {"id": "s005", "item": "m002", "kind": "content", "text": "Zwei Waggons sollen entgleist sein."},
    {"id": "s006", "item": None, "kind": "ai_note", "text": "Dieses Briefing wurde mit KI erstellt."},
]


def run(tmp_path, sentences, status="ok"):
    input_path = tmp_path / "normalize.json"
    output_path = tmp_path / "preprocess_piper.json"
    save_stage(input_path, RUN_ID, "normalize", sentences, status, key="sentences")  # Eingabe wie von normalize
    status, path = preprocess_piper(input_path, output_path, RUN_ID)
    return status, load_stage(path)


def test_preprocess_piper_builds_segments(tmp_path):
    status, data = run(tmp_path, SENTENCES)
    segments = data["segments"]

    assert status == "ok"                                                       # Stufe läuft durch
    assert [s["id"] for s in segments] == ["b001", "b002", "b003", "b004", "b005"]  # Fünf Segmente in Sendereihenfolge
    assert segments[2]["sentence_ids"] == ["s003", "s004"]                      # Zwei Sätze einer Meldung in einem Segment
    assert segments[2]["text"] == "Das Elterngeld soll steigen. Die Regierung hat sich geeinigt."  # Verbunden, Punkt ergänzt
    assert segments[3]["item"] == "m002"                                        # Neue Meldung, neues Segment
    assert segments[0]["kind"] == "greeting"                                    # Zeile ohne Meldung behält ihre Art
    assert all("[" not in s["text"] for s in segments)                          # Keine Liste als Text im Segment


def test_preprocess_piper_abort_when_normalize_aborted(tmp_path):
    status, data = run(tmp_path, [], status="abort")

    assert status == "abort"                                                    # Leere Kiste geht nicht durch
    assert "input not released" in data["reason"]                               # Richtiger Grund
    assert data["segments"] == []                                               # Abbruch schreibt auch unter "segments"


def test_preprocess_piper_abort_when_text_missing(tmp_path):
    sentences = SENTENCES[:2] + [{"id": "s003", "item": "m067", "kind": "content", "text": None}]
    status, data = run(tmp_path, sentences)

    assert status == "abort"                                                    # Satz ohne Text stoppt die Stufe
    assert "s003" in data["reason"]                                             # Grund nennt die Satz-ID


def test_preprocess_piper_abort_when_no_sentences(tmp_path):
    status, data = run(tmp_path, [])

    assert status == "abort"                                                    # Keine Sätze, kein Segment
    assert data["reason"] == "no sentences in input"
