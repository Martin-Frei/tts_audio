# src/residue_check.py

"""Stage residue_check: find what normalize left over, change nothing.

Reads the _normalize.json and writes the check_report (_residue_check.json).
residue_check only checks. It never changes a text and passes no text on:
tts_piper reads the _normalize.json, but only if this stage reports "ok".

Workflow (residue_check):
    1. Receive input_path, output_path and run_id from run.py.
    2. Load the normalize file with load_stage().
       If it cannot be read: status "abort" with a reason.
    3. For each item: search title and teaser with find_residues()
       for digits, abbreviations in capitals, symbols and URLs.
       Every finding is noted with item id, field and the found text.
    4. Zero tolerance: a single finding sets status "abort".
       The search still runs to the end, so all findings can be fixed
       in one round (lexicon or normalize, then a regression case in
       tests/testsatz.txt).
    5. Write the check_report with save_stage(): the findings take the
       place of the items.
    6. Return (status, output_path) to run.py.

Functions:
    find_residues(text)                          all residues in one text, [] for None
    residue_check(input_path, output_path, run_id)
                                                 run the stage, return (status, path)

Dependencies:
    stage_io (own module), standard library: json, logging, re.

Known limits:
    Mixed abbreviations like "AfD" are not found (lowercase letter inside).
    Wrong but complete conversions ("siebzehn. UN-Konferenz") are not found:
    they contain no residue. Only the test sentence and the ear find them.

Start and test:
    python -m pytest -v
"""


import json 
import logging 
import re 
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
    """Check the normalize file for residues and report to run.py."""
    try:
        data = load_stage(input_path)                                           # Lädt die normalisierte Stufen-Datei
    except (FileNotFoundError, json.JSONDecodeError) as error:                  # wenn File not found
        reason = f"input not readable: {error}"                                 # reason ist eien Meldung mit Fehlermeldung
        save_stage(output_path, run_id, "residue_check", [], "abort", reason)   # lauf speichern mit status abort und reason Meldung 
        return "abort", output_path                                             # Beenden mit status abort udn den Output pfad

    findings = []                                                               # leere Liste findings initialisieren
    for item in data["items"]:                                                  # iteriert duch data 
        for field in ("title", "teaser"):                                       # nummt nur title und teaser asu data
            for found in find_residues(item.get(field)):                        # found erhält alle find_residues Werte
                findings.append({"id": item["id"], "field": field, "found": found}) # finding wird id, fild (title od. teaser) und der Fund aus found angehängt

    if findings:
        status, reason = "abort", f"{len(findings)} residues found"             # Setzt den Status auf "abort", wenn Rückstände entdeckt wurde
    else:
        status, reason = "ok", None                                             # Setzt den Status auf "ok", wenn keine Rückstände gefunden wurden

    save_stage(output_path, run_id, "residue_check", findings, status, reason)  # Speichert die Ergebnisse in der Stufen-Datei
    logger.info("residue_check: %d findings, status %s", len(findings), status)
    return status, output_path                                                  # Gibt den Endstatus und den Ausgabepfad an den Runner zurück
