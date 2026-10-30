# tests/test_residue_check.py


from stage_io import load_stage, save_stage
from residue_check import residue_check

RUN_ID = "2026-10-26_0800"                                              # Feste Test-Kennung für den Testlauf


def test_residue_check_ok_without_findings(tmp_path):
    input_path = tmp_path / "normalize.json"                            # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                       # TemporärerPfad für Output
    sentence = {"id": "s001", "item": "m001", "kind": "content", "text": "Der Dax steigt."}  # Test-Satz ohne Reste
    save_stage(input_path, RUN_ID, "normalize", [sentence], "ok", key="sentences")          # Speichert die Test-Datei unter "sentences"

    status, path = residue_check(input_path, output_path, RUN_ID)       # Führt residue_checkaus

    assert status == "ok"                                               # Prüft, ob der Status ohne Funde "ok" ist
    assert load_stage(output_path)["findings"] == []                    # Prüft, ob die Fundliste leer ist


def test_residue_check_abort_with_findings(tmp_path):
    input_path = tmp_path / "normalize.json"                            # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                       # TemporärerPfad für Output
    sentence = {"id": "s012", "item": "m001", "kind": "content", "text": "BMW 7er"}  # Test-Satz mit Resten
    save_stage(input_path, RUN_ID, "normalize", [sentence], "ok", key="sentences")  # Speichert die Test-Datei unter "sentences"

    status, path = residue_check(input_path, output_path, RUN_ID)       # Führt residue_checkaus

    assert status == "abort"                                            # Prüft ob Staus abort
    findings = load_stage(output_path)["findings"]                      # Lädt gefundne Rest in findings
    assert findings == [{"id": "s012", "found": "BMW"},
                        {"id": "s012", "found": "7"}]                   # Prüft, ob genau diese Reste mit Satz-ID gefunden wurden


def test_residue_check_abort_when_normalize_aborted(tmp_path):
    input_path = tmp_path / "normalize.json"                            # TemporärerPfad für Input
    output_path = tmp_path / "residue_check.json"                       # TemporärerPfad für Output
    save_stage(input_path, RUN_ID, "normalize", [], "abort", "no sentences in input", key="sentences")  # normalize hat abgebrochen

    status, path = residue_check(input_path, output_path, RUN_ID)       # Führt residue_checkaus

    assert status == "abort"                                            # Prüft, ob eine leere Kiste nicht als ok durchgeht
    assert "normalize not released" in load_stage(output_path)["reason"]  # Prüft den richtigen Grund, nicht nur den Status


def test_residue_check_abort_when_input_missing(tmp_path):
    output_path = tmp_path / "residue_check.json"                       # TemporärerPfad für Output

    status, path = residue_check(tmp_path / "missing.json", output_path, RUN_ID)  # Führt residue_check mit fehlender Eingabe aus

    assert status == "abort"                                            # Prüft, ob bei fehlender Eingabedatei abgebrochen wird
    assert output_path.exists()                                         # Prüft, ob trotzdem ein Prüfprotokoll geschrieben wurde
    assert load_stage(output_path)["findings"] == []                    # Prüft, ob auch der Abbruch unter "findings" schreibt
