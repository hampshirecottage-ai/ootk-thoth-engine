"""Downloads public-domain card art into static/images, then builds the web WebP copies.

The art is Pamela Colman Smith's 1909 Rider-Waite-Smith deck (public domain in the US and
UK), mapped onto the Thoth titles. The Thoth paintings themselves are still under copyright,
so they are never downloaded or committed.

The scans come from a pinned commit of github.com/mixvlad/TarotCards (rider-waite/full,
restored scans of a 1909 "Pam-A" printing). Each one has its Roman numeral strip and title
banner cut away, because the Waite numbers and names differ from Thoth's (Strength VIII is
Lust XI, Justice XI is Adjustment VIII, Page is Prince, and so on). The page shows the
Thoth title instead.

    python scripts/download_images.py          # needs Pillow: pip install -e ".[images]"
    python scripts/download_images.py --force  # re-download and rebuild everything
"""
import sys
import urllib.request
from io import BytesIO

from PIL import Image

from ootk import PROJECT_ROOT

IMAGE_DIR = PROJECT_ROOT / "static" / "images"
SOURCE = ("https://raw.githubusercontent.com/mixvlad/TarotCards/"
          "840b84d012c6b74dc1634fa2d00d1b21f5b28093/tarot/rider-waite/full/")

# Thoth slug -> Rider-Waite-Smith file. The trumps follow Thoth numbering, so Strength and
# Justice swap places. The courts match by picture rather than Golden Dawn rank: the Knight is
# the mounted Waite Knight and the Prince the young Waite Page. Waite has no young woman among
# his courts, so the Princesses get no picture (the page shows her name instead) and his Kings
# go unused. Pentacles are Disks.
TRUMPS = {
    "0---the-fool": "00_Fool", "i---the-magus": "01_Magician",
    "ii---the-priestess": "02_High_Priestess", "iii---the-empress": "03_Empress",
    "iv---the-emperor": "04_Emperor", "v---the-hierophant": "05_Hierophant",
    "vi---the-lovers": "06_Lovers", "vii---the-chariot": "07_Chariot",
    "viii---adjustment": "11_Justice", "ix---the-hermit": "09_Hermit",
    "x---fortune": "10_Wheel_of_Fortune", "xi---lust": "08_Strength",
    "xii---the-hanged-man": "12_Hanged_Man", "xiii---death": "13_Death",
    "xiv---art": "14_Temperance", "xv---the-devil": "15_Devil", "xvi---the-tower": "16_Tower",
    "xvii---the-star": "17_Star", "xviii---the-moon": "18_Moon", "xix---the-sun": "19_Sun",
    "xx---the-aeon": "20_Judgement", "xxi---the-universe": "21_World",
}
SUITS = {"wands": "Wands", "cups": "Cups", "swords": "Swords", "disks": "Pents"}
PIP_TITLES = {
    "wands": ["dominion", "virtue", "completion", "strife", "victory", "valour", "swiftness",
              "strength", "oppression"],
    "cups": ["love", "abundance", "luxury", "disappointment", "pleasure", "debauch",
             "indolence", "happiness", "satiety"],
    "swords": ["peace", "sorrow", "truce", "defeat", "science", "futility", "interference",
               "cruelty", "ruin"],
    "disks": ["change", "works", "power", "worry", "success", "failure", "prudence", "gain",
              "wealth"],
}
COURTS = {"prince": 11, "knight": 12, "queen": 13}


def card_sources():
    cards = dict(TRUMPS)
    for suit, rws in SUITS.items():
        cards[f"ace-of-{suit}"] = f"{rws}01"
        for n, name in enumerate(PIP_TITLES[suit], start=2):
            cards[f"{n}-of-{suit}---{name}"] = f"{rws}{n:02d}"
        for court, n in COURTS.items():
            cards[f"{court}-of-{suit}"] = f"{rws}{n}"
    return cards


def trim_labels(image):
    """Cuts out the numeral strip and the title banner but keeps the black outer frame.

    Rows are measured on the 1086 x 1810 source scans: the frame's top line ends at 38,
    the numeral strip at 128, the title banner starts at 1643 and the bottom line at 1775.
    """
    scale = image.height / 1810
    top, art_top, art_bottom, bottom = (round(y * scale) for y in (38, 128, 1643, 1775))
    parts = [image.crop((0, 0, image.width, top)),
             image.crop((0, art_top, image.width, art_bottom)),
             image.crop((0, bottom, image.width, image.height))]
    out = Image.new("RGB", (image.width, sum(p.height for p in parts)))
    y = 0
    for part in parts:
        out.paste(part, (0, y))
        y += part.height
    return out


def download_images(force=False):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    cards = card_sources()
    fetched = 0
    for slug, name in cards.items():
        dest = IMAGE_DIR / f"{slug}.jpg"
        if dest.exists() and not force:
            continue
        with urllib.request.urlopen(f"{SOURCE}{name}.jpg", timeout=120) as response:
            image = Image.open(BytesIO(response.read())).convert("RGB")
        trim_labels(image).save(dest, "JPEG", quality=92)
        fetched += 1
        print(f"✓ {slug}.jpg  <- {name}.jpg")
    print(f"{fetched} of {len(cards)} cards downloaded into {IMAGE_DIR}.")
    # The web GUI serves small WebP copies, not these full-size scans.
    from optimize_images import optimize_images
    optimize_images(force=force)


if __name__ == "__main__":
    download_images(force="--force" in sys.argv)
