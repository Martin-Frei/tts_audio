"""Shared reading and writing of stage files.

Workflow:
    Every stage of the pipeline reads the file of the stage before and
    writes its own file. All stage files share the same frame:
    run_id, stage, created, status, reason, items.
    save_stage() writes this frame, load_stage() reads a stage file back.
    A stage only passes its own name and its items.

Functions:
    load_stage(path)
        Read a stage file and return it as a dictionary.
    save_stage(path, run_id, stage, items, status, reason=None)
        Write a stage file with metadata, created in UTC.

Dependencies:
    Standard library only (json, datetime, pathlib).

Test:
    python -m pytest tests/test_stage_io.py -v
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def load_stage(path):
    """Read a stage file and return its content as a dictionary.

    Raises FileNotFoundError if the file is missing and
    json.JSONDecodeError if it is not valid JSON. The calling stage
    decides what happens then, usually status "abort".
    """
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def save_stage(path, run_id, stage, items, status, reason=None):
    """Write a stage file: metadata first, then the items.

    created is set here, in UTC. The parent folder is created if needed,
    because Git does not keep empty folders.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "run_id": run_id,
        "stage": stage,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "items": items,
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
