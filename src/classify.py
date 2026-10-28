


from pathlib import Path
import json


def load_json(path: Path) -> dict:
    """Read a JSON file and return it as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    """Read a text file, e.g. the prompt template."""
    return path.read_text(encoding="utf-8")


def split_batches(items: list[dict], batch_size: int) -> list[list[dict]]:
    """Split items into consecutive batches; the last batch may be smaller.
    
    >>> split_batches([1, 2, 3, 4, 5], 2)
    [[1, 2], [3, 4], [5]]
    >>> split_batches([], 10)
    []
    >>> batches = split_batches(list(range(111)), 10)
    >>> len(batches), len(batches[-1])
    (12, 1)
    >>> split_batches([1, 2], 0)
    Traceback (most recent call last):
    ValueError: batch_size must be at least 1, got 0
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")
    batches = []
    for start in range(0, len(items), batch_size):
        batches.append(items[start:start + batch_size])
    return batches


def evidence_found(word: str, item: dict) -> bool:
    """Check case-insensitively whether word appears in title or teaser.

    >>> item = {"title": "Bundestag unterstützt Olympia-Bewerbung", "teaser": None}
    >>> evidence_found("olympia-bewerbung", item)
    True
    >>> evidence_found("Olympiabewerbung", item)
    False
    >>> evidence_found("Abgeordnete", {"title": None, "teaser": "Die Abgeordneten stimmten zu."})
    True
    >>> evidence_found("STRASSE", {"title": "Straße nach Hochwasser gesperrt", "teaser": None})
    True
    >>> evidence_found("Hochwasser", {"title": None, "teaser": None})
    False
    """
    text = (item["title"] or "") + " " + (item["teaser"] or "")
    return word.casefold() in text.casefold()


def validate_batch(batch: list[dict], results: list[dict], category_ids: set[str]) -> list[dict]:
    """Check one LLM answer against its batch; return a list of errors, empty if all is fine."""
    errors = []
    sent = {item["id"]: item for item in batch}
    returned_ids = [result["id"] for result in results]

    for item_id in sent:
        count = returned_ids.count(item_id)
        if count == 0:
            errors.append({"id": item_id, "check": "missing_id"})
        elif count > 1:
            errors.append({"id": item_id, "check": "duplicate_id"})

    for result in results:
        item_id = result["id"]
        if item_id not in sent:
            errors.append({"id": item_id, "check": "unknown_id"})
            continue
        if result["category"] not in category_ids:
            errors.append({"id": item_id, "check": "unknown_category", "value": result["category"]})
        if not result["evidence"]:
            errors.append({"id": item_id, "check": "no_evidence"})
        for word in result["evidence"]:
            if not evidence_found(word, sent[item_id]):
                errors.append({"id": item_id, "check": "evidence_not_found", "value": word})

    return errors
