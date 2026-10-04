"""Card art: every one of the 78 Thoth titles shows the right Rider-Waite-Smith picture.

Three checks, so a card can't quietly show the wrong art:
- every title has its small, thumb and full WebP;
- the Waite card each image was cut from (scripts/download_images.py) is the one the page
  names in its "Pictured: Rider-Waite-Smith ..." note, or carries the same name when there is none;
- each image still looks like the picture checked by eye on 2026-10-04 (with printed Waite names, courts by Golden Dawn rank, and added banners on the 2-10s) (a 256-bit difference
  hash per card in card_art_fingerprints.json), in all three sizes.

After deliberately replacing the art, look at every card, then refresh the fingerprints:
    python tests/test_card_art.py --update
"""
import json
import re
import sys
from pathlib import Path

import pytest

from ootk import PROJECT_ROOT
from ootk.visual import art_note, card_slug, rws_art_name

CARDS = PROJECT_ROOT / "static" / "cards"
SIZES = ("small", "thumb", "full")
FINGERPRINTS = Path(__file__).with_name("card_art_fingerprints.json")


def thoth_titles():
    """The 78 titles, read from the thoth_cards data in database/schema.sql."""
    sql = (PROJECT_ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    block = sql.split("COPY public.thoth_cards", 1)[1].split("\n", 1)[1].split("\n\\.", 1)[0]
    return [line.split("\t")[1] for line in block.splitlines()]


TITLES = thoth_titles()


def card_sources():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        pytest.importorskip("PIL")
        import download_images
    finally:
        sys.path.pop(0)
    return download_images.card_sources()


# The source files' own naming (github.com/mixvlad/TarotCards, rider-waite/full).
SOURCE_SUITS = {"Wands": "Wands", "Cups": "Cups", "Swords": "Swords", "Pents": "Pentacles"}
SOURCE_RANKS = {1: "Ace", 11: "Page", 12: "Knight", 13: "Queen", 14: "King"}
# Trumps whose Waite name differs only in wording, not in what the card is.
SAME_TRUMP = {"The Magus": "Magician", "The Priestess": "High Priestess", "Fortune": "Wheel of Fortune"}
ROMAN = {r: n for n, r in enumerate("0 I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII "
                                       "XVIII XIX XX XXI".split())}


def waite_name(source):
    """'14_Temperance' -> (14, 'Temperance'); 'Pents14' -> (None, 'King of Pentacles')."""
    m = re.fullmatch(r"(\d\d)_(\w+)", source)
    if m:
        return int(m[1]), m[2].replace("_", " ")
    m = re.fullmatch(r"([A-Za-z]+)(\d\d)", source)
    n = int(m[2])
    return None, f"{SOURCE_RANKS.get(n, n)} of {SOURCE_SUITS[m[1]]}"


def test_there_are_78_titles():
    assert len(TITLES) == 78 and len(set(map(card_slug, TITLES))) == 78


@pytest.mark.parametrize("title", TITLES)
def test_every_title_has_an_image_in_every_size(title):
    for size in SIZES:
        assert (CARDS / size / f"{card_slug(title)}.webp").is_file(), (size, title)


def test_art_note_names_the_waite_card_each_image_comes_from():
    sources = card_sources()
    assert sorted(sources) == sorted(map(card_slug, TITLES))
    for title in TITLES:
        number, waite = waite_name(sources[card_slug(title)])
        named = rws_art_name(title)
        if " - " in title and title.split(" - ")[0] in ROMAN:            # a trump
            thoth = title.split(" - ", 1)[1]
            assert waite.removeprefix("The ") == (named or SAME_TRUMP.get(thoth, thoth)).removeprefix("The "), title
            if not named:
                assert number == ROMAN[title.split(" - ")[0]], title
        else:
            plain = re.sub(r"\bDisks\b", "Pentacles", title.split(" - ")[0])
            assert waite == (named or plain), title


def test_art_notes_cover_only_the_renamed_cards():
    noted = [t for t in TITLES if art_note(t)]
    assert len(noted) == 17                     # 5 trumps + 12 Knights, Princes and Princesses
    assert art_note("Knight of Wands") == "Pictured: Rider-Waite-Smith King of Wands"
    assert art_note("Prince of Disks") == "Pictured: Rider-Waite-Smith Knight of Pentacles"
    assert art_note("Princess of Cups") == "Pictured: Rider-Waite-Smith Page of Cups"
    assert art_note("XI - Lust") == "Pictured: Rider-Waite-Smith Strength"
    assert art_note("VIII - Adjustment") == "Pictured: Rider-Waite-Smith Justice"
    assert art_note("Queen of Swords") == art_note("5 of Disks - Worry") == art_note("XIX - The Sun") == ""


def test_numbered_cards_get_a_banner_with_their_thoth_title():
    pytest.importorskip("PIL")
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        from download_images import pip_banner_text
    finally:
        sys.path.pop(0)
    banners = {t: pip_banner_text(card_slug(t)) for t in TITLES}
    assert sum(1 for b in banners.values() if b) == 36
    for title, banner in banners.items():
        if re.fullmatch(r"\d+ of \w+ - \w+", title):     # '2 of Disks - Change'
            number_suit, name = title.split(" - ")
            number, suit = number_suit.split(" of ")
            assert banner == f"{number} of {suit.upper()} · {name.upper()}", title
        else:
            assert banner is None, title


def dhash(path, side=16):
    """256-bit difference hash: does each pixel get brighter or darker to its right?"""
    from PIL import Image
    with Image.open(path) as im:
        px = im.convert("L").resize((side + 1, side), Image.LANCZOS).tobytes()
    bits = 0
    for y in range(side):
        row = px[y * (side + 1):(y + 1) * (side + 1)]
        for x in range(side):
            bits = bits << 1 | (row[x] > row[x + 1])
    return bits


# Measured 2026-10-04: one card in different sizes differs by at most 13 bits, two different
# cards by at least 75.
SAME_CARD_BITS = 40


def test_every_image_still_shows_its_checked_picture():
    pytest.importorskip("PIL")
    expected = {slug: int(h, 16) for slug, h in json.loads(FINGERPRINTS.read_text()).items()}
    assert sorted(expected) == sorted(map(card_slug, TITLES))
    wrong = []
    for slug, want in expected.items():
        for size in SIZES:
            got = dhash(CARDS / size / f"{slug}.webp")
            nearest = min(expected, key=lambda s: bin(expected[s] ^ got).count("1"))
            if bin(want ^ got).count("1") > SAME_CARD_BITS or nearest != slug:
                wrong.append(f"{size}/{slug}.webp looks like {nearest}")
    assert not wrong, wrong


if __name__ == "__main__" and "--update" in sys.argv:
    FINGERPRINTS.write_text(json.dumps(
        {card_slug(t): f"{dhash(CARDS / 'full' / f'{card_slug(t)}.webp'):064x}" for t in sorted(TITLES, key=card_slug)},
        indent=1) + "\n")
    print(f"Wrote {FINGERPRINTS}")
