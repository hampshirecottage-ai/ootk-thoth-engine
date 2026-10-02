"""Builds the web-sized WebP card images from the full-size scans in static/images.

The JPG scans are about 2,700 x 3,900 px and 2-3 MB each; the pages never show a card wider
than 220 px. This writes three WebP copies per card, which the web GUI serves instead:

    static/cards/full/<slug>.webp   440 px wide (the detail panel, 220 px at 2x)
    static/cards/thumb/<slug>.webp  200 px wide (catalog, spread rows and wheels on 2x screens)
    static/cards/small/<slug>.webp  110 px wide (the same on 1x screens)

Run it after scripts/download_images.py: `python scripts/optimize_images.py` (needs Pillow).
Existing WebP files newer than their JPG are skipped; pass --force to rebuild them all.
"""
import sys

from PIL import Image

from ootk import PROJECT_ROOT

SOURCE_DIR = PROJECT_ROOT / "static" / "images"
CARDS_DIR = PROJECT_ROOT / "static" / "cards"
# name: (width in px, WebP quality)
SIZES = {"full": (440, 80), "thumb": (200, 75), "small": (110, 75)}


def optimize_images(force=False):
    sources = sorted(SOURCE_DIR.glob("*.jpg"))
    for name in SIZES:
        (CARDS_DIR / name).mkdir(parents=True, exist_ok=True)
    before = after = written = 0
    for src in sources:
        before += src.stat().st_size
        image = None
        for name, (width, quality) in SIZES.items():
            dest = CARDS_DIR / name / f"{src.stem}.webp"
            if force or not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
                if image is None:
                    image = Image.open(src).convert("RGB")
                height = round(image.height * width / image.width)
                image.resize((width, height), Image.LANCZOS).save(dest, "WEBP", quality=quality, method=6)
                written += 1
            after += dest.stat().st_size
    print(f"{len(sources)} cards, {written} WebP files written; "
          f"{before / 2**20:.1f} MB of JPG -> {after / 2**20:.1f} MB of WebP ({', '.join(SIZES)}).")


if __name__ == "__main__":
    optimize_images(force="--force" in sys.argv)
