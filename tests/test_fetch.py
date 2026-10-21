# tests/test_fetch.py

"""Tests for the fetch stage."""

import time
import json
import requests

from fetch import fetch, fetch_feed, load_feed_list, parse_entry, save_raw


SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Testfeed</title>
    <item>
      <title>Bäckerei öffnet neue Filiale</title>
      <description>Nach drei Jahren Bauzeit.</description>
      <link>https://example.org/1</link>
      <pubDate>Mon, 19 Oct 2026 07:31:49 +0200</pubDate>
    </item>
    <item>
      <title>Stadtfest am Wochenende</title>
      <description>Mit Musik und Markt.</description>
      <link>https://example.org/2</link>
      <pubDate>Mon, 19 Oct 2026 08:00:00 +0200</pubDate>
    </item>
  </channel>
</rss>
"""


class FakeResponse:
    """Stands in for a requests response in tests."""

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


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


def test_load_feed_list_returns_feeds(tmp_path):
    path = tmp_path / "feeds.yaml"
    path.write_text(
        "feeds:\n"
        "  feed_a: https://example.org/a.xml\n"
        "  feed_b: https://example.org/b.xml\n",
        encoding="utf-8",
    )

    feeds = load_feed_list(path)

    assert feeds == {
        "feed_a": "https://example.org/a.xml",
        "feed_b": "https://example.org/b.xml",
        }


def test_fetch_feed_returns_entries(monkeypatch):
    def fake_get(url, timeout):
        return FakeResponse(SAMPLE_FEED.encode("utf-8"))

    monkeypatch.setattr("fetch.requests.get", fake_get)

    result = fetch_feed("https://example.org/feed.xml")

    assert result is not None
    assert len(result.entries) == 2  
    assert result.entries[0].title == "Bäckerei öffnet neue Filiale"    


def test_fetch_feed_returns_none_on_error(monkeypatch):
    def fake_get(url, timeout):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("fetch.requests.get", fake_get)

    assert fetch_feed("https://example.org/feed.xml") is None 


def write_test_feeds(path):
    """Write a feed list with two invented feeds."""
    path.write_text(
        "feeds:\n"
        "  feed_a: https://example.org/a.xml\n"
        "  feed_b: https://example.org/b.xml\n",
        encoding="utf-8",
    )


def test_fetch_all_feeds_work(tmp_path, monkeypatch):
    def fake_get(url, timeout):
        return FakeResponse(SAMPLE_FEED.encode("utf-8"))

    monkeypatch.setattr("fetch.requests.get", fake_get)
    feeds_path = tmp_path / "feeds.yaml"
    output_path = tmp_path / "raw.json"
    write_test_feeds(feeds_path)

    status, path = fetch(feeds_path, output_path, "test")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))

    assert status == "ok"
    assert len(data["items"]) == 4 
    assert data["items"][-1]["id"] ==  "m004"   
    assert data["items"][2]["source"] == "feed_b" 


def test_fetch_one_feed_fails(tmp_path, monkeypatch):
    def fake_get(url, timeout):
        if "b.xml" in url:
            raise requests.ConnectionError("feed_b down")
        return FakeResponse(SAMPLE_FEED.encode("utf-8"))

    monkeypatch.setattr("fetch.requests.get", fake_get)
    feeds_path = tmp_path / "feeds.yaml"
    output_path = tmp_path / "raw.json"
    write_test_feeds(feeds_path)

    status, path = fetch(feeds_path, output_path, "test")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))

    assert status == "ok"  
    assert len(data["items"]) == 2 


def test_fetch_all_feeds_fail(tmp_path, monkeypatch):
    def fake_get(url, timeout):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("fetch.requests.get", fake_get)
    feeds_path = tmp_path / "feeds.yaml"
    output_path = tmp_path / "raw.json"
    write_test_feeds(feeds_path)

    status, path = fetch(feeds_path, output_path, "test")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    
    assert status == "abort"    
    assert data["items"] == []     
