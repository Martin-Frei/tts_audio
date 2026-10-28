"""Stage classify: give every item exactly one category, with evidence words.

Reads the _clean.json and writes the _classify.json. classify only marks;
it never drops an item (that is select_items) and never changes a title
or teaser: the LLM returns only id, category and evidence, the code copies
each item unchanged and adds the label.

Workflow (classify):
    1. Receive paths and parameters from run.py (profile news_classify).
    2. Load items, categories (config/categories.json) and prompt template.
       Unreadable input or no items: status "abort" with a reason.
    3. Split the items into batches of batch_size. For each batch, with
       min_interval_s pause between batches (free tier: 15 requests/min):
       build the prompt (id, title, teaser; categories without transition),
       call Gemini with a response schema, parse the JSON.
    4. filter_evidence drops evidence words that are not in title or teaser
       (warning). validate_batch checks ids, category and that at least one
       evidence word is left (error).
    5. Errors are collected over all batches; LLM errors (503, 429 after
       retries, no text) too. Any error: status "abort" at the end.
    6. Write the file with save_classify, return (status, output_path).

Functions:
    load_json(path)                          JSON file as dictionary
    load_text(path)                          text file, e.g. the prompt
    split_batches(items, batch_size)         consecutive batches
    format_categories(categories)            numbered category list for the prompt
    format_items(batch)                      one line per item for the prompt
    build_prompt(template, categories, batch) prompt with both blocks inserted
    evidence_found(word, item)               word in title or teaser, case-insensitive
    filter_evidence(batch, results)          drop invalid evidence, return warnings
    validate_batch(batch, results, category_ids) errors of one answer
    parse_response(text)                     JSON text to list of dictionaries
    save_classify(...)                       write the file with metadata
    classify(...)                            run the stage, return (status, path)

Dependencies:
    llm (own module), pydantic; standard library: json, time, datetime.

Start and test:
    python run.py --profile news_classify
    python -m pytest src\\classify.py tests\\test_classify.py -v
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from llm import call_llm, make_client


class Classification(BaseModel):
    """Shape of one LLM answer entry; enforced by the API as response schema."""
    id: str
    category: str
    evidence: list[str]


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


def format_categories(categories: list[dict]) -> str:
    """Format categories as a numbered list with their exclusions; transitions are left out.

    >>> print(format_categories([{"id": "sports", "description": "Sport aller Art.", "not": ["Lotto (-> noise)"]}]))
    1. sports: Sport aller Art.
       Nicht: Lotto (-> noise)
    """
    lines = []
    for number, category in enumerate(categories, start=1):
        lines.append(f"{number}. {category['id']}: {category['description']}")
        for rule in category["not"]:
            lines.append(f"   Nicht: {rule}")
    return "\n".join(lines)


def format_items(batch: list[dict]) -> str:
    """Format a batch as one line per item: id, title, teaser.

    >>> print(format_items([{"id": "m002", "title": "Bayern gewinnt", "teaser": None}]))
    m002 | Titel: Bayern gewinnt | Teaser: -
    """
    lines = []
    for item in batch:
        title = item["title"] or "-"
        teaser = item["teaser"] or "-"
        lines.append(f"{item['id']} | Titel: {title} | Teaser: {teaser}")
    return "\n".join(lines)


def build_prompt(template: str, categories: list[dict], batch: list[dict]) -> str:
    """Insert categories and items into the prompt template."""
    prompt = template.replace("{{CATEGORIES}}", format_categories(categories))
    return prompt.replace("{{ITEMS}}", format_items(batch))


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


def filter_evidence(batch: list[dict], results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Drop evidence words not found in the source item; return cleaned results and warnings."""
    sent = {item["id"]: item for item in batch}
    cleaned = []
    warnings = []
    for result in results:
        item = sent.get(result["id"])
        if item is None:
            cleaned.append(result)  # unknown id is reported by validate_batch
            continue
        kept = []
        for word in result["evidence"]:
            if evidence_found(word, item):
                kept.append(word)
            else:
                warnings.append({"id": result["id"], "check": "evidence_dropped", "value": word})
        cleaned.append({**result, "evidence": kept})
    return cleaned, warnings


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

    return errors


def parse_response(text: str) -> list[dict]:
    """Turn the JSON text of an answer into a list of dictionaries.

    >>> parse_response('[{"id": "m002", "category": "sports", "evidence": ["gewinnt"]}]')
    [{'id': 'm002', 'category': 'sports', 'evidence': ['gewinnt']}]
    """
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("answer is not a list")
    return data


def save_classify(path: Path, run_id: str, status: str, reason: str | None,
                  items: list[dict], errors: list[dict], warnings: list[dict]) -> None:
    """Write the classify file with metadata, status, errors, warnings and classified items."""
    data = {
        "run_id": run_id,
        "stage": "classify",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "errors": errors,
        "warnings": warnings,
        "items": items,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def classify(clean_path: Path, categories_path: Path, prompt_path: Path, output_path: Path,
             run_id: str, model: str, batch_size: int, timeout_ms: int, attempts: int,
             temperature: float, min_interval_s: float) -> tuple[str, Path]:
    """Classify all items batch by batch, collect all errors, write the file, return status and path."""
    # 1. load inputs; unreadable input is a technical abort
    try:
        items = load_json(clean_path)["items"]
        categories = load_json(categories_path)["categories"]
        template = load_text(prompt_path)
    except (OSError, ValueError, KeyError) as error:
        save_classify(output_path, run_id, "abort", f"input not readable: {error}", [], [], [])
        return "abort", output_path
    if not items:
        save_classify(output_path, run_id, "abort", "no items", [], [], [])
        return "abort", output_path

    # 2. classify batch by batch; errors are collected, never stop the loop
    category_ids = {category["id"] for category in categories}
    try:
        client = make_client(timeout_ms, attempts)
    except KeyError as error:
        save_classify(output_path, run_id, "abort", f"missing api key: {error}", [], [], [])
        return "abort", output_path
    labels = []
    errors = []
    warnings = []
    for number, batch in enumerate(split_batches(items, batch_size), start=1):
        if number > 1:
            time.sleep(min_interval_s)
        try:
            prompt = build_prompt(template, categories, batch)
            results = parse_response(call_llm(client, model, prompt, temperature, list[Classification]))
        except Exception as error:
            errors.append({"batch": number, "check": "llm_error", "value": str(error)})
            continue
        results, dropped = filter_evidence(batch, results)
        warnings.extend(dropped)
        errors.extend(validate_batch(batch, results, category_ids))
        labels.extend(results)

    # 3. code copies each item unchanged and adds the label of the LLM
    by_id = {label["id"]: label for label in labels}
    classified = []
    for item in items:
        label = by_id.get(item["id"], {})
        classified.append({**item, "category": label.get("category"), "evidence": label.get("evidence", [])})

    # 4. abort after all batches if any error was collected
    status = "abort" if errors else "ok"
    reason = f"{len(errors)} errors" if errors else None
    save_classify(output_path, run_id, status, reason, classified, errors, warnings)
    return status, output_path
