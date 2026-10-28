"""Manual smoke test: run classify once on a real clean file from phase 1.

Workflow: load .env, call classify with fixed paths and parameters, print status and path.
Functions: none, this is a script.
Dependencies: python-dotenv, src.classify (google-genai, pydantic).
Start from the repo root: python -m experiments.try_classify
"""
from pathlib import Path

from dotenv import load_dotenv

from src.classify import classify

load_dotenv()
status, path = classify(
    clean_path=Path("data/runs/news/2026-10-26_1333/news_2026-10-26_1333_clean.json"),
    categories_path=Path("config/categories.json"),
    prompt_path=Path("prompts/classify_prompt.md"),
    output_path=Path("logs/classify_try.json"),
    run_id="2026-10-26_1333",
    model="gemini-3.5-flash-lite",
    batch_size=5,
    timeout_ms=30000,
    attempts=3,
    temperature=0.0,
    min_interval_s=5.0,
)
print(status, path)
