# tts_audio

**English** | [Deutsch](README.de.md)

tts_audio is a Python pipeline that turns current headlines and teasers from RSS feeds into a spoken news briefing. A residue check stops the run as soon as the text still contains digits, abbreviations or symbols the voice would read out wrongly.

This is a learning project in progress. **Phase 1 is runnable:** one command turns the current feeds into an MP3 with local speech from Piper. Still open for phase 1: a fixed test sentence that runs without a single pronunciation error. Later phases add an LLM script with a fact check against the sources, Gemini TTS and a podcast feed (see roadmap).

## Pipeline (phase 1)

```
fetch → clean → normalize → residue_check → select_items → tts_piper → postprocess
```

| Stage | One task |
|---|---|
| fetch | download headlines and teasers from RSS feeds |
| clean | remove HTML remains, unify quotes and hyphens, tidy whitespace |
| normalize | make text speakable: numbers, dates, times, units, symbols, lexicon; round only where a whitelist allows it |
| residue_check | find digits, abbreviations, symbols and URLs that are left; one finding stops the run |
| select_items | keep the newest usable items (default 20) |
| tts_piper | one WAV per item with Piper, a pause between sentences |
| postprocess | join the items with a gong, set loudness to −16 LUFS, write one MP3 |

Every stage reads the file of the stage before and writes its own file. Checking stages and changing stages are separate. Which stages run is set in a profile, not in the code.

## Quick start (Windows, PowerShell)

Requirements: Python 3.11, [ffmpeg](https://ffmpeg.org/) on the PATH (for example `winget install Gyan.FFmpeg`), and a German Piper voice.

```powershell
git clone https://github.com/Martin-Frei/tts_audio.git
cd tts_audio
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Download the voice `de_DE-thorsten-high` from the [official Piper voices](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md) and put both files (`.onnx` and `.onnx.json`) into `voices/`. Voices are model files, not Python packages, and are not part of the repository.

Run the pipeline:

```powershell
python run.py --profile news_piper
```

The result lies in `data/runs/news/<run_id>/`, the run_id is the start time (`YYYY-MM-DD_HHMM`). If a stage stops, fix the cause and restart from that stage:

```powershell
python run.py --profile news_piper --from normalize
```

## Configuration

| File | Content |
|---|---|
| `config/pipelines.yaml` | profiles: stages, order, settings |
| `config/feeds.yaml` | RSS feeds |
| `config/rundung_whitelist.json` | which numbers may be rounded, and how |
| `config/aussprache_lexikon.json` | pronunciation of names and abbreviations |

The lexicon grows from real data: every finding of the residue check is fixed once and added to the test sentence.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Small functions are tested with doctest in their docstrings, stages with pytest and temporary folders. No test uses the internet or the real configuration files.

## Roadmap

1. **Piper:** fetch and speak locally. *Runnable, test sentence in progress.*
2. **Briefing script:** an LLM writes a script from the headlines, a separate stage checks every statement against the source. *Planned.*
3. **Gemini TTS:** the same script in higher quality. *Planned.*
4. **Style tests:** how style prompts change tempo and tone, measured. *Planned.*
5. **Docker Compose and podcast feed.** *Planned.*

## Notes

- Only titles and teasers are used, never full articles. Briefings from third-party news stay private and are not published.
- Every audio is marked as AI-generated (from phase 2 on, in the script).
- Licences of Piper (GPL-3.0) and of the voice are still to be checked before the repository is made public.

Documentation of each stage: `A_documentation/doku_public/` (German).
