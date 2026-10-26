# src/clean.py


"""Stage clean: tidy title and teaser of every item in the raw file.

Reads the _raw.json written by fetch and writes the _clean.json.
clean only changes text. It never removes an item, never judges
content and does nothing that is only needed for speech (that is
the job of normalize).

Workflow (clean):
    1. Receive input_path, output_path and run_id from run.py.
    2. Load the raw file with load_raw().
       If it cannot be read or has no items: status "abort" with a reason.
    3. For each item: clean title and teaser with clean_item(),
       which calls clean_text() for each field.
       All other fields stay untouched.
    4. clean_text() returns None for None. Otherwise it runs the rules
       in a fixed order: first remove characters, last tidy up whitespace.
    5. Write the clean file with save_clean() and log the item count.
    6. Return (status, output_path) to run.py.

Functions:
    load_raw(path)                  read the raw file (via stage_io.load_stage)
    remove_html(text)               remove HTML tags, decode entities like &amp;
    unify_quotes(text)              replace typographic double quotes with "
    unify_hyphens(text)             replace special hyphens with a normal -
    remove_repeated_symbols(text)   remove runs of 2+ identical symbols like +++
    tidy_whitespace(text)           collapse inner spaces, strip both ends
    clean_text(text)                run all rules in order, None stays None
    clean_item(item)                clean title and teaser of one item
    save_clean(path, run_id, items, status, reason=None)
                                    write the clean file (via stage_io.save_stage)
    clean(input_path, output_path, run_id)
                                    run the stage, return (status, path)

Dependencies:
    stage_io (own module), standard library: html, json, logging, re, sys, pathlib.

Start and test:
    python -m pytest -v
    python src/clean.py <raw.json> <clean.json> <run_id>
"""

import html
import json
import logging
import re
import sys
from pathlib import Path

from stage_io import load_stage, save_stage


logger = logging.getLogger(__name__)

# Typographic double quotes that become a plain "
# Single quotes are not touched on purpose: ’ is also the apostrophe ("geht’s").
DOUBLE_QUOTES = "„“”»«"

# Special hyphens that become a plain -
# U+2010 hyphen, U+2011 non-breaking hyphen (as in "KI‑Strategie")
# The en dash – is not touched: it is a dash between clauses, not a hyphen.
SPECIAL_HYPHENS = "\u2010\u2011"

# Patterns are compiled once when the module loads, not on every call.
# The name also says what the pattern is for.

# ( ... ) captures ONE symbol, \1+ demands the SAME symbol at least once more.
# So "+++" and "==" are removed, but "=>" stays (two different symbols).
# . ! ? are not in the list on purpose: "..." and "!!!" are still open.
REPEATED_SYMBOLS = re.compile(r"([+*#~_|=])\1+")

# "<", then any characters except ">", then ">"  ->  one HTML tag
HTML_TAG = re.compile(r"<[^>]+>")

# \s also matches tabs, line breaks and the non-breaking space.
WHITESPACE = re.compile(r"\s+")


def load_raw(path):
    """Read the raw file and return its content as a dictionary."""

    return load_stage(path)                 # Lädt die Rohdaten-Datei über load_stage und gibt sie zurück


def remove_html(text):
    """Replace HTML tags with a space and decode entities.

    Tags become a space, so two words never stick together.
    The extra spaces are removed later by tidy_whitespace().

    >>> remove_html("<b>Eilmeldung</b> Brand &amp; Rauch")
    ' Eilmeldung  Brand & Rauch'
    """
    
    text = HTML_TAG.sub(" ", text)  # Ersetzt HTML-Tags durch Leerzeichen, um Wortverschmelzungen zu verhindern
    return html.unescape(text)      # Dekodiert HTML-Entitäten (z.B. &amp; zu &) und gibt den Text zurück


def unify_quotes(text):
    """Replace typographic double quotes with a plain double quote.

    >>> unify_quotes("„Wir sind bereit“, sagte er.")
    '"Wir sind bereit", sagte er.'
    """
    
    for quote in DOUBLE_QUOTES:             # Iteriert durch alle typografischen Anführungszeichen
        text = text.replace(quote, '"')     # Ersetzt jedes typografische Anführungszeichen durch ein normales "
    return text                             # Gibt den angepassten Text zurück


def unify_hyphens(text):
    """Replace special hyphens with a plain hyphen.

    >>> unify_hyphens("KI\u2011Strategie")
    'KI-Strategie'
    """
   
    for hyphen in SPECIAL_HYPHENS:          # Iteriert durch spezielle Bindestriche
        text = text.replace(hyphen, "-")    # Ersetzt spezielle Bindestriche durch einen normalen Bindestrich
    return text                             # Gibt den bereinigten Text zurück


def remove_repeated_symbols(text):
    """Remove runs of two or more identical symbols, such as +++.

    A single symbol stays.

    >>> remove_repeated_symbols("+++ Liveblog +++")
    ' Liveblog '
    >>> remove_repeated_symbols("1 + 1")
    '1 + 1'
    """
 
    return REPEATED_SYMBOLS.sub("", text)               # Entfernt mehrfach wiederholte Symbole (z.B. +++) per Regex


def tidy_whitespace(text):
    """Collapse all whitespace to one space and strip both ends.

    >>> tidy_whitespace("  Brand   in Beispielstadt ")
    'Brand in Beispielstadt'
    """
    return WHITESPACE.sub(" ", text).strip()            # Fasst mehrfache Leerzeichen zu einem zusammen und entfernt Randabstände


def clean_text(text):
    """Run all rules in a fixed order. None stays None.

    Order matters: first remove characters, last tidy up whitespace.
    Otherwise the spaces next to removed characters would remain.

    >>> clean_text("+++ Brand in Beispielstadt +++ ")
    'Brand in Beispielstadt'
    >>> clean_text(None) is None
    True
    """
   
    if text is None:
        return None                         # Gibt None direkt zurück, falls kein Text vorhanden ist.
    text = remove_html(text)                # Entfernt HTML-Tags und dekodiert Entitäten
    text = unify_quotes(text)               # Vereinheitlicht Anführungszeichen
    text = unify_hyphens(text)              # Vereinheitlicht spezielle Bindestriche
    text = remove_repeated_symbols(text)    # Entfernt wiederholte Symbole
    return tidy_whitespace(text)            # Bereinigt Leerzeichen als letzten Schritt und gibt den Text zurück


def clean_item(item):
    """Return a copy of one item with title and teaser cleaned.

    All other fields are copied unchanged.

    >>> clean_item({"id": "m001", "title": "+++ A +++", "teaser": None})
    {'id': 'm001', 'title': 'A', 'teaser': None}
    """
    
    cleaned = dict(item)                                # Erstellt eine flache Kopie des Datensatzes, um das Original zu schützen
    cleaned["title"] = clean_text(item.get("title"))    # Bereinigt den Titel des Items
    cleaned["teaser"] = clean_text(item.get("teaser"))  # Bereinigt den Teaser des Items
    return cleaned                                      # Gibt das bereinigte Item zurück


def save_clean(path, run_id, items, status, reason=None):
    """Write the clean file with metadata in front of the items."""
    save_stage(path, run_id, "clean", items, status, reason)    # Übergibt das Speichern an stage_io.save_stage


def clean(input_path, output_path, run_id):
    """Run the stage clean and return (status, output_path) to run.py."""
    input_path = Path(input_path)                               # Konvertiert den Eingangspfad in ein Path-Objekt
    output_path = Path(output_path)                             # Konvertiert den Ausgangspfad in ein Path-Objekt

    try:
        raw = load_raw(input_path)                              # Versucht, die Rohdaten-Datei zu laden
    except (OSError, json.JSONDecodeError) as error:
        reason = f"raw file not readable: {error}"              # Erstellt eine Fehlerbeschreibung bei Lesefehlern
        logger.error(reason)                                    # Loggt den Fehler
        save_clean(output_path, run_id, [], "abort", reason)    # Speichert den Abbruchstatus in der Zieldatei
        return "abort", output_path                             # raw file not readable -> abort

    items = raw.get("items") or []                              # Extrahiert die Artikelliste oder nutzt eine leere Liste als Fallback
    if not items:
        reason = "raw file has no items"                        # Grund für Abbruch bei leerer Artikelliste
        logger.error(reason)                                    # Loggt den Fehler
        save_clean(output_path, run_id, [], "abort", reason)    # Speichert den Abbruchstatus
        return "abort", output_path                             # no items -> abort

    cleaned = [clean_item(item) for item in items]                          # Bereinigt jedes Item in der Liste per List Comprehension
    save_clean(output_path, run_id, cleaned, "ok")                          # Speichert die erfolgreich bereinigten Daten mit Status "ok"
    logger.info("clean: %d items written to %s", len(cleaned), output_path) # Loggt die Anzahl geschriebener Einträge
    return "ok", output_path                                                # Gibt Status und Ausgabepfad an den Runner zurück


if __name__ == "__main__":
    # Manual test run, not an automatic test.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) != 4:
        print("Usage: python src/clean.py <raw.json> <clean.json> <run_id>")
        sys.exit(1)
    status, path = clean(sys.argv[1], sys.argv[2], sys.argv[3])
    print(status, path)
