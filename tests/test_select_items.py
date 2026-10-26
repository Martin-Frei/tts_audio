from stage_io import load_stage, save_stage
from select_items import select_items

RUN_ID = "2026-10-26_0800"


def test_select_items_keeps_newest(tmp_path):
    input_path = tmp_path / "normalize.json"                # Temp Input Pfad
    output_path = tmp_path / "select_items.json"            # Temp Output Pfad
    items = [
        {"id": "m001", "title": "A", "teaser": None, "published": "2026-10-26T06:00:00Z"},  # Älterer Artikel
        {"id": "m002", "title": "B", "teaser": None, "published": None},                    # Artikel ohen Datum
        {"id": "m003", "title": "C", "teaser": None, "published": "2026-10-26T07:00:00Z"},  # Neuerer Artikel
    ]
    save_stage(input_path, RUN_ID, "normalize", items, "ok")                                # Speichert Input Datei

    status, path = select_items(input_path, output_path, RUN_ID, max_items=2)               # Führt select_items aus 

    assert status == "ok"                                                                   # Prüft ob ok ist
    selected = load_stage(output_path)["items"]                                             # Lädt die Artikel
    assert [item["id"] for item in selected] == ["m003", "m001"]                            # Überprüft Anzahl und richtige Artikel absteigen ausgewählt worden sind


def test_select_items_abort_when_input_missing(tmp_path):
    output_path = tmp_path / "select_items.json"                                            # Temporärer Pfad und Name für Ergebnis

    status, path = select_items(tmp_path / "missing.json", output_path, RUN_ID)             # Test mit nicht vohandener Datei

    assert status == "abort"                                                                # Prüft ob abort ist   
    assert output_path.exists()                                                             # Prüft ob eien Datei geschrieben worden ist


def test_select_items_abort_when_no_items(tmp_path):
    input_path = tmp_path / "normalize.json"                                                # Temporärer Pfad und Name für Input datei
    output_path = tmp_path / "select_items.json"                                            # Temporärer Pfad und Name für Ergebnis
    save_stage(input_path, RUN_ID, "normalize", [], "ok")                                   # Speichert leere Liste als input

    status, path = select_items(input_path, output_path, RUN_ID)                            # Führte Selektion mit leere Liste aus 

    assert status == "abort"                                                                # Prüft ob abort
    assert load_stage(output_path)["reason"] == "no items in input"                         # prüft ob Datei reason enthält 
