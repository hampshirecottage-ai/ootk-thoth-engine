"""Standard Hebrew gematria (mispar hechrachi): each of the 22 letters has its fixed number,
Aleph 1 to Tav 400. A Trump takes the value of its path letter and a court card the value of
the letter it takes through its sign (or element), both in the active mapping system. The
pips have no letter of their own (their Hebrew is the name of their Sephira), so no value."""
from ootk.shuffle import operation_number

STANDARD_VALUES = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10,
    "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90, "ק": 100,
    "ר": 200, "ש": 300, "ת": 400,
}


def letter_value(text):
    """The standard value of the first Hebrew letter in `text` ("ס (Samekh)" -> 60), or None."""
    for ch in text or "":
        if ch in STANDARD_VALUES:
            return STANDARD_VALUES[ch]
    return None


def card_value(card_data):
    """The card's letter value in the active mapping system, or None for a pip or no letter."""
    if card_data.get("arcana_type") == "Minor":
        return None
    return letter_value(card_data.get("hebrew_letter"))


def operation_totals(spread_results):
    """[(operation number, [(position number, letter text, value), ...], total), ...] in
    operation order, one entry per operation that has at least one card with a value."""
    ops = {}
    for item in spread_results:
        data = item["card_data"]
        value = card_value(data)
        if value is not None:
            ops.setdefault(operation_number(item["position_name"]), []).append(
                (item["position_number"], data["hebrew_letter"], value))
    return [(op, rows, sum(v for _, _, v in rows)) for op, rows in sorted(ops.items())]
