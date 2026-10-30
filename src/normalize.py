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
    step = Decimal(1).scaleb(-round_to)                     # Erstellt den Rundungsschritt basierend auf Dezimalstellen (z.B. 1 für Ganze, 0.01 für Hundertstel)
    result = value.quantize(step, rounding=ROUND_HALF_UP)   # Rundet den Dezimalwert kaufmännisch (half up) auf die gewünschte Stelle
    return int(result)                                      # Wandelt das gerundete Ergebnis in einen Integer um und gibt es zurück


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
    difference = original - rounded     # Berechnet die Differenz zwischen exaktem Dezimalwert und gerundetem Wert
    if difference > 0:                  # Wenn der originale Wert größer ist als das gerundete Ergebnis...
        return "gut"                    # ...ist es "gut" darüber (Aufrundungs-Qualifizierer)
    if difference < 0:                  # Wenn der originale Wert kleiner ist als das gerundete Ergebnis...
        return "knapp"                  # ...ist es "knapp" darunter (Abrundungs-Qualifizierer)
    return None                         # Wenn beide Werte exakt übereinstimmen, wird kein Zusatzwort benötigt


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
    without_dots = text.replace(".", "")            # Entfernt deutsche Tausenderpunkte aus dem String (z.B. "1.250" -> "1250")
    with_point = without_dots.replace(",", ".")     # Ersetzt das deutsche Dezimalkomma durch einen Punkt für Berechnungen in Python (z.B. "1250,5" -> "1250.5")
    return Decimal(with_point)                      # Konvertiert den bereinigten String in ein präzises Decimal-Objekt für exakte Finanz-/Einheiten-Berechnungen


def spell_number(value, unit, word=None):
    """Write a number with its unit as spoken German.

    word is "knapp", "gut" or None (from qualifier()).

    >>> spell_number(3, "%", "knapp")
    'knapp drei Prozent'
    >>> spell_number(Decimal("0.4"), "%")
    'null Komma vier Prozent'
    """
    spoken = say_number(value)                  # Wandelt den reinen Zahlenwert in das entsprechende deutsche Zahlwort um
    text = spoken + " " + UNIT_WORDS[unit]      # Verbindet das Zahlwort mit dem ausgeschriebenen Wort der Einheit (z.B. "drei" + " " + "Prozent")
    if word is not None:                        # Prüft, ob ein zusätzlicher Qualifizierer (wie "knapp" oder "gut") übergeben wurde
        text = word + " " + text                # Setzt den Qualifizierer vor den Text (z.B. "knapp drei Prozent")
    return text                                 # Gibt den fertigen, gesprochenen Text zurück



LETTERS = "A-Za-zÄÖÜäöüß"
NUMBER = re.compile(r"(?<![" + LETTERS + r"\d])\d+(?:\.\d{3})*(?:,\d+)?(?![" + LETTERS + r"\d])(?!\.\s+[" + LETTERS + r"])"
)

# Regex-Muster für isolierte Zahlen mit 6 detaillierten Schutz- und Formatregeln:
# 
# 1. (?<![LETTERS...])      -> Negatives Lookbehind: Unmittelbar vor der Zahl darf kein Buchstabe stehen.
# 2. (?<!...\d)            -> Negatives Lookbehind: Unmittelbar vor der Zahl darf auch keine andere Ziffer stehen.
# 3. \d+                   -> Der Ganzzahl-Kern: Es muss mindestens eine Ziffer (0-9) vorhanden sein.
# 4. (?:\.\d{3})*          -> Tausendergruppen: Erlaubt optional deutsche Tausendertrennpunkte (z. B. .234).
# 5. (?:,\d+)?             -> Dezimalteil: Erlaubt optional ein Komma gefolgt von beliebigen Nachkommastellen (z. B. ,50).
# 6. Lookaheads danach     -> Schließt nachfolgende Zeichen (Buchstaben/Ziffern) sowie Ordnungszahlen/Aufzählungen (wie "1. Januar") aus.


def spell_plain_number(match):
    """Return one found number as spoken German (helper for re.sub)."""
    return say_number(to_decimal(match.group()))                # Konvertiert den Text in ein decimal object, say_number wandelt um 


RANGE = re.compile(r"(?<=\d)-(?=\d)")
# 1. (?<=\d)        -> Positives Lookbehind: Prüft den linken Teil vor dem Bindestrich.
# 2. Linke Ziffern   -> Stellt sicher, dass direkt vor dem Trenner mindestens eine Ziffer steht.
# 3. -               -> Das Trennzeichen: Matcht den eigentlichen Bindestrich der Spanne.
# 4. (?=\d)         -> Positives Lookahead: Prüft den rechten Teil nach dem Bindestrich.
# 5. Rechte Ziffern  -> Stellt sicher, dass direkt nach dem Trenner mindestens eine Ziffer folgt.
# 6. Zweck           -> Unterscheidet echte Zahlenbereiche zuverlässig von Wort-Bindestrichen.


def spell_ranges(text):
    """Replace a dash between two numbers with 'bis'.

    >>> spell_ranges("Die Studie lief von 2020-2024.")
    'Die Studie lief von 2020 bis 2024.'
    >>> spell_ranges("Die A8-Ausfahrt ist gesperrt.")
    'Die A8-Ausfahrt ist gesperrt.'
    """
    return RANGE.sub(" bis ", text)


def spell_numbers(text):
    """Write out all remaining numbers in a text, without rounding.

    >>> spell_numbers("Der Dax steht bei 19.450 Punkten.")
    'Der Dax steht bei neunzehntausendvierhundertfünfzig Punkten.'
    >>> spell_numbers("Keine Zahl hier.")
    'Keine Zahl hier.'
    >>> spell_numbers("Der G7-Gipfel und das 5G-Netz.")
    'Der G7-Gipfel und das 5G-Netz.'
    >>> spell_numbers("Er feierte 55. Geburtstag.")
    'Er feierte 55. Geburtstag.'
    >>> spell_numbers("Er wurde 55.")
    'Er wurde fünfundfünfzig.'
    """
    return NUMBER.sub(spell_plain_number, text)

def say_number(value):
    """Return a number as spoken German; 1100 to 1999 in hundreds.

    >>> say_number(1990)
    'neunzehnhundertneunzig'
    >>> say_number(2024)
    'zweitausendvierundzwanzig'
    >>> say_number(Decimal("1500.5"))
    'eintausendfünfhundert Komma fünf'
    """
    if value == int(value) and 1100 <= value <= 1999:
        return num2words(int(value), lang="de", to="year")
    return num2words(value, lang="de")


ORDINAL_ENDINGS = {
    "am": "n", "im": "n", "zum": "n", "beim": "n", "dem": "n", "den": "n",
    "der": "", "die": "", "das": "",
    "ihr": "r", "sein": "r", "mein": "r", "unser": "r",
}

ORDINAL = re.compile(r"\b(\w+) (\d+)\. (?=\w)")
# Regex-Muster zum Erkennen von Signalwort + Zahl mit Punkt (z. B. "am 1." oder "der 15."):
# 
# 1. \b          -> Wortgrenze: Stellt sicher, dass das Signalwort am Anfang steht.
# 2. (\w+)       -> Erste Gruppe: Das Signalwort (Präposition oder Artikel, z. B. am oder der).
# 3.             -> Das feste trennende Leerzeichen zwischen Signalwort und Zahl.
# 4. (\d+)       -> Zweite Gruppe: Die Ziffern der Zahl/des Datums.
# 5. \.          -> Der Punkt direkt nach der Zahl.
# 6. (?=\w)      -> Positives Lookahead: Stellt sicher, dass nach dem folgenden Leerzeichen ein Wort beginnt.

def spell_ordinals(text):
    """Spell a number with a period as an ordinal if a signal word precedes it.
    
    >>> spell_ordinals("Es war ihr 55. Geburtstag.")
    'Es war ihr fünfundfünfzigster Geburtstag.'
    >>> spell_ordinals("Am 1. Mai wird gefeiert.")
    'Am ersten Mai wird gefeiert.'
    >>> spell_ordinals("Er feierte 55. Geburtstag.")
    'Er feierte 55. Geburtstag.'
    """
    def replace(match):
        word = match.group(1)                                                   # Holt das gefundene Signalwort (z. B. "am")
        ending = ORDINAL_ENDINGS.get(word.lower())                              # Sucht die passende Endung in ORDINAL_ENDINGS
        if ending is None:                                                      # Wenn Signal wort is None, dann....                            
            return match.group(0)                                               # .... behalte Text
        number = int(match.group(2))                                            # In number wird die gefunden Ziffer umgewandelt int
        return f"{word} {num2words(number, lang='de', to='ordinal')}{ending} "  # Generiert number => num2word und bindet word und Leerzeichen ein 
    return ORDINAL.sub(replace, text)                                           # Iteriert durch alle Fälle im text


def spell_date(day, month, previous_word):
    """Write a day and month as spoken German, e.g. 'sechzehnten Oktober'.

    previous_word is the word in front of the date. After "der" the
    ordinal ends in -e, otherwise in -en.

    >>> spell_date(16, 10, "am")
    'sechzehnten Oktober'
    >>> spell_date(1, 5, "Der")
    'erste Mai'
    """
    ordinal = num2words(day, lang="de", to="ordinal")       # Wandelt den Tag in ein deutsches Ordnungszahlwort um (z.B. 16 -> "sechzehnte")
    if previous_word.lower() != "der":                      # Prüft, ob das vorherige Wort im Text NICHT "der" ist (z.B. "am" oder keines)
        ordinal = ordinal + "n"                             # Hängt ein "n" an die Ordnungszahl an (aus "sechzehnte" wird "sechzehnten")
    return ordinal + " " + MONTHS[month - 1]                # Verbindet den Tag mit dem Monatsnamen (Monats-Index beginnt bei 0, daher month - 1)


# Reguläres Ausdrucksmuster für ein Datum wie "16.10." mit optionalem vorherigen Wort
DATE = re.compile(r"(?:(\w+)\s+)?(?<![\d.])(\d{1,2})\.(\d{1,2})\.(?!\d)")

# 1. (?:(\w+)\s+)? -> Optionales Präfix (Group 1): Fängt ein vorheriges Wort (z.B. "am") samt nachfolgendem Leerzeichen auf.
# 2. (?<![\d.])    -> Negatives Lookbehind: Verhindert, dass das Datum mitten in einer Dezimalzahl oder längeren Ziffernfolge steht.
# 3. (\d{1,2})     -> Tag (Group 2): Erfasst 1 oder 2 Ziffern für den Tag.
# 4. \.            -> Wörtlicher Trennpunkt nach dem Tag.
# 5. (\d{1,2})     -> Monat (Group 3): Erfasst 1 oder 2 Ziffern für den Monat.
# 6. \.            -> Wörtlicher Endpunkt nach dem Monat.
# 7. (?!\d)        -> Negatives Lookahead: Stellt sicher, dass direkt danach keine Ziffer folgt (schützt vor vollen Datumsangaben mit Jahr wie ".2026")

def spell_date_match(match):
    """Replace one found date, keep the word in front (helper for re.sub)."""
    word = match.group(1) or ""                     # Holt das optionale Präfix-Wort vor dem Datum (z.B. "am"), falls vorhanden
    day = int(match.group(2))                       # Extrahiert den erfassten Tag als Ganzzahl
    month = int(match.group(3))                     # Extrahiert den erfassten Monat als Ganzzahl
    if not (1 <= month <= 12 and 1 <= day <= 31):   # Prüft, ob Tag und Monat in einem logisch gültigen Bereich liegen
        return match.group()                        # Wenn ungültig (z.B. 16.13.), wird das Original unverändert zurückgegeben
    spoken = spell_date(day, month, word)           # Erstellt die gesprochene Form (Ordnungszahl + Monatsname)
    if word:                                        # Wenn ein Präfix-Wort existierte...
        return word + " " + spoken                  # ...wird es wieder vorangestellt (z.B. "am sechzehnten Oktober")
    return spoken                                   # Andernfalls nur das gesprochene Datum zurückgeben


def spell_dates(text):
    """Write out all dates like 16.10. in a text.

    >>> spell_dates("Am 16.10. stieg der Dax.")
    'Am sechzehnten Oktober stieg der Dax.'
    >>> spell_dates("Gesperrt wurde 167.0.0.1.")
    'Gesperrt wurde 167.0.0.1.'
    >>> spell_dates("Nichts am 16.13. passiert.")
    'Nichts am 16.13. passiert.'
    """
    return DATE.sub(spell_date_match, text)         # Wendet das Datums-Regex auf den Text an und ersetzt Treffer per Callback


# Regex-Muster für Uhrzeiten wie "14 Uhr", "14:30 Uhr" oder "14.30 Uhr" (Stunden immer, Minuten optional):

TIME = re.compile(r"(?<![\d.:])(\d{1,2})(?:[.:](\d{2}))?\s+Uhr\b")
 
# 1. (?<![\d.:])       -> Negatives Lookbehind: Die Uhrzeit darf nicht direkt hinter einer Ziffer, einem Punkt oder Doppelpunkt stehen (verhindert Fehltreffer).
# 2. (\d{1,2})         -> Stunde (Group 1): Erfasst 1 oder 2 Ziffern für die Stunde (z.B. "8" oder "14").
# 3. (?:[.:](\d{2}))?  -> Optionaler Minutenteil: 
#                         - [.:] Ein Punkt oder Doppelpunkt als Trenner.
#                         - (\d{2}) (Group 2): Genau zwei Ziffern für die Minuten.
#                         - Das ? am Ende macht den gesamten Minutenblock optional.
# 4. \s+               -> Ein oder mehrere Leerzeichen zwischen der Zahl und dem Wort "Uhr".
# 5. Uhr               -> Das wörtliche Wort "Uhr".
# 6. \b                -> Wortgrenze (Word Boundary): Stellt sicher, dass nach "Uhr" kein weiterer Buchstabe folgt (schützt vor Wörtern wie "Uhrzeit").


def spell_time_match(match):
    """Replace one found time like 11:51 Uhr (helper for re.sub)."""
    hour = int(match.group(1))                                      # Extrahiert die gefundene Stunde als Ganzzahl
    minutes = match.group(2)                                        # Extrahiert den optionalen Minutenteil als String (oder None)
    if hour == 1:                                                   # Sonderfall für 1 Uhr (im Deutschen sagt man "ein Uhr", nicht "eins Uhr")
        hour_word = "ein"                                           # Setzt das Stundenwort auf "ein"
    else:                                                           # Für alle anderen Stunden...
        hour_word = num2words(hour, lang="de")                      # ...wird das reguläre deutsche Zahlwort ermittelt
    spoken = hour_word + " Uhr"                                     # Baut den Basis-String für die volle Stunde zusammen (z.B. "elf Uhr")
    if minutes is not None and int(minutes) != 0:                   # Prüft, ob Minuten vorhanden und ungleich "00" sind
        spoken = spoken + " " + num2words(int(minutes), lang="de")  # Fügt die Minuten als Zahlwort hinzu (z.B. "einundfünfzig")
    return spoken                                                   # Gibt die vollständig ausgeschriebene Uhrzeit zurück


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
    return TIME.sub(spell_time_match, text)                 # Sucht alle Uhrzeiten per Regex und ersetzt sie über die Callback-Funktion


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
    if entry is None:                                           # Wenn gar kein Whitelist-Eintrag für diese Einheit existiert...
        return False                                            # ...darf nicht gerundet werden.
    if not any(word in text for word in entry["keywords"]):     # Prüft, ob keines der geforderten Schlüsselwörter im Text vorkommt
        return False                                            # Wenn kein passendes Keyword gefunden wurde, wird nicht gerundet.
    if abs(value) < entry["min_abs"]:                           # Prüft, ob der absolute Betrag des Wertes kleiner ist als das geforderte Minimum
        return False                                            # Wenn der Wert zu klein ist, greift die Rundung ebenfalls nicht.
    return True                                                 # Wenn alle Bedingungen erfüllt sind, ist das Runden offiziell erlaubt.


def find_entry(whitelist, unit):
    """Return the whitelist entry for a unit, or None if there is none.

    >>> whitelist = [{"unit": "%", "keywords": ["Marktanteil"], "round_to": 0, "min_abs": 1}]
    >>> find_entry(whitelist, "%")["unit"]
    '%'
    >>> find_entry(whitelist, "€") is None
    True
    """
    for entry in whitelist:         # Durchläuft alle Regel-Einträge in der Whitelist-Liste
        if entry["unit"] == unit:   # Sucht nach dem Eintrag, dessen definierte Einheit mit der übergebenen übereinstimmt
            return entry            # Gibt den gefundenen Regel-Eintrag zurück
    return None                     # Wenn kein passender Eintrag in der Whitelist existiert, wird None zurückgegeben

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
        value = to_decimal(match.group(1))                      # Numerischer Wert als Decimal (kann auch Dezimalstellen haben)
        unit = match.group(2)                                   # Die erkannte Maßeinheit (z. B. %, kg)
        entry = find_entry(whitelist, unit)                     # Passenden Whitelist-Eintrag für diese Einheit suchen
        if may_round(entry, value, text):                       # Prüfen, ob laut Whitelist (Keyword, min_abs) gerundet werden darf
            rounded = round_half_up(value, entry["round_to"])   # Kaufmännisch auf die gewünschten Dezimalstellen runden
            return spell_number(rounded, unit, qualifier(value, rounded))  # Mit Qualifizierer (z.B. "knapp") ausschreiben
        return spell_number(value, unit)                        # Fallback: Zahl ungerundet mit Einheit ausschreiben

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


GENDER_MARK = re.compile(r"[:*_]innen\b")
# [ :*_ ] matcht Doppelpunkt, Sternchen oder Unterstrich 
# # \b stellt sicher, dass "innen" am Wortende steht.

BINNEN_I = re.compile(r"(?<=[a-zäöüß])Innen\b")
# (?<=[a-zäöüß]) stellt sicher, dass ein Kleinbuchstabe davor steht
# \b beendet das Wort nach "Innen".

def spell_gender(text):
    """Replace gender marks (:, *, _) and the Binnen-I before 'innen' with a space.

    >>> spell_gender("Die Metzgermeister*innen trafen sich.")
    'Die Metzgermeister innen trafen sich.'
    >>> spell_gender("Die Metzgermeister_innen trafen sich.")
    'Die Metzgermeister innen trafen sich.'
    >>> spell_gender("Die Metzgermeister:innen trafen sich.")
    'Die Metzgermeister innen trafen sich.'
    >>> spell_gender("Die MetzgermeisterInnen trafen sich.")
    'Die Metzgermeister innen trafen sich.'
    >>> spell_gender("Innen und Außen sind gleich warm.")
    'Innen und Außen sind gleich warm.'
    """
    text = GENDER_MARK.sub(" innen", text)
    return BINNEN_I.sub(" innen", text)


MINUS = re.compile(r"(?<!\S)-(?=\d)")
# (?<!\S) stellt sicher, dass kein Nicht-Leerzeichen davor steht (Wortanfang oder Leerzeichen)
# - matcht das Minus-Zeichen selbst
# (?=\d) stellt sicher, dass direkt danach eine Ziffer folgt


def spell_minus(text):
    """Replace a minus sign before a number with the word 'minus'.

    >>> spell_minus("Die Temperatur fiel auf -0,4 Grad.")
    'Die Temperatur fiel auf minus 0,4 Grad.'
    >>> spell_minus("Die Studie lief von 2020-2024.")
    'Die Studie lief von 2020-2024.'
    """
    return MINUS.sub("minus ", text)


def apply_lexicon(text, lexicon):
    """Replace whole words from the pronunciation lexicon.

    >>> lexicon = {"DAX": "Dax", "Dr.": "Doktor", "F&E": "F und E"}
    >>> apply_lexicon("Der DAX und der MDAX stiegen.", lexicon)
    'Der Dax und der MDAX stiegen.'
    >>> apply_lexicon("Dr. Müller leitet F&E.", lexicon)
    'Doktor Müller leitet F und E.'
    """
    for written, spoken in lexicon.items():                     # Iteriert durch alle Schlüssel-Wert-Paare (geschriebenes Wort und gesprochene Form) im Lexikon.
        pattern = r"(?<!\w)" + re.escape(written) + r"(?!\w)"   # Erstellt ein sicheres RegEx-Muster mit Wortgrenzen für den aktuellen Begriff.
        text = re.sub(pattern, spoken, text)                    # Ersetzt alle Vorkommen des Begriffs im Text durch die gesprochene Variante.
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
    if text is None:                    # Fängt leere oder nicht vorhandene Eingaben (None) direkt ab.
        return None                     # Gibt None sofort zurück, um Fehler bei String-Operationen zu verhindern.
    text = apply_lexicon(text, lexicon) # 1. Ersetzt spezifische Fachbegriffe, Titel und Abkürzungen aus dem Lexikon.
    text = spell_gender(text)           # 2. Ersetz : * _ nur wenn : * oder _ iVm innen vorkommt mit eine Leerzeichen
    text = spell_minus(text)            # 3. Ersetz - mit minus wenn davor nichts oder Satzanfang ist udndananch gleich eien Zahl steht
    text = spell_ranges(text)           # 4. Bestimtm Ranges um - mit bis zu ersetzen     
    text = spell_dates(text)            # 5. Formatiert Datumsangaben (z.B. 16.10.) in gesprochene Ordnungszahlen Und Monatsnamen um.
    text = spell_ordinals(text)         # 6. wandelt Ordinalzahlen um
    text = spell_times(text)            # 7. Wandelt Uhrzeiten (z.B. 11:51 Uhr) in eine natürlich gesprochene Form.
    text = spell_units(text, whitelist) # 8. Verarbeitet Zahlen mit Einheiten und wendet die Whitelist-Rundung an.
    text = spell_numbers(text)          # 9. Übersetzt alle verbleibenden, isolierten Zahlen im Text in Wörter.
    text = spell_symbols(text)          # 10. Löst restliche Symbole (wie kaufmännisches Und oder Paragrafen) auf.
    return text                         # Gibt den vollständig normalisierten, TTS-fertigen Text zurück.


def load_config(path):
    """Read a JSON config file (whitelist or lexicon)."""
    with Path(path).open(encoding="utf-8") as file:     # Öffnet die angegebene Konfigurationsdatei sicher im Lesemodus mit UTF-8-Codierung
        return json.load(file)                          # Liest den JSON-Inhalt ein, wandelt ihn in Python-Datenstrukturen um und gibt ihn zurück


def normalize_sentence(sentence, whitelist, lexicon):
    """Return a copy of one sentence with its text made speakable."""
    new_sentence = dict(sentence)
    new_sentence["text"] = normalize_text(sentence["text"], whitelist, lexicon)
    return new_sentence                                                         # Gibt das verarbeitete Item zurück.


def normalize(input_path, output_path, run_id, whitelist_path, lexicon_path):
    """Run the stage normalize and report the result to run.py."""
    try:
        data = load_stage(input_path)                                           # Versucht, die Rohdaten der vorherigen Pipeline-Stufe zu laden
        whitelist = load_config(whitelist_path)                                 # Lädt die Whitelist-Regeln für Maßeinheiten aus der JSON-Datei
        lexicon = load_config(lexicon_path)                                     # Lädt das Aussprachelexikon (Abkürzungen, Päpste,...) aus JSON
    except (FileNotFoundError, json.JSONDecodeError) as error:                  # Fängt Fehler beim Laden ab (z.B. Datei fehlt oder fehlerhaftes JSON)
        reason = f"input not readable: {error}"                                 # Erstellt eine präzise Fehlerbeschreibung
        save_stage(output_path, run_id, "normalize", [], "abort", reason, key="sentences")       # Speichert den Abbruchstatus im System-Protokoll 
        logging.error("normalize aborted: %s", reason)                          # Schreibt einen entsprechenden Fehlereintrag ins Log
        return "abort", output_path                                             # Signalisiert dem Pipeline-Runner den sofortigen Abbruch

    if not data.get("sentences"):                                               # Prüft, ob die geladene JSON-Struktur leer ist (keine Items vorhanden)
        reason = "no sentences in input"                                        # Setzt den Grund für den Abbruch
        save_stage(output_path, run_id, "normalize", [], "abort", reason, key="sentences")       # Protokolliert den leeren Input als Abbruch
        logging.error("normalize aborted: %s", reason)                          # Loggt den Fehler
        return "abort", output_path                                             # Gibt den Abbruchstatus an den Runner zurück

    sentences = []                                                              # Initialisiert eine leere Liste für die fertig normalisierten Datensätze
    for sentence in data["sentences"]:                                          # Durchläuft alle einzelnen Artikel/Items nacheinander
        sentences.append(normalize_sentence(sentence, whitelist, lexicon))      # Normalisiert das Item und fügt es zur Ergebnisliste hinzu

    save_stage(output_path, run_id, "normalize", sentences, "ok", key="sentences")  # Speichert die erfolgreich verarbeiteten Items mit Status "ok".
    logging.info("normalize: %d sentences written to %s", len(sentences), output_path)  # Loggt die erfolgreiche Anzahl geschriebener Einträge
    return "ok", output_path                                                    # Gibt den Erfolgsstatus und den Ausgabepfad an den Runner zurück
