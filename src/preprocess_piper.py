# src/preprocess_piper.py

"""Stage preprocess_piper: cut the checked sentences into segments for Piper.

Reads the _normalize.json and writes the _preprocess_piper.json with the
list "segments". A segment is what tts_piper turns into one WAV: all
consecutive sentences of one item, or one line without item (greeting,
transition, ai note) on its own. preprocess_piper only joins texts and adds
no words. residue_check runs after this stage, so it checks exactly what
Piper will speak. Gemini gets its own preprocess_gemini in Phase 3.

Workflow (preprocess_piper):
    1. Receive input_path, output_path and run_id from run.py.
    2. Load the normalize file. Not readable, status not "ok", no sentences
       or a sentence without text: status "abort" with a reason.
    3. build_segments: consecutive sentences with the same item form one
       segment; a sentence with item None is a segment of its own.
       kind is "content" for a segment with item, else the line's kind.
    4. join_texts: texts joined with one space; a text without end mark
       gets a full stop, so Piper pauses between the sentences.
    5. Segment ids b001, b002 ... in broadcast order; sentence_ids keep
       the trace back to the sentences.
    6. Write the file with save_stage(key="segments"), return (status, path).

Functions:
    end_mark(text)                                   text ending with . ! or ?
    join_texts(texts)                                one text for one segment
    build_segments(sentences)                        segments in broadcast order
    preprocess_piper(input_path, output_path, run_id)  run the stage, return (status, path)

Dependencies:
    stage_io (own module); standard library: json, logging, pathlib.

Start and test:
    python -m pytest src\\preprocess_piper.py tests\\test_preprocess_piper.py -v
"""

import json
import logging
from pathlib import Path

from stage_io import load_stage, save_stage

logger = logging.getLogger(__name__)


def end_mark(text):
    """Return the text with an end mark, so Piper pauses after it.

    >>> end_mark("Zwei Waggons sollen entgleist sein")
    'Zwei Waggons sollen entgleist sein.'
    >>> end_mark("Wann kommt die Reform?")
    'Wann kommt die Reform?'
    """
    text = text.strip()                                         # Leerzeichen am Rand entfernen
    if not text.endswith((".", "!", "?")):
        text = text + "."                                       # Ohne Satzzeichen am Ende: Punkt anhängen
    return text


def join_texts(texts):
    """Join the texts of one segment with one space.

    >>> join_texts(["Satz eins.", "Satz zwei"])
    'Satz eins. Satz zwei.'
    """
    return " ".join(end_mark(text) for text in texts)          # Jeden Text mit Satzzeichen, dann mit Leerzeichen verbinden


def build_segments(sentences):
    """Group consecutive sentences of one item; lines without item stay alone.

    >>> lines = [{"id": "s007", "item": None, "kind": "transition", "text": "Und nun Welt."},
    ...          {"id": "s008", "item": "m062", "kind": "content", "text": "Satz eins."},
    ...          {"id": "s009", "item": "m062", "kind": "content", "text": "Satz zwei."}]
    >>> [(s["id"], s["kind"], s["sentence_ids"]) for s in build_segments(lines)]
    [('b001', 'transition', ['s007']), ('b002', 'content', ['s008', 's009'])]
    """
    groups = []                                                 # Gruppen in Sendereihenfolge
    for sentence in sentences:
        last = groups[-1] if groups else None                   # Letzte Gruppe, falls vorhanden
        same_item = (last is not None and sentence["item"] is not None
                     and last["item"] == sentence["item"])      # Gleiche Meldung wie direkt davor?
        if same_item:
            last["sentence_ids"].append(sentence["id"])         # An die laufende Meldung anhängen
            last["texts"].append(sentence["text"])
        else:
            groups.append({"item": sentence["item"], "kind": sentence["kind"],
                           "sentence_ids": [sentence["id"]], "texts": [sentence["text"]]})  # Neue Gruppe beginnen

    segments = []
    for number, group in enumerate(groups, start=1):
        segments.append({
            "id": f"b{number:03d}",                                             # Segment-ID in Sendereihenfolge
            "item": group["item"],
            "kind": "content" if group["item"] is not None else group["kind"],  # Meldung oder Art der Zeile
            "sentence_ids": group["sentence_ids"],                              # Spur zurück zu den Sätzen
            "text": join_texts(group["texts"]),                                 # Ein Text pro Segment
        })
    return segments


def preprocess_piper(input_path, output_path, run_id):
    """Cut the normalize sentences into segments for Piper and report to run.py."""
    def abort(reason):
        save_stage(output_path, run_id, "preprocess_piper", [], "abort", reason, key="segments")  # Abbruch mit leerer Liste speichern
        logger.error("preprocess_piper aborted: %s", reason)
        return "abort", output_path

    try:
        data = load_stage(input_path)                                           # Lädt die Datei von normalize
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return abort(f"input not readable: {error}")

    if data["status"] != "ok":
        return abort(f"input not released: {Path(input_path).name} has status {data['status']}")

    sentences = data.get("sentences")
    if not sentences:
        return abort("no sentences in input")

    empty = [sentence["id"] for sentence in sentences if not sentence.get("text")]  # Sätze ohne Text
    if empty:
        return abort(f"sentences without text: {', '.join(empty)}")

    segments = build_segments(sentences)
    save_stage(output_path, run_id, "preprocess_piper", segments, "ok", key="segments")  # Segmente unter "segments" speichern
    logger.info("preprocess_piper: %d sentences into %d segments", len(sentences), len(segments))
    return "ok", output_path
