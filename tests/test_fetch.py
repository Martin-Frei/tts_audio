# tests/test_fetch.py

"""Tests for the fetch stage."""

import time
import json

from fetch import parse_entry, save_raw


def test_parse_entry_complete():
    entry = {
        "title": "Testtitel",
        "summary": "Testteaser",
        "link": "https://example.com/1",
        "published_parsed": time.strptime("2026-10-19 05:31:49", "%Y-%m-%d %H:%M:%S"),
    }
    item = parse_entry(entry, "tagesschau")

    assert item["source"] == "tagesschau" 
    assert item["title"] == "Testtitel"
    assert item["teaser"] == "Testteaser"  
    assert item["published"] == "2026-10-19T05:31:49Z" 


def test_parse_entry_missing_teaser():
    entry = {
        "title": "Nur ein Titel",
        "link": "https://example.com/2",
        "published_parsed": None,
    }
    item = parse_entry(entry, "t-online")

    assert item["teaser"] is None  
    assert item["published"] is None
    

def test_save_raw_writes_file(tmp_path):
    path = tmp_path / "test_raw.json"
    items = [
        {
            "id": "m001",
            "source": "feed_a",
            "title": "Bäckerei öffnet neue Filiale",
            "teaser": None,
            "link": "https://example.org/1",
            "published": "2026-10-19T05:31:49Z",
        }
    ]

    save_raw(path, "2026-10-21_0800", items, "ok")

    assert path.exists()                        

    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    assert data["run_id"] == "2026-10-21_0800"               
    assert data["stage"] == "fetch"  
    assert data["status"] == "ok"
    assert data["reason"] is None 
    assert data["items"] == items 
    assert data["created"].endswith("Z")    

    text = path.read_text(encoding="utf-8")
    assert "Bäckerei" in text 
