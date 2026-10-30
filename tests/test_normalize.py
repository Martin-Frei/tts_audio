from stage_io import load_stage, save_stage
from normalize import normalize, normalize_text

RUN_ID = "2026-10-23_0800"


def write_config(tmp_path):
    whitelist_path = tmp_path / "whitelist.json"
    lexicon_path = tmp_path / "lexicon.json"
    whitelist_path.write_text("[]", encoding="utf-8")
    lexicon_path.write_text('{"DAX": "Dax"}', encoding="utf-8")
    return whitelist_path, lexicon_path


def test_normalize_ok(tmp_path):
    input_path = tmp_path / "factcheck_apply.json"
    output_path = tmp_path / "normalize.json"
    sentence = {"id": "s001", "item": "m001", "kind": "content",
                "text": "Der DAX steigt"}                                                       # Ein Satz wie in der Ausgabe von factcheck_apply
    save_stage(input_path, RUN_ID, "factcheck_apply", [sentence], "ok", key="sentences")      # Eingabedatei mit der Satzliste unter "sentences" anlegen
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(input_path, output_path, RUN_ID, whitelist_path, lexicon_path)

    assert status == "ok"                     # Prüft, ob die Stufe erfolgreich ("ok") durchgelaufen ist.
    result = load_stage(output_path)["sentences"][0]                                            # Ersten Satz aus der Ausgabe unter "sentences" holen
    assert result["text"] == "Der Dax steigt" # Prüft, ob das Lexikon "DAX" korrekt zu "Dax" normalisiert wurde.
    assert result["id"] == "s001"             # Prüft, ob die Satz-ID unverändert übernommen wurde.
    assert result["item"] == "m001"           # Prüft, ob der Verweis auf die Meldung unverändert übernommen wurde.
    assert result["kind"] == "content"        # Prüft, ob die Satzart unverändert durchgereicht wurde.


def test_normalize_abort_when_old_input(tmp_path):
    input_path = tmp_path / "clean.json"
    output_path = tmp_path / "normalize.json"
    item = {"id": "m001", "source": "feed_a", "title": "Der DAX steigt",
            "teaser": None, "link": "https://example.org/1"}                                    # Alte Eingabe aus Phase 1: Meldung mit Titel und Teaser
    save_stage(input_path, RUN_ID, "clean", [item], "ok")                                      # Ohne key: landet unter "items" wie bei clean
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(input_path, output_path, RUN_ID, whitelist_path, lexicon_path)

    assert status == "abort"                                                                    # Prüft, ob normalize Meldungen statt Sätzen ablehnt
    assert load_stage(output_path)["reason"] == "no sentences in input"                         # Prüft den Abbruchgrund
    assert load_stage(output_path)["sentences"] == []                                           # Prüft, ob auch der Abbruch unter "sentences" schreibt


def test_normalize_abort_when_input_missing(tmp_path):
    output_path = tmp_path / "normalize.json"
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(tmp_path / "missing.json", output_path, RUN_ID,
                             whitelist_path, lexicon_path)

    assert status == "abort"                  # Prüft, ob bei fehlender Eingabedatei sauber abgebrochen wird ("abort").
    assert output_path.exists()               # Prüft, ob trotz des Fehlers ein Fehlerbericht (Abort-State) gespeichert wurde.


def test_normalize_abort_when_no_sentences(tmp_path):
    input_path = tmp_path / "factcheck_apply.json"
    output_path = tmp_path / "normalize.json"
    save_stage(input_path, RUN_ID, "factcheck_apply", [], "ok", key="sentences")              # Leere Satzliste unter "sentences"
    whitelist_path, lexicon_path = write_config(tmp_path)

    status, path = normalize(input_path, output_path, RUN_ID, whitelist_path, lexicon_path)

    assert status == "abort"                  # Prüft, ob bei einer leeren Item-Liste abgebrochen wird.
    assert load_stage(output_path)["reason"] == "no sentences in input" # Prüft, ob der korrekte Fehlergrund protokolliert wurde.

def test_number_with_period_without_signal_word_stays():
    """Without a signal word, '55.' before a word stays as digits (loud)."""
    text = "Er wurde 55. Danach zog er nach Berlin."
    result = normalize_text(text, [], {})
    assert result == "Er wurde 55. Danach zog er nach Berlin."
