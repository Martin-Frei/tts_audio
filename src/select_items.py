# src/select_items.py


"""Stage select_items: keep the newest usable items for the briefing.

Reads the _normalize.json and writes the _select_items.json.
select_items only decides which items are spoken and how many. It never
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
    3. Drop items that are no news with is_usable(): a question in the
       title without a teaser. This happens before counting, so the next
       item moves up and all places are filled.
    4. Sort with pick_newest(): newest published first, items without a
       date last, then keep the first max_items.
       ISO 8601 UTC times sort correctly as plain text.
    5. Write the file with save_stage(), status "ok".
    6. Return (status, output_path) to run.py.

Functions:
    is_usable(item)                              False for a question without teaser
    pick_newest(items, max_items)                usable items, newest first, undated last
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


def is_usable(item):
    """A question without a teaser is no news, and neither is noise. Everything else is kept.

    >>> is_usable({"title": "Brand in Beispielstadt", "teaser": None})
    True
    >>> is_usable({"title": "Wann kommt die Reform?", "teaser": None})
    False
    >>> is_usable({"title": "Wann kommt die Reform?", "teaser": "Die Koalition streitet."})
    True
    >>> is_usable({"title": "Lottozahlen vom Samstag", "teaser": "1, 7, 12", "category": "noise"})
    False
    """
    # classify only marks noise; dropping it is the job of this stage.
    if item.get("category") == "noise":
        return False
    # A statement tells something even without a teaser.
    # A question leaves the listener without an answer.
    title = item.get("title") or ""
    return bool(item.get("teaser")) or not title.endswith("?")

def pick_newest(items, max_items):
    """Return the newest usable items first; items without a date go last.

    >>> items = [{"id": "m001", "title": "Brand", "teaser": None, "published": "2026-10-19T08:00:00Z"},
    ...          {"id": "m002", "title": "Brücke", "teaser": "B", "published": None},
    ...          {"id": "m003", "title": "Streik", "teaser": "C", "published": "2026-10-19T09:00:00Z"},
    ...          {"id": "m004", "title": "Wann kommt die Reform?", "teaser": None, "published": "2026-10-19T10:00:00Z"}]
    >>> [item["id"] for item in pick_newest(items, 2)]
    ['m003', 'm001']
    >>> [item["id"] for item in pick_newest(items, 5)]
    ['m003', 'm001', 'm002']
    """
    # Drop first, count later: a dropped item frees its place for the next one.
    usable = [item for item in items if is_usable(item)]
    dated = [item for item in usable if item.get("published")]
    undated = [item for item in usable if not item.get("published")]
    # UTC times as ISO text ("2026-10-19T09:00:00Z") sort correctly as text.
    dated.sort(key=lambda item: item["published"], reverse=True)
    return (dated + undated)[:max_items]


def select_items(input_path, output_path, run_id, max_items=10):
    """Run the stage select_items and report (status, output_path) to run.py."""
    try:
        data = load_stage(input_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        reason = f"input not readable: {error}"
        save_stage(output_path, run_id, "select_items", [], "abort", reason)
        return "abort", output_path

    if not data["items"]:
        reason = "no items in input"
        save_stage(output_path, run_id, "select_items", [], "abort", reason)
        return "abort", output_path

    selected = pick_newest(data["items"], max_items)
    save_stage(output_path, run_id, "select_items", selected, "ok")
    logger.info("select_items: %d of %d items selected", len(selected), len(data["items"]))
    return "ok", output_path
