import os
import sys
import re
import urllib.request
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.spread_engine import DB_CONFIG

IMAGE_DIR = BASE_DIR / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Reliable CDNs hosting Lady Frieda Harris Thoth scans
CDNS = [
    "https://raw.githubusercontent.com/vaxicy/tarot-chrome-extension/main/images/thoth/",
    "https://raw.githubusercontent.com/gutenberg-tarot/tarot-cards/main/thoth/",
    "https://raw.githubusercontent.com/josh-street/tarot-api/master/public/cards/",
    "https://raw.githubusercontent.com/fabioms/tarot-api/master/public/cards/"
]

# Comprehensive filename alias map for Thoth deck variations
TITLE_ALIASES = {
    "0---the-fool": ["fool", "the-fool", "00-the-fool", "0-the-fool"],
    "i---the-magus": ["magus", "the-magus", "the-magician", "magician", "01-the-magician", "01-the-magus"],
    "ii---the-priestess": ["priestess", "the-priestess", "high-priestess", "the-high-priestess", "02-priestess", "02-the-priestess", "02-the-high-priestess", "popess"],
    "iii---the-empress": ["empress", "the-empress", "03-the-empress"],
    "iv---the-emperor": ["emperor", "the-emperor", "04-the-emperor"],
    "v---the-hierophant": ["hierophant", "the-hierophant", "05-the-hierophant"],
    "vi---the-lovers": ["lovers", "the-lovers", "06-the-lovers"],
    "vii---the-chariot": ["chariot", "the-chariot", "07-the-chariot"],
    "viii---adjustment": ["adjustment", "justice", "08-adjustment", "08-justice"],
    "ix---the-hermit": ["hermit", "the-hermit", "09-the-hermit"],
    "x---fortune": ["fortune", "wheel-of-fortune", "10-fortune", "10-wheel-of-fortune"],
    "xi---lust": ["lust", "strength", "11-lust", "11-strength"],
    "xii---the-hanged-man": ["hanged-man", "the-hanged-man", "12-the-hanged-man"],
    "xiii---death": ["death", "13-death"],
    "xiv---art": ["art", "temperance", "14-art", "14-temperance"],
    "xv---the-devil": ["devil", "the-devil", "15-the-devil"],
    "xvi---the-tower": ["tower", "the-tower", "16-the-tower"],
    "xvii---the-star": ["star", "the-star", "17-the-star"],
    "xviii---the-moon": ["moon", "the-moon", "18-the-moon"],
    "xix---the-sun": ["sun", "the-sun", "19-the-sun"],
    "xx---the-aeon": ["aeon", "the-aeon", "judgement", "judgment", "20-aeon", "20-judgement"],
    "xxi---the-universe": ["universe", "the-universe", "world", "the-world", "21-universe", "21-the-world"]
}

def get_clean_slug(title):
    clean_title = re.sub(r'^(?:[IVXLCDM]+\s*-\s*|\d+\s*-\s*)', '', title, flags=re.IGNORECASE)
    return clean_title.strip().lower().replace(" ", "-").replace("'", "")

def download_images():
    conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    with conn.cursor() as cur:
        cur.execute("SELECT card_id, title FROM thoth_cards ORDER BY card_id;")
        cards = cur.fetchall()

    print(f"Downloading Lady Frieda Harris artwork for {len(cards)} cards...")

    for card in cards:
        title = card["title"]
        local_slug = title.lower().replace(" ", "-").replace("'", "")
        local_path = IMAGE_DIR / f"{local_slug}.jpg"

        if os.path.exists(local_path) and os.path.getsize(local_path) > 5000:
            print(f"➜ Skipping (already present): {local_slug}.jpg")
            continue

        clean_slug = get_clean_slug(title)
        candidates = [clean_slug, local_slug]

        if local_slug in TITLE_ALIASES:
            candidates.extend(TITLE_ALIASES[local_slug])

        downloaded = False
        for candidate in candidates:
            if downloaded:
                break
            for base_url in CDNS:
                remote_url = f"{base_url}{candidate}.jpg"
                try:
                    req = urllib.request.Request(remote_url, headers=HEADERS)
                    with urllib.request.urlopen(req) as response, open(local_path, 'wb') as out_file:
                        out_file.write(response.read())
                    print(f"✓ Saved Lady Frieda Harris painting: {local_slug}.jpg (from {candidate}.jpg)")
                    downloaded = True
                    break
                except Exception:
                    continue

        if not downloaded:
            print(f"✗ Failed download for: {title}")

    print("\nFinished downloading Thoth card images!")

if __name__ == "__main__":
    download_images()
