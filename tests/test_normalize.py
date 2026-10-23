from stage_io import load_stage, save_stage
from normalize import normalize

RUN_ID = "2026-10-23_0800"


def write_config(tmp_path):
    whitelist_path = tmp_path / "whitelist.json"
    lexicon_path = tmp_path / "lexicon.json"
    whitelist_path.write_text("[]", encoding="utf-8")
    lexicon_path.write_text('{"DAX": "Dax"}', encoding="utf-8")
    return whitelist_path, lexicon_path


def test_normalize_ok(tmp_path):
    input_path = tmp_path / "clean.json"
    output_path = tmp_path / "normalize.json"
    item = {"id": "m001", "source": "feed_a", "title": "Der DAX steigt",
            "teaser": None, "link": "https://example.org/1"}
    save_stage(input_path, RUN_ID, "clean", [item], "ok")
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(input_path, output_path, RUN_ID, whitelist_path, lexicon_path)

    assert status == "ok"                     # Prüft, ob die Stufe erfolgreich ("ok") durchgelaufen ist.
    result = load_stage(output_path)["items"][0]
    assert result["title"] == "Der Dax steigt" # Prüft, ob das Lexikon "DAX" korrekt zu "Dax" normalisiert wurde.
    assert result["teaser"] is None           # Prüft, ob ein fehlender Teaser (None) korrekt erhalten bleibt.
    assert result["id"] == "m001"             # Prüft, ob die Item-ID unverändert übernommen wurde.


def test_normalize_abort_when_input_missing(tmp_path):
    output_path = tmp_path / "normalize.json"
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(tmp_path / "missing.json", output_path, RUN_ID,
                             whitelist_path, lexicon_path)

    assert status == "abort"                  # Prüft, ob bei fehlender Eingabedatei sauber abgebrochen wird ("abort").
    assert output_path.exists()               # Prüft, ob trotz des Fehlers ein Fehlerbericht (Abort-State) gespeichert wurde.


def test_normalize_abort_when_no_items(tmp_path):
    input_path = tmp_path / "clean.json"
    output_path = tmp_path / "normalize.json"
    save_stage(input_path, RUN_ID, "clean", [], "ok")
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(input_path, output_path, RUN_ID, whitelist_path, lexicon_path)

    assert status == "abort"                  # Prüft, ob bei einer leeren Item-Liste abgebrochen wird.
    assert load_stage(output_path)["reason"] == "no items in input" # Prüft, ob der korrekte Fehlergrund protokolliert wurde.
