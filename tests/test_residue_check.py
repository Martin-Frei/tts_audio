from stage_io import load_stage, save_stage
from residue_check import residue_check

RUN_ID = "2026-10-26_0800"


def segment(text):
    return {"id": "b003", "item": "m001", "kind": "content",
            "sentence_ids": ["s012", "s013"], "text": text}                       # Ein Segment wie von preprocess_piper


def test_residue_check_ok_without_findings(tmp_path):
    input_path = tmp_path / "preprocess_piper.json"                             # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                               # TemporärerPfad für Output
    save_stage(input_path, RUN_ID, "preprocess_piper", [segment("Der Dax steigt.")], "ok", key="segments")  # Segment ohne Reste

    status, path = residue_check(input_path, output_path, RUN_ID)               # Führt residue_checkaus

    assert status == "ok"                                                       # Prüft, ob der Status ohne Funde "ok" ist
    assert load_stage(output_path)["findings"] == []                            # Prüft, ob die Fundliste leer ist


def test_residue_check_abort_with_findings(tmp_path):
    input_path = tmp_path / "preprocess_piper.json"                             # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                               # TemporärerPfad für Output
    save_stage(input_path, RUN_ID, "preprocess_piper", [segment("BMW 7er")], "ok", key="segments")  # Segment mit Resten

    status, path = residue_check(input_path, output_path, RUN_ID)               # Führt residue_checkaus

    assert status == "abort"                                                    # Prüft ob Staus abort
    findings = load_stage(output_path)["findings"]                              # Lädt gefundne Rest in findings
    assert findings == [{"id": "b003", "sentence_ids": ["s012", "s013"], "found": "BMW"},
                        {"id": "b003", "sentence_ids": ["s012", "s013"], "found": "7"}]  # Genau diese Reste mit Spur zu den Sätzen


def test_residue_check_abort_with_list_in_text(tmp_path):
    input_path = tmp_path / "preprocess_piper.json"                             # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                               # TemporärerPfad für Output
    broken = "['Zwei Waggons sollen entgleist sein.', 'Die Strecke wurde gesperrt.']"  # Fehler in preprocess: Liste als Text
    save_stage(input_path, RUN_ID, "preprocess_piper", [segment(broken)], "ok", key="segments")

    status, path = residue_check(input_path, output_path, RUN_ID)               # Führt residue_checkaus

    assert status == "abort"                                                    # Endkontrolle fängt den Fehler von preprocess
    assert {"[", "]"} <= {f["found"] for f in load_stage(output_path)["findings"]}  # Klammern als Funde gemeldet


def test_residue_check_abort_when_input_not_released(tmp_path):
    input_path = tmp_path / "preprocess_piper.json"                             # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                               # TemporärerPfad für Output
    save_stage(input_path, RUN_ID, "preprocess_piper", [], "abort", "no sentences in input", key="segments")  # Vorstufe hat abgebrochen

    status, path = residue_check(input_path, output_path, RUN_ID)               # Führt residue_checkaus

    assert status == "abort"                                                    # Prüft, ob eine leere Kiste nicht als ok durchgeht
    assert "input not released" in load_stage(output_path)["reason"]            # Prüft den richtigen Grund, nicht nur den Status


def test_residue_check_abort_when_input_missing(tmp_path):
    output_path = tmp_path / "residue_check.json"                               # TemporärerPfad für Output

    status, path = residue_check(tmp_path / "missing.json", output_path, RUN_ID)  # Führt residue_check mit fehlender Eingabe aus

    assert status == "abort"                                                    # Prüft, ob bei fehlender Eingabedatei abgebrochen wird
    assert output_path.exists()                                                 # Prüft, ob trotzdem ein Prüfprotokoll geschrieben wurde
    assert load_stage(output_path)["findings"] == []                            # Prüft, ob auch der Abbruch unter "findings" schreibt
