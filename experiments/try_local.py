"""Smoke test: fact-check three known sentences with a local model in LM Studio.

Workflow:
    Read prompts/factcheck_prompt.md, insert three sentences from earlier runs
    with their real source, send one request with a JSON schema to the
    LM Studio server, print the time, the verdicts and any reasoning text.
    Expected (the yardstick from the runs of 2026-10-28):
        s006 nicht_belegt  ("bis zu" and the attribution are missing)
        s004 belegt        (300 and 330 Euro, as in the source)
        s022 nicht_belegt  ("Einem Bericht zufolge" is missing)

Functions:
    none, this is a script.

Dependencies:
    httpx (comes with google-genai); LM Studio server on localhost:1234
    with qwen/qwen3.6-35b-a3b loaded.

Start from the repo root:
    lms server start
    lms load qwen/qwen3.6-35b-a3b
    python -m experiments.try_local
"""

import json
import time
from pathlib import Path

import httpx

URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen/qwen3.6-35b-a3b"

SENTENCES = """s006 | Satz: Das Elterngeld bleibt weiterhin bei 14 Monaten.
     Quelle (tagesschau): Weiterhin 14 Monate - Rolle rückwärts beim Elterngeld | Das Elterngeld bleibt laut neuen Plänen des Familienministeriums bei bis zu 14 Monaten. Eine ursprünglich geplante Kürzung auf zwölf Monate zur Entlastung des Haushalts wird damit nicht umgesetzt.
s004 | Satz: Es soll von 300 auf 330 Euro erhöht werden.
     Quelle (handelsblatt): Familien: Elterngeld soll erstmals seit Einführung steigen | Das Elterngeld soll von 300 auf 330 Euro steigen. Ein entsprechender Gesetzentwurf ging in die regierungsinterne Abstimmung.
s022 | Satz: Der 66-jährige Regime-Kritiker wurde in Teheran erneut zu einer mehrjährigen Haftstrafe verurteilt.
     Quelle (tagesschau): Erneute Haftstrafe für iranischen Regisseur Panahi | Die iranische Justiz geht weiter gegen den Regisseur und Goldene-Palme-Gewinner Jafar Panahi vor. Einem Bericht zufolge wurde der 66-Jährige Regime-Kritiker in Teheran erneut zu einer mehrjährigen Haftstrafe verurteilt."""

# Object at the top level, the list inside, as in the LM Studio examples.
SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["belegt", "nicht_belegt", "widerspricht"]},
                    "reason": {"type": "string"},
                },
                "required": ["id", "verdict", "reason"],
            },
        }
    },
    "required": ["verdicts"],
}

template = Path("prompts/factcheck_prompt.md").read_text(encoding="utf-8")
payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": template.replace("{{SENTENCES}}", SENTENCES)}],
    "response_format": {"type": "json_schema", "json_schema": {"name": "verdicts", "strict": True, "schema": SCHEMA}},
    "temperature": 0.0,
    "stream": False,
}

start = time.perf_counter()
response = httpx.post(URL, json=payload, timeout=300)
seconds = time.perf_counter() - start
response.raise_for_status()
message = response.json()["choices"][0]["message"]

print(f"time: {seconds:.1f} s")
if message.get("reasoning_content"):
    print(f"reasoning: {len(message['reasoning_content'])} characters")
for verdict in json.loads(message["content"])["verdicts"]:
    print(f"{verdict['id']}  {verdict['verdict']:<13} {verdict['reason']}")
