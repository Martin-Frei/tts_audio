import json

import pytest

from stage_io import load_stage, save_stage


def test_save_stage_writes_metadata_and_items(tmp_path):
    path = tmp_path / "news_2026-10-23_0800_normalize.json"
    items = [{"id": "m001", "title": "Brücke in Beispielstadt", "teaser": None}]

    save_stage(path, "2026-10-23_0800", "normalize", items, "ok")

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "2026-10-23_0800"
    assert data["stage"] == "normalize"
    assert data["status"] == "ok"
    assert data["reason"] is None
    assert data["created"].endswith("Z")
    assert data["items"] == items
    assert "Brücke" in path.read_text(encoding="utf-8")


def test_save_stage_creates_missing_folder(tmp_path):
    path = tmp_path / "news" / "2026-10-23_0800" / "news_2026-10-23_0800_normalize.json"

    save_stage(path, "2026-10-23_0800", "normalize", [], "abort", "no items")

    assert path.exists()


def test_load_stage_reads_file_back(tmp_path):
    path = tmp_path / "stage.json"
    save_stage(path, "2026-10-23_0800", "clean", [{"id": "m001"}], "ok")

    data = load_stage(path)

    assert data["stage"] == "clean"
    assert data["items"] == [{"id": "m001"}]


def test_load_stage_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_stage(tmp_path / "missing.json")
