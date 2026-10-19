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
import requests
import feedparser
import yaml

logger = logging.getLogger(__name__)


def load_feed_list(path):
    """Read config/feeds.yaml and return the feeds as a dictionary (name -> URL)."""
    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data["feeds"]


def fetch_feed(url, timeout=10):
    """Download one RSS feed and return the parsed result, or None if it failed.

    A feed counts as failed when the download fails or times out,
    or when it delivers no entries.
    A feed with entries but a format warning (bozo) is still used.
    """
    try:
        response = requests.get(url, timeout=timeout)    
        response.raise_for_status()
    except requests.RequestException as error:
        logger.warning("Feed failed: %s (%s)", url, error)
        return None 

    result = feedparser.parse(response.content)

    if len(result.entries) == 0:
        logger.warning("Feed failed: %s (no entries, %s)", url, result.get("bozo_exception"))
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


def fetch(feeds_path, output_path, run_id):
    """Run the fetch stage: download all feeds and write the raw file.

    Returns a tuple (status, output_path) for run.py.
    """
    feeds = load_feed_list(feeds_path)
    items = []
    number = 1

    for source, url in feeds.items():                
        result = fetch_feed(url)
        if result is None:
            continue                                     # ausgefallen: Feed überspringen

        for entry in result.entries:
            item = parse_entry(entry, source)
            item = {"id": f"m{number:03d}", **item}      # Kennung vorne einfügen
            items.append(item)   
            number += 1

    if len(items) == 0:                             
        status, reason = "abort", "no feed reachable"
    else:
        status, reason = "ok", None

    save_raw(output_path, run_id, items, status, reason)
    logger.info("fetch: %d items, status %s", len(items), status)
    return status, output_path                          


if __name__ == "__main__":
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    test_dir = Path("data/runs/test")
    test_dir.mkdir(parents=True, exist_ok=True)

    status, path = fetch("config/feeds.yaml", test_dir / "test_raw.json", "test")
    print(status, path)
    print("timeout:", fetch_feed(feeds_url_tagesschau := "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml", timeout=0.001))
    
