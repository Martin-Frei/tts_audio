# run.py


"""Orchestrator: run the stages of a profile one after the other.

Workflow (run.py):
    1. Read the profile from config/pipelines.yaml: project, stages, params.
    2. New run: the run_id is the start time (JJJJ-MM-TT_HHMM), the run
       folder is data/runs/<project>/<run_id>/.
       Restart with --from <stage>: the last run of the project (or --run
       <id>), shown and confirmed first. Files from that stage on are
       overwritten, the manifest notes the restart with the time.
    3. plan() gives every stage its input file and its output file.
       A check stage (residue_check) passes no text on: the next stage
       reads the file of the stage before the check. If the profile has
       params.input, the first stage reads that file (test sentence).
    4. For each stage: call it, then read its file. A stage counts as done
       only if its file exists AND its status is "ok". The file is the
       truth, not the returned value.
    5. Write the stage into the manifest, after its file (file first,
       manifest second).
    6. Stop at the first stage that is not done. Otherwise the MP3 lies
       in the run folder.

Functions:
    stage_file(run_dir, project, run_id, stage)   path of a stage file
    plan(stages, run_dir, project, run_id, first_input=None)
                                                  (stage, input, output) per stage
    latest_run(project)                           run_id of the newest run
    run(profile_name, run_id, from_stage=None)    run the stages, return (status, info)
    main()                                        command line

Dependencies:
    pyyaml, python-dotenv, stage_io and all stage modules in src/.
    GEMINI_API_KEY in .env for stages that call Gemini (classify).

Start:
    python run.py --profile news_piper
    python run.py --profile news_piper --from normalize
    python run.py --profile news_piper --from normalize --run 2026-10-26_0800
    python run.py --profile testsatz_piper
    python run.py --profile news_classify
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stage_io import load_stage                      
from fetch import fetch                              
from clean import clean                              
from classify import classify
from normalize import normalize                      
from residue_check import residue_check              
from select_items import select_items                
from tts_piper import tts_piper                      
from postprocess import postprocess     
from script import script     
from factcheck import factcheck        

logger = logging.getLogger("run")

RUNS_DIR = Path("data/runs")
LOGS_DIR = Path("logs")
PROFILES_PATH = Path("config/pipelines.yaml")

# How each stage is called. All get input, output and run_id;
# some also need settings from the profile (params).
STAGES = {
    "fetch": lambda inp, out, run_id, p: fetch(p["feeds"], out, run_id),
    "clean": lambda inp, out, run_id, p: clean(inp, out, run_id),
    "classify": lambda inp, out, run_id, p: classify(inp, Path(p["categories"]), Path(p["classify_prompt"]), out, run_id, p["model"], p["batch_size"], p["timeout_ms"], p["attempts"], p["temperature"], p["min_interval_s"]),
    "normalize": lambda inp, out, run_id, p: normalize(inp, out, run_id, p["whitelist"], p["lexicon"]),
    "residue_check": lambda inp, out, run_id, p: residue_check(inp, out, run_id),
    "select_items": lambda inp, out, run_id, p: select_items(inp, out, run_id, p["max_items"]),
    "tts_piper": lambda inp, out, run_id, p: tts_piper(inp, out, run_id, p["voice"]),
    "postprocess": lambda inp, out, run_id, p: postprocess(inp, out, run_id),
    "script": lambda inp, out, run_id, p: script(inp, Path(p["categories"]), Path(p["script_prompt"]), Path(p["script_texts"]), out, run_id, p["model"], p["timeout_ms"], p["attempts"], p["temperature"], p["max_words"]),
    "factcheck": lambda inp, out, run_id, p: factcheck(inp, Path(p["factcheck_prompt"]), out, run_id, p["factcheck_provider"], p["factcheck_model"], p["lmstudio_url"], p["factcheck_timeout_ms"], p["attempts"], p["temperature"], p["stop_at_unsupported"]),   
}

# Stages that only check: their file holds findings, not items.
# This is a property of the stage itself, like MONTHS in normalize, so it lives in code.
CHECK_STAGES = {"residue_check"}

# fetch writes the "raw" file, all other stages are named after themselves.
FILE_NAMES = {"fetch": "raw"}


def stage_file(run_dir, project, run_id, stage):
    """Return the path of a stage file. Every name holds the full run_id.

    >>> stage_file(Path("data/runs/news/2026-10-26_0800"), "news", "2026-10-26_0800", "fetch").name
    'news_2026-10-26_0800_raw.json'
    """
    name = FILE_NAMES.get(stage, stage)
    return run_dir / f"{project}_{run_id}_{name}.json"


def plan(stages, run_dir, project, run_id, first_input=None):
    """Return (stage, input_path, output_path) for every stage.

    A check stage gets the text file, but the next stage gets it too.
    first_input is the input of the first stage, None for fetch.

    >>> steps = plan(["fetch", "normalize", "residue_check", "select_items"], Path("r"), "news", "x")
    >>> [(s, i.name if i else None, o.name) for s, i, o in steps]
    [('fetch', None, 'news_x_raw.json'), ('normalize', 'news_x_raw.json', 'news_x_normalize.json'), ('residue_check', 'news_x_normalize.json', 'news_x_residue_check.json'), ('select_items', 'news_x_normalize.json', 'news_x_select_items.json')]
    >>> plan(["normalize"], Path("r"), "testsatz", "x", Path("tests/testsatz.json"))[0][1].name
    'testsatz.json'
    """
    steps = []
    text_file = first_input
    for stage in stages:
        output = stage_file(run_dir, project, run_id, stage)
        steps.append((stage, text_file, output))
        if stage not in CHECK_STAGES:
            text_file = output
    return steps


def latest_run(project):
    """Return the run_id of the newest run of a project, or None."""
    project_dir = RUNS_DIR / project
    if not project_dir.exists():
        return None
    # Run ids are times as text (2026-10-26_0800), so they sort correctly as text.
    runs = sorted(folder.name for folder in project_dir.iterdir() if folder.is_dir())
    return runs[-1] if runs else None


def run(profile_name, run_id, from_stage=None):
    """Run the stages of a profile. Return ("ok", mp3 info) or ("abort", stage)."""
    profiles = yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    profile = profiles[profile_name]
    project, stages, params = profile["project"], profile["stages"], profile["params"]

    run_dir = RUNS_DIR / project / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / f"{project}_{run_id}_manifest.json"
    now = datetime.now().isoformat(timespec="seconds")

    if from_stage is None:
        manifest = {"run_id": run_id, "profile": profile_name, "project": project,
                    "stages": stages, "params": params, "started": now,
                    "restarts": [], "done": []}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["restarts"].append({"from": from_stage, "time": now})
        # Entries from the restart stage on become invalid.
        keep = stages[:stages.index(from_stage)]
        manifest["done"] = [entry for entry in manifest["done"] if entry["stage"] in keep]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    started = from_stage is None
    # The test sentence profile names its first input; fetch needs none.
    first_input = Path(params["input"]) if "input" in params else None
    for stage, input_path, output_path in plan(stages, run_dir, project, run_id, first_input):
        if not started:
            if stage != from_stage:
                continue
            started = True

        if input_path is not None and not input_path.exists():
            logger.error("%s: input file missing: %s", stage, input_path)
            return "abort", stage

        logger.info("start %s", stage)
        STAGES[stage](input_path, output_path, run_id, params)

        # Done only if the file exists AND its status is ok. The file is the truth.
        if not output_path.exists():
            logger.error("%s: no output file", stage)
            return "abort", stage
        result = load_stage(output_path)

        # File first, manifest second.
        manifest["done"].append({"stage": stage, "file": output_path.name,
                                 "status": result["status"],
                                 "time": datetime.now().isoformat(timespec="seconds")})
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        if result["status"] != "ok":
            logger.error("%s stopped the run: %s", stage, result["reason"])
            return "abort", stage

    logger.info("run %s done: %s", run_id, run_dir)
    return "ok", str(run_dir)


def main():
    """Command line: new run, or restart from a stage after confirmation."""
    parser = argparse.ArgumentParser(description="Run a tts_audio pipeline profile.")
    parser.add_argument("--profile", required=True, help="profile name in config/pipelines.yaml")
    parser.add_argument("--from", dest="from_stage", help="restart from this stage")
    parser.add_argument("--run", dest="run_id", help="run_id for the restart, default: the newest run")
    args = parser.parse_args()

    profiles = yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    if args.profile not in profiles:
        print(f"Unknown profile: {args.profile}")
        sys.exit(1)
    project = profiles[args.profile]["project"]

    if args.from_stage is None:
        run_id = datetime.now().strftime("%Y-%m-%d_%H%M")
    else:
        if args.from_stage not in profiles[args.profile]["stages"]:
            print(f"Stage {args.from_stage} is not in profile {args.profile}")
            sys.exit(1)
        run_id = args.run_id or latest_run(project)
        if run_id is None:
            print(f"No run found for project {project}")
            sys.exit(1)
        if args.run_id is None:
            # Restart is manual: show which run and ask first.
            answer = input(f"Restart run {run_id} from {args.from_stage}? [j/n] ")
            if answer.strip().lower() != "j":
                print("Cancelled.")
                sys.exit(0)

    # Secrets come from .env, read once by whoever starts the program.
    load_dotenv()

    # Logging belongs to whoever starts the program: here, not in the stages.
    LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOGS_DIR / f"{run_id}.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )

    status, info = run(args.profile, run_id, args.from_stage)
    print(status, info)
    sys.exit(0 if status == "ok" else 1)


if __name__ == "__main__":
    main()
