# src/fetch.py


"""Fetch stage: download all RSS feeds and write the raw file.

Workflow (fetch):
    1. Receive feeds_path, output_path and run_id from run.py.
    2. Load the feed list (name -> URL) with load_feed_list().
    3. For each feed: download it with fetch_feed().
       If it returns None (unreachable, timeout, no entries), skip it
       and continue with the next feed.
    4. For each entry of a working feed: extract the fields with
       parse_entry() (which calls to_utc() for the date), put a running
       id in front (m001, m002, ... across all feeds) and append the
       item to the list.
    5. Set the status: "abort" with a reason if no item was collected,
       otherwise "ok".
    6. Write the raw file with save_raw() and log the item count.
    7. Return (status, output_path) to run.py.

Functions:
    load_feed_list(path) -> dict
    fetch_feed(url, timeout=10) -> FeedParserDict | None
    to_utc(parsed_time) -> str | None
    parse_entry(entry, source) -> dict
    save_raw(path, run_id, items, status, reason=None) -> None  (via stage_io.save_stage)
    fetch(feeds_path, output_path, run_id) -> tuple (status, output_path)

Dependencies:
    feedparser, pyyaml, requests, stage_io (own module)

Test:
    python -m pytest -v    # all tests and doctests
"""

import logging
import time

import requests
import feedparser
import yaml

from stage_io import save_stage

logger = logging.getLogger(__name__)


def load_feed_list(path):
    """Read config/feeds.yaml and return the feeds as a dictionary (name -> URL)."""
    with open(path, encoding="utf-8") as file:      # Öffnet die Konfigurationsdatei im Lesemodus mit UTF-8-Codierung
        data = yaml.safe_load(file)                 # Lädt die YAML-Inhalte sicher als Python-Struktur
    return data["feeds"]                            # Gibt das Dictionary mit den Feeds (Name -> URL) zurück


def fetch_feed(url, timeout=10):
    """Download one RSS feed and return the parsed result, or None if it failed.

    A feed counts as failed when the download fails or times out,
    or when it delivers no entries.
    A feed with entries but a format warning (bozo) is still used.
    """
    try: 
        response = requests.get(url, timeout=timeout)                       # Führt einen HTTP-GET-Request für die Feed-URL mit Zeitlimit durch 
        response.raise_for_status()                                         # Löst bei HTTP-Fehlern (z.B. 404 oder 500) eine Exception aus
    except requests.RequestException as error:
        logger.warning("Feed failed: %s (%s)", url, error)                  # Loggt eine Warnung, falls der Abruf fehlschlägt
        return None                                                         # Gibt None zurück, um den fehlgeschlagenen Feed zu überspringen

    result = feedparser.parse(response.content)                             # Parst den heruntergeladenen Feed-Inhalt mit feedparser

    if len(result.entries) == 0:                                            # Einträge ist gleich 0
        logger.warning("Feed failed: %s (no entries, %s)", url, result.get("bozo_exception"))  # Loggt eine Warnung, wenn keine Einträge vorhanden sind
        return None                                                         # Gibt None zurück

    if result.bozo:
        logger.warning("Feed has format issues but is used: %s (%s)",       # Loggt Formatwarnungen (bozo), nutzt den Feed aber dennoch
                       url, result.get("bozo_exception"))

    return result                                                           # Gibt das geparste Ergebnis zurück


def to_utc(parsed_time):
    """Convert a feedparser time to an ISO 8601 UTC string, or None if missing.

    >>> to_utc(time.strptime("2026-10-19 05:31:49", "%Y-%m-%d %H:%M:%S"))
    '2026-10-19T05:31:49Z'
    >>> to_utc(None) is None
    True
    """
    if parsed_time is None:                                         # Prüft, ob keine Zeitinformation übergeben wurde
        return None                                                 # Gibt direkt None zurück
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", parsed_time)         # Konvertiert die Zeitstruktur in einen ISO-8601-UTC-String


def parse_entry(entry, source):
    """Extract the fields we keep from one feed entry and return them as a dictionary."""
    return {
        "source": source,                                       # Speichert den Namen der Feed-Quelle              
        "title": entry.get("title"),                            # Extrahiert den Titel des Artikels
        "teaser": entry.get("summary"),                         # Extrahiert den Teaser oder die Zusammenfassung
        "link": entry.get("link"),                              # Extrahiert den Weblink zum Originalbeitrag
        "published": to_utc(entry.get("published_parsed")),     # Konvertiert und speichert das Veröffentlichungsdatum in UTC
    }


def save_raw(path, run_id, items, status, reason=None):
    """Write the raw stage file with metadata and all items."""
    # The frame is the same for every stage: written in stage_io.save_stage().
    save_stage(path, run_id, "fetch", items, status, reason)    # Übergibt das Schreiben der Rohdaten an stage_io.save_stage


def fetch(feeds_path, output_path, run_id):
    """Run the fetch stage: download all feeds and write the raw file.

    Returns a tuple (status, output_path) for run.py.
    """
    feeds = load_feed_list(feeds_path)                   # Lädt die Feed-Liste (Name zu URL) aus der Konfigurationsdatei
    items = []                                           # Initialisiert eine leere Liste für alle gesammelten Einträge
    number = 1                                           # Initialisiert den laufenden Zähler für die eindeutigen Item-IDs

    for source, url in feeds.items():                    # Durchläuft alle definierten Feeds nacheinander
        result = fetch_feed(url)                         # Lädt den aktuellen Feed herunter und parst ihn
        if result is None:
            continue                                     # ausgefallen: Feed überspringen

        for entry in result.entries:                     # Durchläuft alle einzelnen Beiträge des Feeds
            item = parse_entry(entry, source)            # Extrahiert die relevanten Datenfelder des Eintrags
            item = {"id": f"m{number:03d}", **item}      # Kennung vorne einfügen
            items.append(item)                           # Fügt das bearbeitete Item zur Gesamtliste hinzu
            number += 1                                  # Inkrementiert den ID-Zähler für das nächste Item

    if len(items) == 0:                                  # Prüft, ob nach dem Durchlauf aller Feeds keine Items gesammelt wurden
        status, reason = "abort", "no feed reachable"    # Setzt den Status auf "abort" und gibt einen Grund an
    else:
        status, reason = "ok", None                      # Setzt den Status auf "ok", wenn Daten erfolgreich gesammelt wurden

    save_raw(output_path, run_id, items, status, reason) # Speichert die Rohdaten-Datei im Dateisystem
    logger.info("fetch: %d items, status %s", len(items), status)  # Loggt die Anzahl gesammelter Artikel und den Endstatus
    return status, output_path                          # Gibt Status und den Ausgabepfad an den Runner zurück                         


if __name__ == "__main__":
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    test_dir = Path("data/runs/test")
    test_dir.mkdir(parents=True, exist_ok=True)

    status, path = fetch("config/feeds.yaml", test_dir / "test_raw.json", "test")
    print(status, path)
