# src/residue_check.py

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
