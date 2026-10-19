"""Fetch stage: load the feed list and download RSS feeds.

Workflow:
    1. load_feed_list() reads config/feeds.yaml
    2. fetch_feed() downloads one feed per URL
    (parse_entry, to_utc, save_raw and fetch() follow)

Functions:
    load_feed_list(path) -> dict
    fetch_feed(url) -> FeedParserDict | None

Dependencies:
    pyyaml, feedparser

Test:
    python src/fetch.py
"""

import logging

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    feeds = load_feed_list("./config/feeds.yaml")
    for name, url in feeds.items():
        result = fetch_feed(url)
        count = len(result.entries) if result else 0
        print(f"{name}: {count} entries")

    print("Test with unknown host:", fetch_feed("https://www.gibtesnicht-xyz.de/feed"))
