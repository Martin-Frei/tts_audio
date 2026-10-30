"""Stage factcheck: judge every spoken content sentence against its own source.

Reads the _script.json (sentences and source items) and writes the
_factcheck.json. factcheck only judges; it never changes or removes a
sentence (that is factcheck_apply). Sentences and items are passed on
unchanged, so factcheck_apply reads exactly the script that was checked.

Workflow (factcheck):
    1. Receive paths and parameters from run.py (profile news_classify).
    2. Load sentences, items and prompt. Only kind "content" is judged;
       greeting, transitions, source lines and AI note come from code.
    3. One call with every sentence and its own source, to the provider
       named in the profile: lmstudio (local model) or gemini.
    4. validate_verdicts: every sentence exactly once, only known verdicts.
    5. apply_number_check: a number in the sentence that is missing in the
       source turns "belegt" into "nicht_belegt" (code tightens, never loosens).
    6. decide_status: one "widerspricht", or stop_at_unsupported
       "nicht_belegt", stops the run for a manual review.
    7. Write the file with save_factcheck, return (status, output_path).

Functions:
    extract_numbers(text)                         numbers as written
    missing_numbers(sentence, item)               numbers not found in the source
    format_factcheck_input(sentences, items_by_id) sentence plus its own source
    validate_verdicts(content_ids, verdicts)      errors of the answer
    apply_number_check(sentences, items_by_id, verdicts) verdicts tightened by code
    decide_status(verdicts, stop_at_unsupported)  (status, reason)
    save_factcheck(...)                           write the file with metadata
    factcheck(...)                                run the stage, return (status, path)

Dependencies:
    llm and classify (own modules), pydantic; standard library: re, json, datetime.

Start and test:
    python run.py --profile news_classify --from factcheck --run <run_id>
    python -m pytest src\\factcheck.py tests\\test_factcheck.py -v
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from classify import load_json, load_text, parse_response
from llm import call_llm, call_lmstudio, make_client

VERDICTS = {"belegt", "nicht_belegt", "widerspricht"}


class Verdict(BaseModel):
    """Shape of one LLM answer entry: the verdict for one sentence."""
    id: str
    verdict: str
    reason: str


def extract_numbers(text: str) -> list[str]:
    """Return all numbers in a text as written, with German decimal comma or thousands dot.

    >>> extract_numbers("Von 300 auf 330 Euro, 2,5 Prozent, 1.000 Tote, im Jahr 2027.")
    ['300', '330', '2,5', '1.000', '2027']
    """
    return re.findall(r"\d+(?:[.,]\d+)*", text)


def missing_numbers(sentence: str, item: dict) -> list[str]:
    """Return the numbers of a sentence that do not appear in title or teaser of its source.

    >>> item = {"title": "Elterngeld soll steigen", "teaser": "Von 300 auf 330 Euro."}
    >>> missing_numbers("Es soll von 300 auf 350 Euro steigen.", item)
    ['350']
    """
    source = (item["title"] or "") + " " + (item["teaser"] or "")
    source_numbers = set(extract_numbers(source))
    return [number for number in extract_numbers(sentence) if number not in source_numbers]


def format_factcheck_input(sentences: list[dict], items_by_id: dict[str, dict]) -> str:
    """Format every content sentence together with its own source item.

    >>> sentences = [{"id": "s004", "item": "m067", "text": "Es soll von 300 auf 330 Euro steigen."}]
    >>> items = {"m067": {"title": "Elterngeld soll steigen", "teaser": "Von 300 auf 330 Euro."}}
    >>> print(format_factcheck_input(sentences, items))
    s004 | Satz: Es soll von 300 auf 330 Euro steigen.
         Quelle: Elterngeld soll steigen | Von 300 auf 330 Euro.
    """
    lines = []
    for sentence in sentences:
        item = items_by_id[sentence["item"]]
        lines.append(f"{sentence['id']} | Satz: {sentence['text']}")
        lines.append(f"     Quelle: {item['title'] or '-'} | {item['teaser'] or '-'}")
    return "\n".join(lines)


def validate_verdicts(content_ids: list[str], verdicts: list[dict]) -> list[dict]:
    """Check the LLM answer: every sentence exactly once, only known verdicts."""
    errors = []
    returned = [verdict["id"] for verdict in verdicts]
    for sentence_id in content_ids:
        count = returned.count(sentence_id)
        if count == 0:
            errors.append({"id": sentence_id, "check": "missing_id"})
        elif count > 1:
            errors.append({"id": sentence_id, "check": "duplicate_id"})
    for verdict in verdicts:
        if verdict["id"] not in content_ids:
            errors.append({"id": verdict["id"], "check": "unknown_id"})
        elif verdict["verdict"] not in VERDICTS:
            errors.append({"id": verdict["id"], "check": "unknown_verdict", "value": verdict["verdict"]})
    return errors


def apply_number_check(sentences: list[dict], items_by_id: dict[str, dict], verdicts: list[dict]) -> list[dict]:
    """Downgrade 'belegt' to 'nicht_belegt' when a number of the sentence is missing in its source."""
    by_id = {sentence["id"]: sentence for sentence in sentences}
    checked = []
    for verdict in verdicts:
        sentence = by_id[verdict["id"]]
        missing = missing_numbers(sentence["text"], items_by_id[sentence["item"]])
        if missing and verdict["verdict"] == "belegt":
            checked.append({**verdict, "verdict": "nicht_belegt",
                            "reason": f"numbers not in source: {missing}", "by": "code"})
        else:
            checked.append({**verdict, "by": "llm"})
    return checked


def decide_status(verdicts: list[dict], stop_at_unsupported: int) -> tuple[str, str | None]:
    """One contradiction, or stop_at_unsupported unsupported sentences, stop the run for a manual review.

    >>> decide_status([{"id": "s003", "verdict": "belegt"}, {"id": "s006", "verdict": "nicht_belegt"}], 2)
    ('ok', None)
    >>> decide_status([{"id": "s006", "verdict": "nicht_belegt"}, {"id": "s031", "verdict": "nicht_belegt"}], 2)
    ('abort', "manual review needed, not supported: ['s006', 's031']")
    >>> decide_status([{"id": "s006", "verdict": "nicht_belegt"}, {"id": "s031", "verdict": "nicht_belegt"}], 3)
    ('ok', None)
    >>> decide_status([{"id": "s015", "verdict": "widerspricht"}], 3)
    ('abort', "contradicts source: ['s015']")
    """
    contradicted = [verdict["id"] for verdict in verdicts if verdict["verdict"] == "widerspricht"]
    unsupported = [verdict["id"] for verdict in verdicts if verdict["verdict"] == "nicht_belegt"]
    if contradicted:
        return "abort", f"contradicts source: {contradicted}"
    if len(unsupported) >= stop_at_unsupported:
        return "abort", f"manual review needed, not supported: {unsupported}"
    return "ok", None


def save_factcheck(path: Path, run_id: str, status: str, reason: str | None, verdicts: list[dict],
                   errors: list[dict], sentences: list[dict], items: list[dict]) -> None:
    """Write verdicts and errors; pass sentences and source items on unchanged."""
    data = {
        "run_id": run_id,
        "stage": "factcheck",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "reason": reason,
        "errors": errors,
        "verdicts": verdicts,
        "sentences": sentences,
        "items": items,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def factcheck(input_path: Path, prompt_path: Path, output_path: Path, run_id: str,
              provider: str, model: str, url: str, timeout_ms: int, attempts: int,
              temperature: float, stop_at_unsupported: int) -> tuple[str, Path]:
    """Judge every content sentence against its own source; the code checks numbers on top."""
    # 1. load script, sources and prompt; old script files without items abort here
    try:
        data = load_json(input_path)
        sentences, items = data["sentences"], data["items"]
        template = load_text(prompt_path)
    except (OSError, ValueError, KeyError) as error:
        save_factcheck(output_path, run_id, "abort", f"input not readable: {error}", [], [], [], [])
        return "abort", output_path
    content = [sentence for sentence in sentences if sentence["kind"] == "content"]
    if not content or not items:
        save_factcheck(output_path, run_id, "abort", "no content sentences or no source items", [], [], sentences, items)
        return "abort", output_path

    # 2. one call with every sentence and its own source; provider comes from the profile
    items_by_id = {item["id"]: item for item in items}
    try:
        prompt = template.replace("{{SENTENCES}}", format_factcheck_input(content, items_by_id))
        if provider == "lmstudio":
            text = call_lmstudio(url, model, prompt, temperature, list[Verdict], timeout_ms)
        else:
            text = call_llm(make_client(timeout_ms, attempts), model, prompt, temperature, list[Verdict])
        answer = parse_response(text)
    except Exception as error:
        save_factcheck(output_path, run_id, "abort", f"llm error: {error}", [], [], sentences, items)
        return "abort", output_path

    # 3. check the answer, then let the code tighten verdicts on numbers
    errors = validate_verdicts([sentence["id"] for sentence in content], answer)
    if errors:
        save_factcheck(output_path, run_id, "abort", f"{len(errors)} errors", answer, errors, sentences, items)
        return "abort", output_path
    verdicts = apply_number_check(content, items_by_id, answer)

    # 4. one contradiction, or stop_at_unsupported unsupported sentences: manual review
    status, reason = decide_status(verdicts, stop_at_unsupported)
    save_factcheck(output_path, run_id, status, reason, verdicts, [], sentences, items)
    return status, output_path
