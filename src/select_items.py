# src/select_items.py


"""Stage select_items: keep the newest items for the briefing.

Reads the _normalize.json and writes the _select_items.json.
select_items only chooses how many and which items are spoken. It never
changes a text. The number comes from outside (max_items, later from
the profile in config/pipelines.yaml).

Position in the chain (Phase 1, decided 2026-10-26):
    fetch -> clean -> normalize -> residue_check -> select_items
    -> tts_piper -> postprocess
    Items are chosen when they are fully prepared. To be reviewed in
    Phase 2, when the fact check may remove sentences.

Workflow (select_items):
    1. Receive input_path, output_path, run_id and max_items from run.py.
    2. Load the input file with load_stage().
       If it cannot be read or has no items: status "abort" with a reason.
    3. Sort with pick_newest(): newest published first, items without a
       date last, then keep the first max_items.
       ISO 8601 UTC times sort correctly as plain text.
    4. Write the file with save_stage(), status "ok".
    5. Return (status, output_path) to run.py.

Functions:
    pick_newest(items, max_items)                newest first, undated last
    select_items(input_path, output_path, run_id, max_items=20)
                                                 run the stage, return (status, path)

Dependencies:
    stage_io (own module), standard library: json, logging.

Start and test:
    python -m pytest -v
"""


import json 
import logging 
from stage_io import load_stage, save_stage

logger = logging.getLogger(__name__)

def pick_newest(items, max_items):
    """Return the newest items first; items without a date go last.

    >>> items = [{"id": "m001", "published": "2026-10-19T08:00:00Z"},
    ...          {"id": "m002", "published": None},
    ...          {"id": "m003", "published": "2026-10-19T09:00:00Z"}]
    >>> [item["id"] for item in pick_newest(items, 2)]
    ['m003', 'm001']
    >>> [item["id"] for item in pick_newest(items, 5)]
    ['m003', 'm001', 'm002']
    """
    dated = [item for item in items if item.get("published")]           # Filter alle item die published Wert haben
    undated = [item for item in items if not item.get("published")]     # Filter alle item ohne published Wert
    dated.sort(key=lambda item: item["published"], reverse=True)        # Sortiert Item nach absteigendem Datum Uhrzeit
    return (dated + undated)[:max_items]                                # Gibt alle Artikel zurück, mit Datum zuerst, ohne ans Ende


def select_items(input_path, output_path, run_id, max_items=20):
    """Run the stage select_items and report (status, output_path) to run.py."""
    try:
        data = load_stage(input_path)                                           # Lädt die Eingabedatei der vorherigen Stufe
    except (FileNotFoundError, json.JSONDecodeError) as error:
        reason = f"input not readable: {error}"                                 # Erstellt eine Fehlermeldung (Lesefehler, JASON)
        save_stage(output_path, run_id, "select_items", [], "abort", reason)    # Speichert Status mit Abbruchgrund
        return "abort", output_path                                             # Gibt Status abort und Pfad zurück 

    if not data["items"]:
        reason = "no items in input"                                            # Erstellt eine Fehlermeldung (keine Artikel)
        save_stage(output_path, run_id, "select_items", [], "abort", reason)    # Speichert Status mit Abbruchgrund 
        return "abort", output_path                                             # Gibt Status und Ausgabepfad zurück

    selected = pick_newest(data["items"], max_items)                                        # Wählt die neuesten Artikel gemäß max_items aus
    save_stage(output_path, run_id, "select_items", selected, "ok")                         # Speichert die ausgewählten Artikel mit Status "ok"
    logger.info("select_items: %d of %d items selected", len(selected), len(data["items"]))
    return "ok", output_path                                                                # Gibt Status und Ausgabepfad zurück
