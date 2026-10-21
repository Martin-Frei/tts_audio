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
    load_raw(path)                  read the raw file, return a dictionary
    remove_html(text)               remove HTML tags, decode entities like &amp;
    unify_quotes(text)              replace typographic double quotes with "
    unify_hyphens(text)             replace special hyphens with a normal -
    remove_repeated_symbols(text)   remove runs of 2+ identical symbols like +++
    tidy_whitespace(text)           collapse inner spaces, strip both ends
    clean_text(text)                run all rules in order, None stays None
    clean_item(item)                clean title and teaser of one item
    save_clean(path, run_id, items, status, reason=None)
                                    write the clean file with metadata
    clean(input_path, output_path, run_id)
                                    run the stage, return (status, path)

Dependencies:
    Standard library only: html, json, logging, re, sys, datetime, pathlib.

Start and test:
    python -m pytest -v
    python src/clean.py <raw.json> <clean.json> <run_id>
"""

import html
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Only get the logger here. logging.basicConfig belongs to whoever starts
# the program: the __main__ block below, later run.py.
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
    # No try/except here: clean() catches the error, because only
    # clean() decides about the status of the stage.
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def remove_html(text):
    """Replace HTML tags with a space and decode entities.

    Tags become a space, so two words never stick together.
    The extra spaces are removed later by tidy_whitespace().

    >>> remove_html("<b>Eilmeldung</b> Brand &amp; Rauch")
    ' Eilmeldung  Brand & Rauch'
    """
    # Tags first, entities second. The other way round, "&lt;b&gt;"
    # would turn into "<b>" and be removed, although it was plain text.
    text = HTML_TAG.sub(" ", text)
    return html.unescape(text)


def unify_quotes(text):
    """Replace typographic double quotes with a plain double quote.

    >>> unify_quotes("„Wir sind bereit“, sagte er.")
    '"Wir sind bereit", sagte er.'
    """
    # Unify, not remove: quotes show that something is a quotation.
    # Whether they are removed for speech is decided by normalize.
    for quote in DOUBLE_QUOTES:
        text = text.replace(quote, '"')
    return text


def unify_hyphens(text):
    """Replace special hyphens with a plain hyphen.

    >>> unify_hyphens("KI\u2011Strategie")
    'KI-Strategie'
    """
    # Replace, not delete: deleting would give "KIStrategie".
    for hyphen in SPECIAL_HYPHENS:
        text = text.replace(hyphen, "-")
    return text


def remove_repeated_symbols(text):
    """Remove runs of two or more identical symbols, such as +++.

    A single symbol stays.

    >>> remove_repeated_symbols("+++ Liveblog +++")
    ' Liveblog '
    >>> remove_repeated_symbols("1 + 1")
    '1 + 1'
    """
    # The spaces next to the removed symbols stay. tidy_whitespace() runs last.
    return REPEATED_SYMBOLS.sub("", text)


def tidy_whitespace(text):
    """Collapse all whitespace to one space and strip both ends.

    >>> tidy_whitespace("  Brand   in Beispielstadt ")
    'Brand in Beispielstadt'
    """
    return WHITESPACE.sub(" ", text).strip()


def clean_text(text):
    """Run all rules in a fixed order. None stays None.

    Order matters: first remove characters, last tidy up whitespace.
    Otherwise the spaces next to removed characters would remain.

    >>> clean_text("+++ Brand in Beispielstadt +++ ")
    'Brand in Beispielstadt'
    >>> clean_text(None) is None
    True
    """
    # A missing teaser stays missing. Without this check, re.sub()
    # would crash with a TypeError on the first item without teaser.
    if text is None:
        return None
    # Order matters: first remove characters, tidy up whitespace last.
    text = remove_html(text)
    text = unify_quotes(text)
    text = unify_hyphens(text)
    text = remove_repeated_symbols(text)
    return tidy_whitespace(text)


def clean_item(item):
    """Return a copy of one item with title and teaser cleaned.

    All other fields are copied unchanged.

    >>> clean_item({"id": "m001", "title": "+++ A +++", "teaser": None})
    {'id': 'm001', 'title': 'A', 'teaser': None}
    """
    # Make a copy, so the original item stays unchanged.
    # A flat copy is enough, because the values are only texts or None.
    cleaned = dict(item)
    # .get() instead of item["title"]: a missing field gives None
    # instead of a KeyError, and clean_text() handles None.
    cleaned["title"] = clean_text(item.get("title"))
    cleaned["teaser"] = clean_text(item.get("teaser"))
    return cleaned


def save_clean(path, run_id, items, status, reason=None):
    """Write the clean file with metadata in front of the items."""
    # stage and created are set here, not passed in:
    # created is the moment the FILE is written, not the run_id of the run.
    data = {
        "run_id": run_id,
        "stage": "clean",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "items": items,
    }
    # encoding="utf-8": how the characters are stored as bytes.
    # ensure_ascii=False: umlauts appear as plain text, not as \u00fc.
    # Python None becomes null in the file.
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def clean(input_path, output_path, run_id):
    """Run the stage clean and return (status, output_path) to run.py."""
    # run.py may pass a text or a Path. Path() makes both the same.
    input_path = Path(input_path)
    output_path = Path(output_path)

    try:
        raw = load_raw(input_path)
    except (OSError, json.JSONDecodeError) as error:
        # OSError: file missing or locked. JSONDecodeError: file is not valid JSON.
        reason = f"raw file not readable: {error}"
        logger.error(reason)
        # Write a file even on abort, so the abort leaves a trace with a reason.
        save_clean(output_path, run_id, [], "abort", reason)
        return "abort", output_path     # raw file not readable -> abort

    # "or []" also catches "items": null in the file.
    items = raw.get("items") or []
    if not items:
        # Should not happen after fetch "ok". Safety net for a manual start.
        reason = "raw file has no items"
        logger.error(reason)
        save_clean(output_path, run_id, [], "abort", reason)
        return "abort", output_path     # no items -> abort

    # One cleaned item per raw item: clean never removes an item.
    # The test checks that the count in equals the count out.
    cleaned = [clean_item(item) for item in items]
    save_clean(output_path, run_id, cleaned, "ok")
    logger.info("clean: %d items written to %s", len(cleaned), output_path)
    return "ok", output_path


if __name__ == "__main__":
    # Manual test run, not an automatic test.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) != 4:
        print("Usage: python src/clean.py <raw.json> <clean.json> <run_id>")
        sys.exit(1)
    status, path = clean(sys.argv[1], sys.argv[2], sys.argv[3])
    print(status, path)
