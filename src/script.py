# src/script.py

"""Stage script: write a listenable briefing as a numbered sentence list.

(Full docstring follows when all functions are done.)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from classify import load_json, load_text, parse_response
from llm import call_llm, make_client



class ItemSentences(BaseModel):
    """Shape of one LLM answer entry: the sentences written for one item."""
    item: str
    sentences: list[str]


def group_by_category(items: list[dict], order: list[str]) -> list[tuple[str, list[dict]]]:
    """Group items by category in briefing order; categories without items are left out.

    >>> items = [{"id": "m1", "category": "sports"}, {"id": "m2", "category": "politics_state"},
    ...          {"id": "m3", "category": "sports"}]
    >>> [(category, [item["id"] for item in members]) for category, members in group_by_category(items, ["politics_state", "world", "sports"])]
    [('politics_state', ['m2']), ('sports', ['m1', 'm3'])]
    >>> group_by_category([{"id": "m4", "category": "noise"}], ["politics_state"])
    Traceback (most recent call last):
    ValueError: items without briefing category: ['m4']
    """
    missing = [item["id"] for item in items if item["category"] not in order]
    if missing:
        raise ValueError(f"items without briefing category: {missing}")
    groups = []
    for category in order:
        members = [item for item in items if item["category"] == category]
        if members:
            groups.append((category, members))
    return groups


def format_script_items(items: list[dict]) -> str:
    """Format items as one line each: id, source, title, teaser.

    >>> print(format_script_items([{"id": "m002", "source": "tagesschau", "title": "Bayern gewinnt", "teaser": None}]))
    m002 | Quelle: tagesschau | Titel: Bayern gewinnt | Teaser: -
    """
    lines = []
    for item in items:
        title = item["title"] or "-"
        teaser = item["teaser"] or "-"
        lines.append(f"{item['id']} | Quelle: {item['source']} | Titel: {title} | Teaser: {teaser}")
    return "\n".join(lines)


def validate_script(items: list[dict], results: list[dict]) -> list[dict]:
    """Check the LLM answer against the selected items; return errors, empty if all is fine."""
    errors = []
    selected = [item["id"] for item in items]
    returned = [result["item"] for result in results]

    for item_id in selected:
        count = returned.count(item_id)
        if count == 0:
            errors.append({"item": item_id, "check": "missing_item"})
        elif count > 1:
            errors.append({"item": item_id, "check": "duplicate_item"})

    for result in results:
        if result["item"] not in selected:
            errors.append({"item": result["item"], "check": "unknown_item"})
            continue
        if not result["sentences"]:
            errors.append({"item": result["item"], "check": "no_sentences"})
        for number, sentence in enumerate(result["sentences"], start=1):
            if not sentence.strip():
                errors.append({"item": result["item"], "check": "empty_sentence", "value": number})

    return errors


def long_sentences(results: list[dict], max_words: int) -> list[dict]:
    """Return a warning for every sentence with more than max_words words.

    >>> long_sentences([{"item": "m1", "sentences": ["Kurz und gut.", "Eins zwei drei vier fünf."]}], 4)
    [{'item': 'm1', 'check': 'long_sentence', 'value': 5}]
    """
    warnings = []
    for result in results:
        for sentence in result["sentences"]:
            words = len(sentence.split())
            if words > max_words:
                warnings.append({"item": result["item"], "check": "long_sentence", "value": words})
    return warnings


def assemble_script(groups: list[tuple[str, list[dict]]], sentences_by_item: dict[str, list[str]],
                    transitions: dict[str, str], texts: dict[str, str]) -> list[dict]:
    """Build the spoken order: greeting, per category transition and sentences, AI note, closing.

    >>> groups = [("sports", [{"id": "m1"}])]
    >>> script = assemble_script(groups, {"m1": ["Bayern gewinnt."]}, {"sports": "Und nun zum Sport."},
    ...                          {"greeting": "Hallo.", "ai_note": "KI.", "closing": "Tschüss."})
    >>> [(line["id"], line["kind"], line["item"]) for line in script]
    [('s001', 'greeting', None), ('s002', 'transition', None), ('s003', 'content', 'm1'), ('s004', 'ai_note', None), ('s005', 'closing', None)]
    """
    lines = [("greeting", None, texts["greeting"])]
    for category, members in groups:
        lines.append(("transition", None, transitions[category]))
        for item in members:
            for sentence in sentences_by_item[item["id"]]:
                lines.append(("content", item["id"], sentence))
    lines.append(("ai_note", None, texts["ai_note"]))
    lines.append(("closing", None, texts["closing"]))
    return [{"id": f"s{number:03d}", "item": item_id, "kind": kind, "text": text}
            for number, (kind, item_id, text) in enumerate(lines, start=1)]


def save_script(path: Path, run_id: str, status: str, reason: str | None, sentences: list[dict],
                errors: list[dict], warnings: list[dict], answer: list[dict],
                items: list[dict] | None = None) -> None:
    """Write the script file with metadata, status, errors, warnings, sentences, raw answer and source items."""
    data = {
        "run_id": run_id,
        "stage": "script",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "errors": errors,
        "warnings": warnings,
        "sentences": sentences,
        "answer": answer,
        "items": items or [],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def script(input_path: Path, categories_path: Path, prompt_path: Path, texts_path: Path,
           output_path: Path, run_id: str, model: str, timeout_ms: int, attempts: int,
           temperature: float, max_words: int) -> tuple[str, Path]:
    """Write the briefing sentences with one LLM call, check them, assemble the script."""
    # 1. load inputs; unreadable input or no items is a technical abort
    try:
        items = load_json(input_path)["items"]
        config = load_json(categories_path)
        texts = load_json(texts_path)
        template = load_text(prompt_path)
    except (OSError, ValueError, KeyError) as error:
        save_script(output_path, run_id, "abort", f"input not readable: {error}", [], [], [], [])
        return "abort", output_path
    if not items:
        save_script(output_path, run_id, "abort", "no items", [], [], [], [])
        return "abort", output_path

    # 2. order and transitions come from categories.json
    transitions = {category["id"]: category["transition"] for category in config["categories"]}
    try:
        groups = group_by_category(items, config["briefing_order"])
        client = make_client(timeout_ms, attempts)
    except (ValueError, KeyError) as error:
        save_script(output_path, run_id, "abort", str(error), [], [], [], [])
        return "abort", output_path

    # 3. one call for all items; the LLM writes only the sentences
    prompt = template.replace("{{ITEMS}}", format_script_items(items))
    try:
        answer = parse_response(call_llm(client, model, prompt, temperature, list[ItemSentences]))
    except Exception as error:
        save_script(output_path, run_id, "abort", f"llm error: {error}", [], [], [], [])
        return "abort", output_path

    # 4. check; long sentences only warn, errors stop before assembling
    errors = validate_script(items, answer)
    warnings = long_sentences(answer, max_words)
    if errors:
        save_script(output_path, run_id, "abort", f"{len(errors)} errors", [], errors, warnings, answer)
        return "abort", output_path

    # 5. code assembles the spoken order and numbers the sentences
    sentences_by_item = {result["item"]: result["sentences"] for result in answer}
    sentences = assemble_script(groups, sentences_by_item, transitions, texts)
    save_script(output_path, run_id, "ok", None, sentences, errors, warnings, answer, items)
    return "ok", output_path
