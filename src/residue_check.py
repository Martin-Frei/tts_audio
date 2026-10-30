# src/residue_check.py

"""Stage residue_check: find what is left over before speech, change nothing.

Reads the segments of the stage before the engine (_preprocess_piper.json,
later _preprocess_gemini.json) and writes the check_report
(_residue_check.json). residue_check only checks. It never changes a text
and passes no text on: tts_piper reads the segments file, but only if this
stage reports "ok". It runs directly before the engine, so it checks exactly
what will be spoken.

Workflow (residue_check):
    1. Receive input_path, output_path and run_id from run.py.
    2. Load the segments file with load_stage().
       Not readable, status not "ok" or no segments: status "abort" with a reason.
    3. For each segment: search the text with find_residues()
       for digits, abbreviations in capitals, symbols and URLs.
       Every finding is noted with segment id, sentence ids and the found text.
    4. Zero tolerance: a single finding sets status "abort".
       The search still runs to the end, so all findings can be fixed
       in one round (lexicon or normalize, then a regression case in
       tests/testsatz.txt).
    5. Write the check_report with save_stage(key="findings").
    6. Return (status, output_path) to run.py.

Functions:
    find_residues(text)                          all residues in one text, [] for None
    residue_check(input_path, output_path, run_id)
                                                 run the stage, return (status, path)

Dependencies:
    stage_io (own module), standard library: json, logging, pathlib, re.

Known limits:
    Mixed abbreviations like "AfD" are not found (lowercase letter inside).
    Wrong but complete conversions ("siebzehn. UN-Konferenz") are not found:
    they contain no residue. Only the test sentence and the ear find them.
    The word "None" is not found (one capital letter only).

Start and test:
    python -m pytest -v
"""


import json 
import logging 
import re 
from pathlib import Path

from stage_io import load_stage, save_stage


logger = logging.getLogger(__name__)

# Regex-Muster zum Aufspüren von "Rückständen" wie URLs, Nummern, Akronymen oder Sonderzeichen:
# 
# 1. https?://\S+         -> Erkennt URLs mit http:// oder https:// 
#                          - https? : Das 's' ist optional (greift bei http:// und https://).
#                          - ://    : Wörtlicher Trenner.
#                          - \S+    : Mindestens ein Zeichen, das kein Leerzeichen ist (erfasst die ganze URL).
# 
# 2. |                    -> Oder (Alternation für die nächste Bedingung).
# 
# 3. www\.\S+             -> Erkennt Webadressen, die mit "www." beginnen 
#                          - www\.  : Wörtliches "www" gefolgt von einem echten Punkt.
#                          - \S+    : Alle folgenden Nicht-Leerzeichen.
# 
# 4. |                    -> Oder.
# 
# 5. \d+                  -> Ziffern: Erfasst eine oder mehrere aufeinanderfolgende Zahlen (0-9).
# 
# 6. |                    -> Oder.
# 
# 7. [A-ZÄÖÜ]{2,}         -> Akronyme / Großbuchstaben: 
#                          - [A-ZÄÖÜ] : Ein Großbuchstabe inklusive deutscher Umlaute.
#                          - {2,}     : Mindestens 2 Mal hintereinander (schützt vor einzelnen Großbuchstaben am Satzanfang).
# 
# 8. |                    -> Oder.
# 
# 9. [%€$&/§()\[\]{}<>@#*+=|] -> Sonderzeichen-Klasse: Matcht exakt eines der aufgeführten Symbole 
#                                (Prozent, Euro, Dollar, Ampersand, Slash, Paragraf, Klammern, etc.).
RESIDUE = re.compile(r"https?://\S+|www\.\S+|\d+|[A-ZÄÖÜ]{2,}|[%€$&/§()\[\]{}<>@#*+=|]")


def find_residues(text):
    """Return all residues in one text: digits, abbreviations, symbols, URLs.

    >>> find_residues("Der Dax fällt.")
    []
    >>> find_residues("BMW 7er und 5 %")
    ['BMW', '7', '5', '%']
    >>> find_residues(None)
    []
    """
    if text is None:
        return []                   # Gibt bei None direkt eine leere Liste zurück
    return RESIDUE.findall(text)    # Sucht alle Muster im Text und gibt sie als Liste zurück


def residue_check(input_path, output_path, run_id):
    """Check the segments for residues and report to run.py."""
    try:
        data = load_stage(input_path)                                           # Lädt die Datei mit den Segmenten
    except (FileNotFoundError, json.JSONDecodeError) as error:                  # wenn File not found
        reason = f"input not readable: {error}"                                 # reason ist eien Meldung mit Fehlermeldung
        save_stage(output_path, run_id, "residue_check", [], "abort", reason, key="findings")   # lauf speichern mit status abort und reason Meldung 
        return "abort", output_path                                             # Beenden mit status abort udn den Output pfad

    if data["status"] != "ok":                                                  # Eingabe nicht freigegeben
        reason = f"input not released: {Path(input_path).name} has status {data['status']}"  # Grund mit Dateiname und Status
        save_stage(output_path, run_id, "residue_check", [], "abort", reason, key="findings")   # Abbruch mit leerer Fundliste speichern
        return "abort", output_path                                             # Abbruch an run.py melden

    if not data.get("segments"):                                                # keine Segmente in der Eingabe (fehlt oder leer)
        reason = "no segments in input"                                         # Grund für den Abbruch
        save_stage(output_path, run_id, "residue_check", [], "abort", reason, key="findings")   # Abbruch speichern statt stilles OK
        return "abort", output_path                                             # Abbruch an run.py melden

    findings = []                                                               # leere Liste findings initialisieren
    for segment in data["segments"]:                                            # iteriert durch alle Segmente
        for found in find_residues(segment["text"]):                            # found erhält alle find_residues Werte
            findings.append({"id": segment["id"], "sentence_ids": segment["sentence_ids"],
                             "found": found})                                   # Fund mit Segment-ID und Satz-IDs anhängen

    if findings:
        status, reason = "abort", f"{len(findings)} residues found"             # Setzt den Status auf "abort", wenn Rückstände entdeckt wurde
    else:
        status, reason = "ok", None                                             # Setzt den Status auf "ok", wenn keine Rückstände gefunden wurden

    save_stage(output_path, run_id, "residue_check", findings, status, reason, key="findings")  # Speichert die Ergebnisse in der Stufen-Datei
    logger.info("residue_check: %d findings, status %s", len(findings), status)
    return status, output_path                                                  # Gibt den Endstatus und den Ausgabepfad an den Runner zurück
