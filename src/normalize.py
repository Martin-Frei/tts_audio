# src/normalize.py
"""Stage normalize. Docstring follows.

    python -m pytest -v
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from num2words import num2words

UNIT_WORDS = {
    "%": "Prozent",
    "€": "Euro",
    "km": "Kilometer",
    "kg": "Kilogramm"
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


MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


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
