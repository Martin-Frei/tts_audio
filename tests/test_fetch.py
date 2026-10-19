# tests/test_fetch.py

"""Tests for the fetch stage."""

import time

from fetch import parse_entry


def test_parse_entry_complete():
    entry = {
        "title": "Testtitel",
        "summary": "Testteaser",
        "link": "https://example.com/1",
        "published_parsed": time.strptime("2026-10-19 05:31:49", "%Y-%m-%d %H:%M:%S"),
    }
    item = parse_entry(entry, "tagesschau")

    assert item["source"] == "tagesschau"            # Lücke 1
    assert item["title"] == "Testtitel"
    assert item["teaser"] == "Testteaser"             # Lücke 2
    assert item["published"] == "2026-10-19T05:31:49Z"         # Lücke 3: welches Format liefert to_utc?


def test_parse_entry_missing_teaser():
    entry = {
        "title": "Nur ein Titel",
        "link": "https://example.com/2",
        "published_parsed": None,
    }
    item = parse_entry(entry, "t-online")

    assert item["teaser"] is None  
    assert item["published"] is None
