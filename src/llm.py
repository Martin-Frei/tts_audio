"""Shared LLM access for all LLM stages: classify, script, factcheck.

Two providers, chosen per stage in the profile:
    gemini    Google Gemini via google-genai, key from GEMINI_API_KEY
    lmstudio  a local model served by LM Studio (OpenAI-like API, no key)

Workflow:
    Gemini: make_client() creates one client with timeout and limited
    retries; the SDK retries 429 and 5xx itself. call_llm() sends one
    prompt with the response schema of the calling stage.
    LM Studio: call_lmstudio() sends one prompt with the same schema,
    converted to plain JSON schema. LM Studio needs an object at the top,
    so the list is wrapped as {"items": [...]} and unwrapped again.
    Both return the raw JSON text of a list, so parse_response() of the
    stages works for both.

Functions:
    make_client(timeout_ms, attempts)                    Gemini client
    call_llm(client, model, prompt, temperature, schema) Gemini: JSON text of the answer
    inline_refs(node, defs)                              replace $ref by the definition
    lmstudio_schema(schema)                              list schema wrapped in an object
    call_lmstudio(url, model, prompt, temperature, schema, timeout_ms)
                                                         LM Studio: JSON text of the answer

Dependencies:
    google-genai, pydantic, httpx (comes with google-genai).
    GEMINI_API_KEY in the environment for gemini (run.py loads .env).
    For lmstudio: lms server start; lms load <model>.

Start and test:
    python -m pytest src\\llm.py -q   (doctests of the schema helpers)
"""

import json
import os

import httpx
from google import genai
from google.genai import types
from pydantic import TypeAdapter


def make_client(timeout_ms: int, attempts: int) -> genai.Client:
    """Create a Gemini client with timeout and limited retries; key from GEMINI_API_KEY."""
    return genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(
            timeout=timeout_ms,
            retry_options=types.HttpRetryOptions(attempts=attempts),
        ),
    )


def call_llm(client: genai.Client, model: str, prompt: str, temperature: float, schema) -> str:
    """Send one prompt with the response schema of the calling stage; return the raw JSON text."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        ),
    )
    if response.text is None:
        raise ValueError("model returned no text")
    return response.text


def inline_refs(node, defs: dict):
    """Replace every {"$ref": "#/$defs/Name"} by the definition itself.

    >>> inline_refs({"items": {"$ref": "#/$defs/A"}}, {"A": {"type": "string"}})
    {'items': {'type': 'string'}}
    """
    if isinstance(node, dict):
        if "$ref" in node:
            return inline_refs(defs[node["$ref"].split("/")[-1]], defs)
        return {key: inline_refs(value, defs) for key, value in node.items()}
    if isinstance(node, list):
        return [inline_refs(value, defs) for value in node]
    return node


def lmstudio_schema(schema) -> dict:
    """Turn a list schema like list[Verdict] into an object schema {"items": [...]} without $ref.

    >>> from pydantic import BaseModel
    >>> class Pair(BaseModel):
    ...     id: str
    >>> lmstudio_schema(list[Pair])["properties"]["items"]["items"]["properties"]
    {'id': {'title': 'Id', 'type': 'string'}}
    """
    plain = TypeAdapter(schema).json_schema()
    defs = plain.pop("$defs", {})
    return {"type": "object", "properties": {"items": inline_refs(plain, defs)}, "required": ["items"]}


def call_lmstudio(url: str, model: str, prompt: str, temperature: float, schema, timeout_ms: int) -> str:
    """Send one prompt to LM Studio with a JSON schema; return the JSON text of the list."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "answer", "strict": True, "schema": lmstudio_schema(schema)}},
        "temperature": temperature,
        "stream": False,
    }
    response = httpx.post(url, json=payload, timeout=timeout_ms / 1000)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    if not content:
        raise ValueError("model returned no text")
    return json.dumps(json.loads(content)["items"], ensure_ascii=False)
