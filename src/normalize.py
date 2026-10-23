# src/normalize.py


"""Stage normalize. Docstring follows.

    python -m pytest -v
"""

import re
import json
import logging
from pathlib import Path

from stage_io import load_stage, save_stage
from decimal import Decimal, ROUND_HALF_UP
from num2words import num2words

UNIT_WORDS = {
    "%": "Prozent",
    "€": "Euro",
    "km": "Kilometer",
    "kg": "Kilogramm"
    }


MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


SYMBOL_WORDS = {
    "&": "und",
    "§": "Paragraf",
}


def round_half_up(value, round_to):
    """Round a Decimal commercially (half up) and return an int.

    round_to works like the second argument of round():
    0 rounds to whole numbers, -2 to hundreds.

    >>> round_half_up(Decimal("2.5"), 0)
    3
    >>> round_half_up(Decimal("1450"), -2)
    1500
    >>> round_half_up(Decimal("-0.4"), 0)
    0
    """
    step = Decimal(1).scaleb(-round_to)
    result = value.quantize(step, rounding=ROUND_HALF_UP)
    return int(result)


def qualifier(original, rounded):
    """Return "gut", "knapp" or None, depending on the rounding direction.

    original is the Decimal from the text, rounded the result of
    round_half_up(). None means: no word in front of the number.

    >>> qualifier(Decimal("2.8"), 3)
    'knapp'
    >>> qualifier(Decimal("2.4"), 2)
    'gut'
    >>> qualifier(Decimal("3.0"), 3) is None
    True
    """
    difference = original - rounded
    if difference > 0:
        return "gut"
    if difference < 0:
        return "knapp"
    return None


def to_decimal(text):
    """Convert a German number text to a Decimal.

    Dots are thousands separators, the comma is the decimal mark.

    >>> to_decimal("2,8")
    Decimal('2.8')
    >>> to_decimal("19.450")
    Decimal('19450')
    >>> to_decimal("1.250,5")
    Decimal('1250.5')
    """
    without_dots = text.replace(".", "")
    with_point = without_dots.replace(",", ".")
    return Decimal(with_point)


def spell_number(value, unit, word=None):
    """Write a number with its unit as spoken German.

    word is "knapp", "gut" or None (from qualifier()).

    >>> spell_number(3, "%", "knapp")
    'knapp drei Prozent'
    >>> spell_number(Decimal("0.4"), "%")
    'null Komma vier Prozent'
    """
    spoken = num2words(value, lang="de")
    text = spoken + " " + UNIT_WORDS[unit]
    if word is not None:
        text = word + " " + text
    return text


# Digits, optional thousands groups (.ddd), optional decimals (,d...)
NUMBER = re.compile(r"\d+(?:\.\d{3})*(?:,\d+)?")


def spell_plain_number(match):
    """Return one found number as spoken German (helper for re.sub)."""
    return num2words(to_decimal(match.group()), lang="de")


def spell_numbers(text):
    """Write out all remaining numbers in a text, without rounding.

    >>> spell_numbers("Der Dax steht bei 19.450 Punkten.")
    'Der Dax steht bei neunzehntausendvierhundertfünfzig Punkten.'
    >>> spell_numbers("Keine Zahl hier.")
    'Keine Zahl hier.'
    """
    return NUMBER.sub(spell_plain_number, text)


def spell_date(day, month, previous_word):
    """Write a day and month as spoken German, e.g. 'sechzehnten Oktober'.

    previous_word is the word in front of the date. After "der" the
    ordinal ends in -e, otherwise in -en.

    >>> spell_date(16, 10, "am")
    'sechzehnten Oktober'
    >>> spell_date(1, 5, "Der")
    'erste Mai'
    """
    ordinal = num2words(day, lang="de", to="ordinal")
    if previous_word.lower() != "der":
        ordinal = ordinal + "n"
    return ordinal + " " + MONTHS[month - 1]


# Reguläres Ausdrucksmuster für ein Datum wie "16.10." mit optionalem vorherigen Wort
DATE = re.compile(r"(?:(\w+)\s+)?(?<![\d.])(\d{1,2})\.(\d{1,2})\.(?!\d)")
#                      ^^^^^               ^^^^^^^^^   ^^^^^^^^^
#                       Group 1             Group 2    Group 3

def spell_date_match(match):
    """Replace one found date, keep the word in front (helper for re.sub)."""
    word = match.group(1) or ""
    day = int(match.group(2))
    month = int(match.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return match.group()
    spoken = spell_date(day, month, word)
    if word:
        return word + " " + spoken
    return spoken


def spell_dates(text):
    """Write out all dates like 16.10. in a text.

    >>> spell_dates("Am 16.10. stieg der Dax.")
    'Am sechzehnten Oktober stieg der Dax.'
    >>> spell_dates("Gesperrt wurde 167.0.0.1.")
    'Gesperrt wurde 167.0.0.1.'
    >>> spell_dates("Nichts am 16.13. passiert.")
    'Nichts am 16.13. passiert.'
    """
    return DATE.sub(spell_date_match, text)

# reguläre Ausdrucksmuster für Uhrzeit studne imme rudn minuten optional 
TIME = re.compile(r"(?<![\d.:])(\d{1,2})(?:[.:](\d{2}))?\s+Uhr\b")
#                                ^^^^^^^^^^            ^^^^^^
#                                Group 1               Group 2   


def spell_time_match(match):
    """Replace one found time like 11:51 Uhr (helper for re.sub)."""
    hour = int(match.group(1))
    minutes = match.group(2)
    if hour == 1:
        hour_word = "ein"
    else:
        hour_word = num2words(hour, lang="de")
    spoken = hour_word + " Uhr"
    if minutes is not None and int(minutes) != 0:
        spoken = spoken + " " + num2words(int(minutes), lang="de")
    return spoken


def spell_times(text):
    """Write out all times like 11:51 Uhr in a text.

    >>> spell_times("Beginn um 11:51 Uhr.")
    'Beginn um elf Uhr einundfünfzig.'
    >>> spell_times("Treffen um 12 Uhr.")
    'Treffen um zwölf Uhr.'
    >>> spell_times("Start um 0.30 Uhr.")
    'Start um null Uhr dreißig.'
    >>> spell_times("Start um 1.30 Uhr")
    'Start um ein Uhr dreißig'
    """
    return TIME.sub(spell_time_match, text)


def may_round(entry, value, text):
    """Return True if the whitelist entry allows rounding this value.

    Three checks: an entry exists for the unit, a keyword is in the text,
    and the absolute value is at least min_abs.

    >>> entry = {"unit": "%", "keywords": ["Marktanteil"], "round_to": 0, "min_abs": 1}
    >>> may_round(entry, Decimal("2.8"), "Der Marktanteil stieg auf 2,8 %.")
    True
    >>> may_round(entry, Decimal("4.6"), "In der Umfrage kommt sie auf 4,6 %.")
    False
    >>> may_round(entry, Decimal("0.4"), "Der Marktanteil stieg um 0,4 %.")
    False
    >>> may_round(None, Decimal("20000"), "Der Marktanteil stieg um 20.000 €.") 
    False
    """
    if entry is None:
        return False
    if not any(word in text for word in entry["keywords"]):
        return False
    if abs(value) < entry["min_abs"]:
        return False
    return True


def find_entry(whitelist, unit):
    """Return the whitelist entry for a unit, or None if there is none.

    >>> whitelist = [{"unit": "%", "keywords": ["Marktanteil"], "round_to": 0, "min_abs": 1}]
    >>> find_entry(whitelist, "%")["unit"]
    '%'
    >>> find_entry(whitelist, "€") is None
    True
    """
    for entry in whitelist:
        if entry["unit"] == unit:
            return entry
    return None 


UNITS = "|".join(re.escape(unit) for unit in UNIT_WORDS)
UNIT_NUMBER = re.compile(r"(?<![\d.,])(-?\d+(?:\.\d{3})*(?:,\d+)?)\s?(" + UNITS + r")(?!\w)")
#                          ----------- --- --- ------------ -----  ---   --------  ------
#                          1           2   3   4            5      6     7         8
# 1. (?<![\d.,]) : Stellt sicher, dass vor der Zahl keine Ziffer, kein Punkt oder Komma steht.
# 2. -?          : Ermöglicht ein optionales Minuszeichen für negative Zahlenwerte.
# 3. \d+         : Erfordert mindestens eine Startziffer für den ganzzahligen Teil.
# 4. (?:\.\d{3})*: Erfasst optionale Tausenderpunkte mit jeweils exakt drei Ziffern.
# 5. (?:,\d+)?   : Erlaubt einen optionalen Nachkommateil mit Komma und Ziffern.
# 6. \s?         : Gestattet ein optionales Leerzeichen zwischen der Zahl und der Einheit.
# 7. (...)       : Speichert die gültige Maßeinheit als eigenständige Erfassungsgruppe.
# 8. (?!\w)      : Verhindert, dass direkt nach der Einheit ein weiteres Wortzeichen folgt. 


def spell_units(text, whitelist):
    """Write out all numbers with a unit, rounding where the whitelist allows.

    >>> wl = [{"unit": "%", "keywords": ["Marktanteil"], "round_to": 0, "min_abs": 1}]
    >>> spell_units("Der Marktanteil stieg auf 2,8 %.", wl)
    'Der Marktanteil stieg auf knapp drei Prozent.'
    >>> spell_units("In der Umfrage kommt sie auf 4,6 %.", wl)
    'In der Umfrage kommt sie auf vier Komma sechs Prozent.'
    """
    def replace(match):
        value = to_decimal(match.group(1))  # Numerischer Wert als Decimal (kann auch Dezimalstellen haben)
        unit = match.group(2)               # Die erkannte Maßeinheit (z. B. %, kg)
        entry = find_entry(whitelist, unit) # Passenden Whitelist-Eintrag für diese Einheit suchen
        if may_round(entry, value, text):   # Prüfen, ob laut Whitelist (Keyword, min_abs) gerundet werden darf
            rounded = round_half_up(value, entry["round_to"])  # Kaufmännisch auf die gewünschten Dezimalstellen runden
            return spell_number(rounded, unit, qualifier(value, rounded))  # Mit Qualifizierer (z.B. "knapp") ausschreiben
        return spell_number(value, unit)    # Fallback: Zahl ungerundet mit Einheit ausschreiben

    return UNIT_NUMBER.sub(replace, text)


def spell_symbols(text):
    """Replace symbols like & with spoken words.

    >>> spell_symbols("Lindt & Sprüngli legt zu.")
    'Lindt und Sprüngli legt zu.'
    >>> spell_symbols("Streit um § 218.")
    'Streit um Paragraf 218.'
    """
    for symbol, word in SYMBOL_WORDS.items():  # Iteriert durch alle definierten Symbole und deren gesprochene Wörter.
        text = text.replace(symbol, word)      # Ersetzt jedes gefundene Symbol im Text durch das ausgeschriebene Wort.
    return text                                # Gibt den bereinigten Text mit den aufgelösten Symbolen zurück.


def apply_lexicon(text, lexicon):
    """Replace whole words from the pronunciation lexicon.

    >>> lexicon = {"DAX": "Dax", "Dr.": "Doktor", "F&E": "F und E"}
    >>> apply_lexicon("Der DAX und der MDAX stiegen.", lexicon)
    'Der Dax und der MDAX stiegen.'
    >>> apply_lexicon("Dr. Müller leitet F&E.", lexicon)
    'Doktor Müller leitet F und E.'
    """
    for written, spoken in lexicon.items():              # Iteriert durch alle Schlüssel-Wert-Paare (geschriebenes Wort und gesprochene Form) im Lexikon.
        pattern = r"(?<!\w)" + re.escape(written) + r"(?!\w)"  # Erstellt ein sicheres RegEx-Muster mit Wortgrenzen für den aktuellen Begriff.
        text = re.sub(pattern, spoken, text)             # Ersetzt alle Vorkommen des Begriffs im Text durch die gesprochene Variante.
    return text

# pattern = r"(?<!\w)" + re.escape(written) + r"(?!\w)"
# 1. (?<!\w)   : Stellt sicher, dass vor dem Suchbegriff kein weiteres Wortzeichen steht (linker Wort-Grenzschutz).
# 2. re.escape : Maskiert eventuelle Sonderzeichen im Suchbegriff, damit sie sicher als Text interpretiert werden.
# 3. (?!\w)    : Stellt sicher, dass nach dem Suchbegriff kein weiteres Wortzeichen folgt (rechter Wort-Grenzschutz).


def normalize_text(text, whitelist, lexicon):
    """Make one text speakable. The order of the passes matters.

    >>> wl = [{"unit": "%", "keywords": ["Marktanteil"], "round_to": 0, "min_abs": 1}]
    >>> lex = {"DAX": "Dax"}
    >>> normalize_text("Am 16.10. stieg der Marktanteil auf 2,8 %.", wl, lex)
    'Am sechzehnten Oktober stieg der Marktanteil auf knapp drei Prozent.'
    >>> normalize_text(None, wl, lex) is None
    True
    """
    if text is None:                  # Fängt leere oder nicht vorhandene Eingaben (None) direkt ab.
        return None                   # Gibt None sofort zurück, um Fehler bei String-Operationen zu verhindern.
    text = apply_lexicon(text, lexicon) # 1. Ersetzt spezifische Fachbegriffe, Titel und Abkürzungen aus dem Lexikon.
    text = spell_dates(text)            # 2. Formatiert Datumsangaben (z.B. 16.10.) in gesprochene Ordnungszahlen Und Monatsnamen um.
    text = spell_times(text)            # 3. Wandelt Uhrzeiten (z.B. 11:51 Uhr) in eine natürlich gesprochene Form.
    text = spell_units(text, whitelist) # 4. Verarbeitet Zahlen mit Einheiten und wendet die Whitelist-Rundung an.
    text = spell_numbers(text)          # 5. Übersetzt alle verbleibenden, isolierten Zahlen im Text in Wörter.
    text = spell_symbols(text)          # 6. Löst restliche Symbole (wie kaufmännisches Und oder Paragrafen) auf.
    return text                         # Gibt den vollständig normalisierten, TTS-fertigen Text zurück.


def load_config(path):
    """Read a JSON config file (whitelist or lexicon)."""
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def normalize_item(item, whitelist, lexicon):
    """Return a copy of one item with title and teaser made speakable."""
    new_item = dict(item)                                                   # Erstellt eine Kopie des Datensatzes, um das Original unverändert zu lassen.
    new_item["title"] = normalize_text(item["title"], whitelist, lexicon)   # Wendet die Text-Normalisierung auf den Titel an.
    new_item["teaser"] = normalize_text(item["teaser"], whitelist, lexicon) # Wendet die Text-Normalisierung auf den Teaser an.
    return new_item                                                         # Gibt das verarbeitete Item zurück.


def normalize(input_path, output_path, run_id, whitelist_path, lexicon_path):
    """Run the stage normalize and report the result to run.py."""
    try:
        data = load_stage(input_path)
        whitelist = load_config(whitelist_path)
        lexicon = load_config(lexicon_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        reason = f"input not readable: {error}"
        save_stage(output_path, run_id, "normalize", [], "abort", reason)   # Protokolliert den Fehler und bricht die Stufe ab. 
        logging.error("normalize aborted: %s", reason)
        return "abort", output_path                                         # Signalisiert dem Runner den Abbruchstatus.

    if not data["items"]:
        reason = "no items in input"
        save_stage(output_path, run_id, "normalize", [], "abort", reason)
        logging.error("normalize aborted: %s", reason)
        return "abort", output_path

    items = []
    for item in data["items"]:
        items.append(normalize_item(item, whitelist, lexicon))              # Iteriert durch alle Items und normalisiert sie nacheinander.

    save_stage(output_path, run_id, "normalize", items, "ok")               # Speichert die erfolgreich verarbeiteten Items mit Status "ok".
    logging.info("normalize: %d items written to %s", len(items), output_path)
    return "ok", output_path                                                # Gibt den erfolgreichen Abschluss an den Pipeline-Runner zurück
