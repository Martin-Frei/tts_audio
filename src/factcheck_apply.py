"""Stage factcheck_apply: carry out the verdicts of factcheck, nothing else.

Reads the _factcheck.json, or the _factcheck_reviewed.json if a person has
reviewed it, and writes the _factcheck_apply.json. factcheck_apply never
judges: it removes every item with an unsupported sentence and the
transitions left without content. No LLM, fully testable.

Workflow (factcheck_apply):
    1. Receive input_path, output_path and run_id from run.py.
    2. If a reviewed file lies next to the input, use it; otherwise the
       factcheck file. Its status must be "ok"; an unreviewed stop never
       passes this stage.
    3. dropped_items: every item with at least one sentence judged
        "nicht_belegt" or "widerspricht" (DROP_VERDICTS).
    4. remove_items: all lines of these items, source line and sentences.
    5. remove_orphan_transitions: a transition stays only if the next line
       belongs to an item. Order matters: items first, then transitions.
    6. Sentence ids are kept; gaps show what was removed.
    7. Write the file with save_apply, return (status, output_path).

Functions:
    reviewed_path(input_path)                   path of the reviewed file
    dropped_items(verdicts, sentences)          ids of items to remove
    remove_items(sentences, dropped)            lines without the dropped items
    remove_orphan_transitions(sentences)        lines without empty transitions
    save_apply(...)                             write the file with metadata
    factcheck_apply(input_path, output_path, run_id)  run the stage, return (status, path)

Dependencies:
    classify (own module, load_json); standard library: json, datetime.

Start and test:
    python run.py --profile news_classify --from factcheck_apply --run <run_id>
    python -m pytest src\\factcheck_apply.py tests\\test_factcheck_apply.py -v
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from classify import load_json


DROP_VERDICTS = {"nicht_belegt", "widerspricht"}


def reviewed_path(input_path: Path) -> Path:
    """Return the path of the reviewed factcheck file next to the input.

    >>> reviewed_path(Path("news_2026-10-28_1429_factcheck.json")).name
    'news_2026-10-28_1429_factcheck_reviewed.json'
    """
    return input_path.with_stem(input_path.stem + "_reviewed")


def dropped_items(verdicts: list[dict], sentences: list[dict]) -> list[str]:
    """Return the ids of items with at least one unsupported sentence, in order of appearance."""
    by_id = {sentence["id"]: sentence for sentence in sentences}
    dropped = []
    for verdict in verdicts:
        if verdict["verdict"] in DROP_VERDICTS:
            item = by_id[verdict["id"]]["item"]
            if item not in dropped:
                dropped.append(item)
    return dropped


def remove_items(sentences: list[dict], dropped: list[str]) -> list[dict]:
    """Remove every line of a dropped item: its source line and all its content sentences."""
    return [sentence for sentence in sentences if sentence["item"] not in dropped]


def remove_orphan_transitions(sentences: list[dict]) -> list[dict]:
    """Keep a transition only if the next line belongs to an item.

    >>> lines = [{"id": "s040", "kind": "transition", "item": None},
    ...          {"id": "s043", "kind": "ai_note", "item": None}]
    >>> [line["id"] for line in remove_orphan_transitions(lines)]
    ['s043']
    """
    kept = []
    for index, sentence in enumerate(sentences):
        if sentence["kind"] == "transition":
            following = sentences[index + 1] if index + 1 < len(sentences) else None
            if following is None or following["item"] is None:
                continue
        kept.append(sentence)
    return kept


def save_apply(path: Path, run_id: str, status: str, reason: str | None, used_file: str,
               removed: list[dict], sentences: list[dict], items: list[dict]) -> None:
    """Write the remaining sentences, the removed items with reasons, and which verdict file was used."""
    data = {
        "run_id": run_id,
        "stage": "factcheck_apply",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "used_file": used_file,
        "removed": removed,
        "sentences": sentences,
        "items": items,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def factcheck_apply(input_path: Path, output_path: Path, run_id: str) -> tuple[str, Path]:
    """Remove items with unsupported sentences and empty transitions; use the reviewed file if present."""
    # 1. a reviewed file wins; an unreviewed stop never passes
    source = reviewed_path(input_path)
    if not source.exists():
        source = input_path
    try:
        data = load_json(source)
        verdicts, sentences, items = data["verdicts"], data["sentences"], data["items"]
    except (OSError, ValueError, KeyError) as error:
        save_apply(output_path, run_id, "abort", f"input not readable: {error}", source.name, [], [], [])
        return "abort", output_path
    if data["status"] != "ok":
        reason = f"verdicts not released: {source.name} has status {data['status']}"
        save_apply(output_path, run_id, "abort", reason, source.name, [], [], items)
        return "abort", output_path

    # 2. items first, transitions second
    dropped = dropped_items(verdicts, sentences)
    remaining = remove_orphan_transitions(remove_items(sentences, dropped))
    if not any(sentence["kind"] == "content" for sentence in remaining):
        save_apply(output_path, run_id, "abort", "no content left", source.name, [], remaining, items)
        return "abort", output_path

    # 3. keep the reason for every removed item in the file
    by_id = {sentence["id"]: sentence for sentence in sentences}
    removed = [{"item": item,
                "reasons": [verdict["reason"] for verdict in verdicts
                            if verdict["verdict"] in DROP_VERDICTS and by_id[verdict["id"]]["item"] == item]}
               for item in dropped]
    save_apply(output_path, run_id, "ok", None, source.name, removed, remaining, items)
    return "ok", output_path
