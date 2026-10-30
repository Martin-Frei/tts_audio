"""Tool review: a person decides on the findings of factcheck after a stop.

Not a pipeline stage. run.py stops after factcheck (one "widerspricht" or
stop_at_unsupported "nicht_belegt"); review.py shows every finding, the person
decides, and the result goes to _factcheck_reviewed.json. factcheck_apply then
reads that file instead of _factcheck.json. _factcheck.json stays unchanged.

Workflow (review):
    1. Find _factcheck.json and _script.json of the run.
    2. check_script_match: if a sentence in _script.json differs from the one
       the checker judged, the verdict is stale: abort, rerun factcheck.
    3. findings: all verdicts "nicht_belegt" or "widerspricht".
    4. For each finding: format_finding shows sentence, verdict, reason,
       title and teaser; ask_decision asks keep (passt) or drop (passt nicht).
       keep -> "belegt", own reason required; drop -> the checker's verdict
       stays, factcheck_apply removes the item. Changed entries get by "human".
    5. summary counts the verdicts; the person confirms before saving.
       Quit or no confirmation -> nothing is written, the stop stays.
    6. save_reviewed writes all verdicts with status "ok".

Functions:
    run_paths(project, run_id)                         paths of factcheck, script, reviewed
    check_script_match(checked, current)               ids whose text differs
    findings(verdicts)                                 verdicts that need a decision
    format_finding(verdict, sentence, item)            text block for one finding
    ask_decision(verdict, ask)                         new verdict after the decision, None on quit
    summary(verdicts)                                  counts per verdict
    save_reviewed(path, data, verdicts)                write the reviewed file
    review(project, run_id, ask)                       run the tool, return path or None

Dependencies:
    classify (own module, load_json); standard library: argparse, collections,
    datetime, json, pathlib.

Start and test (from the repo root):
    python src\\review.py --run 2026-10-28_1429
    python run.py --profile news_classify --from factcheck_apply --run 2026-10-28_1429
    python -m pytest src\\review.py -v
"""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from classify import load_json


FLAGGED = {"nicht_belegt", "widerspricht"}
RUNS_DIR = Path("data") / "runs"


def run_paths(project: str, run_id: str) -> dict[str, Path]:
    """Return the paths of the files review reads and writes.

    >>> run_paths("news", "2026-10-28_1429")["reviewed"].name
    'news_2026-10-28_1429_factcheck_reviewed.json'
    """
    folder = RUNS_DIR / project / run_id
    stem = f"{project}_{run_id}"
    return {
        "factcheck": folder / f"{stem}_factcheck.json",
        "script": folder / f"{stem}_script.json",
        "reviewed": folder / f"{stem}_factcheck_reviewed.json",
    }


def check_script_match(checked: list[dict], current: list[dict]) -> list[str]:
    """Return the ids whose text differs between the judged sentences and the current script.

    >>> check_script_match([{"id": "s007", "text": "330 Euro"}], [{"id": "s007", "text": "380 Euro"}])
    ['s007']
    >>> check_script_match([{"id": "s007", "text": "330 Euro"}], [{"id": "s007", "text": "330 Euro"}])
    []
    """
    judged = {sentence["id"]: sentence["text"] for sentence in checked}
    now = {sentence["id"]: sentence["text"] for sentence in current}
    return [sentence_id for sentence_id in sorted(judged.keys() | now.keys())
            if judged.get(sentence_id) != now.get(sentence_id)]


def findings(verdicts: list[dict]) -> list[dict]:
    """Return the verdicts a person has to decide on.

    >>> [v["id"] for v in findings([{"id": "s003", "verdict": "belegt"},
    ...                              {"id": "s007", "verdict": "widerspricht"}])]
    ['s007']
    """
    return [verdict for verdict in verdicts if verdict["verdict"] in FLAGGED]


def format_finding(verdict: dict, sentence: dict, item: dict | None) -> str:
    """Return one finding as a text block: sentence, verdict, reason, title, teaser."""
    title = item["title"] if item else "(no item)"
    teaser = item["teaser"] if item else "(no item)"
    return (f"{verdict['id']}  {verdict['verdict']}  (by {verdict.get('by', 'llm')})\n"
            f"Sentence: {sentence['text']}\n"
            f"Reason:   {verdict['reason']}\n"
            f"Title:    {title}\n"
            f"Teaser:   {teaser}")


def ask_decision(verdict: dict, ask=input) -> dict | None:
    """Ask keep or drop and a reason; return the new verdict, or None if the person quits.

    >>> answers = iter(["k", "Teaser nennt 330 Euro"])
    >>> ask_decision({"id": "s007", "verdict": "nicht_belegt", "reason": "x", "by": "llm"},
    ...              lambda _: next(answers))
    {'id': 's007', 'verdict': 'belegt', 'reason': 'Teaser nennt 330 Euro', 'by': 'human'}
    >>> answers = iter(["d", ""])
    >>> ask_decision({"id": "s012", "verdict": "widerspricht", "reason": "source says 330", "by": "llm"},
    ...              lambda _: next(answers))
    {'id': 's012', 'verdict': 'widerspricht', 'reason': 'source says 330', 'by': 'human'}
    """
    while True:
        choice = ask("[k] keep (passt)  [d] drop (passt nicht)  [q] quit without saving: ").strip().lower()
        if choice == "q":
            return None
        if choice in ("k", "d"):
            break
    while True:
        if choice == "k":
            reason = ask("Reason (required, you overrule the checker): ").strip()
        else:
            reason = ask("Reason (empty = keep the checker's reason): ").strip()
        if reason or choice == "d":
            break
    new_verdict = "belegt" if choice == "k" else verdict["verdict"]
    return {"id": verdict["id"], "verdict": new_verdict,
            "reason": reason or verdict["reason"], "by": "human"}


def summary(verdicts: list[dict]) -> dict[str, int]:
    """Count the verdicts per kind.

    >>> summary([{"verdict": "belegt"}, {"verdict": "widerspricht"}, {"verdict": "belegt"}])
    {'belegt': 2, 'nicht_belegt': 0, 'widerspricht': 1}
    """
    counts = Counter(verdict["verdict"] for verdict in verdicts)
    return {name: counts[name] for name in ("belegt", "nicht_belegt", "widerspricht")}


def save_reviewed(path: Path, data: dict, verdicts: list[dict]) -> None:
    """Write all verdicts with status ok, plus sentences and items for factcheck_apply."""
    reviewed = {
        "run_id": data["run_id"],
        "stage": "review",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok",
        "reason": "reviewed by human",
        "source_status": data["status"],
        "verdicts": verdicts,
        "sentences": data["sentences"],
        "items": data["items"],
    }
    path.write_text(json.dumps(reviewed, ensure_ascii=False, indent=2), encoding="utf-8")


def review(project: str, run_id: str, ask=input) -> Path | None:
    """Show every finding, collect the decisions, write the reviewed file after confirmation."""
    paths = run_paths(project, run_id)
    try:
        data = load_json(paths["factcheck"])
        script = load_json(paths["script"])
    except (OSError, ValueError) as error:
        print(f"input not readable: {error}")
        return None

    stale = check_script_match(data["sentences"], script["sentences"])
    if stale:
        print(f"verdict is stale, sentences differ: {', '.join(stale)}. Rerun factcheck.")
        return None

    open_findings = findings(data["verdicts"])
    if not open_findings:
        print("nothing to review")
        return None

    if paths["reviewed"].exists():
        if ask(f"{paths['reviewed'].name} exists. Overwrite? [y/n]: ").strip().lower() != "y":
            return None

    sentences = {sentence["id"]: sentence for sentence in data["sentences"]}
    items = {item["id"]: item for item in data["items"]}
    decisions = {}
    for number, verdict in enumerate(open_findings, start=1):
        sentence = sentences[verdict["id"]]
        print(f"\n--- finding {number} of {len(open_findings)} ---")
        print(format_finding(verdict, sentence, items.get(sentence["item"])))
        decision = ask_decision(verdict, ask)
        if decision is None:
            print("quit: nothing written, the stop stays")
            return None
        decisions[verdict["id"]] = decision

    verdicts = [decisions.get(verdict["id"], verdict) for verdict in data["verdicts"]]
    print("\n" + ", ".join(f"{count} {name}" for name, count in summary(verdicts).items()))
    if ask("Save? [y/n]: ").strip().lower() != "y":
        print("not saved: nothing written, the stop stays")
        return None

    save_reviewed(paths["reviewed"], data, verdicts)
    print(f"written: {paths['reviewed']}")
    return paths["reviewed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Review the findings of factcheck after a stop.")
    parser.add_argument("--run", required=True, help="run id, e.g. 2026-10-28_1429")
    parser.add_argument("--project", default="news", help="project folder under data/runs")
    args = parser.parse_args()
    review(args.project, args.run)
