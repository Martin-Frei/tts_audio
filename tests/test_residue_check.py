# tests/test_residue_check.py


from stage_io import load_stage, save_stage
from residue_check import residue_check

RUN_ID = "2026-10-26_0800"                                              # Feste Test-Kennung für den Testlauf


def test_residue_check_ok_without_findings(tmp_path):
    input_path = tmp_path / "normalize.json"                            # Temporärer Pfad für Input
    output_path = tmp_path / "residue_check.json"                       # Temporärer Pfad für Output
    item = {"id": "m001", "title": "Der Dax steigt", "teaser": None}    # Test-Item title == ok Teaser == None
    save_stage(input_path, RUN_ID, "normalize", [item], "ok")           # Speichert die Test-Datei

    status, path = residue_check(input_path, output_path, RUN_ID)       # Führt residue_checkaus

    assert status == "ok"                                               # Prüft, ob der Status ohne Funde "ok" ist
    assert load_stage(output_path)["items"] == []                       # Prüft, ob die Fundliste (findings) leer ist


def test_residue_check_abort_with_findings(tmp_path):
    input_path = tmp_path / "normalize.json"                            # Temporärer Pfad für Input
    output_path = tmp_path / "residue_check.json"                       # Temporärer Pfad für Output
    item = {"id": "m001", "title": "BMW 7er", "teaser": None}           # Test-Item title == Reste Teaser == None
    save_stage(input_path, RUN_ID, "normalize", [item], "ok")           # Speichert die Test-Datei

    status, path = residue_check(input_path, output_path, RUN_ID)       # Führt residue_checkaus

    assert status == "abort"                                            # Prüft ob Staus abort
    findings = load_stage(output_path)["items"]                         # Lädt gefundne Rest in findings
    assert len(findings) == 2                                           # Prüft ob 2 Treffer (BMW und 7)
    assert findings[0] == {"id": "m001", "field": "title", "found": "BMW"} # Erste item in findings ist BMW


def test_residue_check_abort_when_input_missing(tmp_path):
    output_path = tmp_path / "residue_check.json"                       # Temporärer Pfad für Output

    status, path = residue_check(tmp_path / "missing.json", output_path, RUN_ID) # Test mit nicht vorhandenenr Datei 

    assert status == "abort"                                            # Prüft ob Staus abort
    assert output_path.exists()                                         # Prüft ob eine Output Datei gechrieben worden ist
