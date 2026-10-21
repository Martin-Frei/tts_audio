import json

from clean import clean, load_raw, save_clean


def write_raw(path, items):
    """Helper: write a small raw file. Not a test, name has no test_ prefix."""
    data = {
        "run_id": "2026-10-21_0800",
        "stage": "fetch",
        "created": "2026-10-21T08:00:14Z",
        "status": "ok",
        "reason": None,
        "items": items,
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_load_raw_returns_dictionary(tmp_path):
    path = tmp_path / "raw.json"
    write_raw(path, [])

    data = load_raw(path)

    assert isinstance(data, dict)
    assert data["stage"] == "fetch"


def test_save_clean_writes_metadata(tmp_path):
    path = tmp_path / "clean.json"
    items = [{"id": "m001", "title": "Brücke gesperrt", "teaser": None}]

    save_clean(path, "2026-10-21_0800", items, "ok")

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "2026-10-21_0800"
    assert data["stage"] == "clean"
    assert data["created"].endswith("Z")
    assert data["status"] == "ok"
    assert data["reason"] is None
    assert data["items"] == items
    assert "Brücke" in path.read_text(encoding="utf-8")


def test_clean_ok_cleans_text_and_keeps_items(tmp_path):
    raw_path = tmp_path / "raw.json"
    clean_path = tmp_path / "clean.json"
    write_raw(raw_path, [
        {
            "id": "m001",
            "source": "feed_a",
            "title": "+++ Brand in Beispielstadt +++ ",
            "teaser": "Die „KI\u2011Strategie“ steht.  ",
            "link": "https://example.org/1",
            "published": "2026-10-21T05:31:49Z",
        },
        {
            "id": "m002",
            "source": "feed_b",
            "title": "Nur ein Titel",
            "teaser": None,
            "link": "https://example.org/2",
            "published": None,
        },
    ])

    status, path = clean(raw_path, clean_path, "2026-10-21_0800")

    assert status == "ok"
    assert path == clean_path
    items = json.loads(clean_path.read_text(encoding="utf-8"))["items"]
    assert len(items) == 2
    assert items[0]["title"] == "Brand in Beispielstadt"
    assert items[0]["teaser"] == 'Die "KI-Strategie" steht.'
    assert items[0]["link"] == "https://example.org/1"
    assert items[0]["published"] == "2026-10-21T05:31:49Z"
    assert items[1]["teaser"] is None
    assert items[1]["published"] is None


def test_clean_abort_when_raw_file_missing(tmp_path):
    clean_path = tmp_path / "clean.json"

    status, path = clean(tmp_path / "missing.json", clean_path, "2026-10-21_0800")

    assert status == "abort"
    assert clean_path.exists()
    data = json.loads(clean_path.read_text(encoding="utf-8"))
    assert data["items"] == []
    assert data["reason"].startswith("raw file not readable")


def test_clean_abort_when_no_items(tmp_path):
    raw_path = tmp_path / "raw.json"
    clean_path = tmp_path / "clean.json"
    write_raw(raw_path, [])

    status, path = clean(raw_path, clean_path, "2026-10-21_0800")

    assert status == "abort"
    data = json.loads(clean_path.read_text(encoding="utf-8"))
    assert data["reason"] == "raw file has no items"
