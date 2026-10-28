"""Shared Gemini access for all LLM stages: classify, script, factcheck.

Workflow:
    make_client() creates one client with timeout and limited retries;
    the SDK retries 429 and 5xx itself. call_llm() sends one prompt with
    the response schema of the calling stage and returns the raw JSON text.

Functions:
    make_client(timeout_ms, attempts)                    Gemini client, key from GEMINI_API_KEY
    call_llm(client, model, prompt, temperature, schema) raw JSON text of one answer

Dependencies:
    google-genai; GEMINI_API_KEY in the environment (run.py loads .env).

Start and test:
    No own test: it only talks to the API. Covered by the stage runs.
"""

import os

from google import genai
from google.genai import types


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
