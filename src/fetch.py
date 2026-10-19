# src/fetch.py


"""Fetch stage: load the feed list and download RSS feeds.

Workflow:
    1. load_feed_list() reads config/feeds.yaml
    2. fetch_feed() downloads one feed per URL
    (parse_entry, to_utc, save_raw and fetch() follow)

Functions:
    load_feed_list(path) -> dict
    fetch_feed(url) -> FeedParserDict | None
    to_utc(parsed_time) -> str | None
    parse_entry(entry, source) -> dict
    save_raw(path, run_id, items, status, reason=None) -> None

Dependencies:
    pyyaml, feedparser

Test:
    python src/fetch.py
"""

import logging
import time
import json
from datetime import datetime, timezone

import feedparser
import yaml

logger = logging.getLogger(__name__)


def load_feed_list(path):
    """Read config/feeds.yaml and return the feeds as a dictionary (name -> URL)."""
    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data["feeds"]


def fetch_feed(url):
    """Download one RSS feed and return the parsed result, or None if it failed.

    A feed counts as failed when it delivers no entries, whatever the reason
    (unknown host, HTTP error, error page instead of XML).
    A feed with entries but a format warning (bozo) is still used.
    """
    result = feedparser.parse(url)

    if len(result.entries) == 0:
        reason = result.get("bozo_exception") or f"HTTP status {result.get('status')}"
        logger.warning("Feed failed: %s (%s)", url, reason)
        return None

    if result.bozo:
        logger.warning("Feed has format issues but is used: %s (%s)",
                       url, result.get("bozo_exception"))

    return result


def to_utc(parsed_time):
    """Convert a feedparser time to an ISO 8601 UTC string, or None if missing.

    >>> to_utc(time.strptime("2026-10-19 05:31:49", "%Y-%m-%d %H:%M:%S"))
    '2026-10-19T05:31:49Z'
    >>> to_utc(None) is None
    True
    """
    if parsed_time is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", parsed_time) 


def parse_entry(entry, source):
    """Extract the fields we keep from one feed entry and return them as a dictionary."""
    return {
        "source": source,                                      
        "title": entry.get("title"),                   
        "teaser": entry.get("summary"),                
        "link": entry.get("link"), 
        "published": to_utc(entry.get("published_parsed")),
    }


def save_raw(path, run_id, items, status, reason=None):
    """Write the raw stage file with metadata and all items."""
    data = {
        "run_id": run_id, 
        "stage": "fetch",  
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "items": items, 
    }
    with open(path, "w", encoding="utf-8") as file: 
        json.dump(data, file, ensure_ascii=False, indent=2)



if __name__ == "__main__":
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    test_dir = Path("data/runs/test")
    test_dir.mkdir(parents=True, exist_ok=True)

    feeds = load_feed_list("./config/feeds.yaml")
    result = fetch_feed(feeds["tagesschau"])
    if result is None:
        print("tagesschau failed")
    else:
        item = parse_entry(result.entries[0], source="tagesschau")
        save_raw(test_dir / "test_raw.json", "test", [item], "ok")
        print("written:", test_dir / "test_raw.json")
