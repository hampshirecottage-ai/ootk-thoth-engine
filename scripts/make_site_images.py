"""Builds the site's icon and link-preview images in static/.

    static/site/favicon.svg           the icon modern browsers use (drawn by hand, not written here)
    static/site/favicon.ico           16, 32 and 48 px, for browsers and crawlers that ask /favicon.ico
    static/site/apple-touch-icon.png  180 px, for phone home screens
    static/site/og-image.jpg          1200 x 630 preview card shown when a link is shared

The preview uses the public-domain 1909 Rider-Waite-Smith art in static/cards/full (see
static/cards/CREDITS.md), never the copyrighted Thoth paintings.

Run `python scripts/make_site_images.py` (needs Pillow) after changing the colours or text.
"""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ootk import PROJECT_ROOT

STATIC = PROJECT_ROOT / "static"
SITE = STATIC / "site"
PURPLE = (58, 29, 92)       # #3a1d5c, the light theme's text colour
BEIGE = (244, 236, 220)     # #f4ecdc, the light theme's background
MUTED = (102, 85, 122)      # #66557a
PREVIEW_CARDS = ["i---the-magus.webp", "xvii---the-star.webp", "xix---the-sun.webp"]
TITLE = "LLM Tarot Reading"
SUBTITLE = ("Golden Dawn dignities, decans and Liber 777 correspondences, "
            "calculated for your LLM to interpret.")
FOOTER = "ootk.onrender.com · free and open source"


def font(names, size):
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


SERIF_BOLD = ["DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"]
SANS = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"]


def icon(size, rounded=True):
    """The favicon at `size` px: a beige card with a purple eight-pointed star on a purple
    square (as favicon.svg). Phones round the home-screen icon themselves, so that one is
    square (rounded=False)."""
    scale = 8                                   # draw large, then shrink for smooth edges
    s = size * scale
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.18 if rounded else 0, fill=PURPLE)
    d.rounded_rectangle([s * 0.27, s * 0.14, s * 0.73, s * 0.86], radius=s * 0.06, fill=BEIGE)
    c, outer, inner = s / 2, s * 0.17, s * 0.07
    points = []
    for k in range(16):
        r = outer if k % 2 == 0 else inner
        a = math.pi * k / 8 - math.pi / 2
        points.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(points, fill=PURPLE)
    return im.resize((size, size), Image.LANCZOS)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def preview():
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), BEIGE)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=PURPLE)

    # Three cards fanned on the right, each with a soft shadow.
    card_w, pad = 210, 40
    for i, name in enumerate(PREVIEW_CARDS):
        card = Image.open(STATIC / "cards" / "full" / name).convert("RGBA")
        card = card.resize((card_w, round(card.height * card_w / card.width)), Image.LANCZOS)
        framed = Image.new("RGBA", (card.width + 8, card.height + 8), (*PURPLE, 255))
        framed.paste(card, (4, 4))
        rotated = framed.rotate((1 - i) * 9, expand=True, resample=Image.BICUBIC)
        shadow = Image.new("RGBA", (rotated.width + 2 * pad, rotated.height + 2 * pad), (0, 0, 0, 0))
        shadow.paste((40, 20, 60, 80), (pad, pad), mask=rotated.split()[3])
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        x = 845 + (i - 1) * 150 - rotated.width // 2
        y = (H - rotated.height) // 2 + abs(1 - i) * 20
        im.paste(shadow, (x - pad + 6, y - pad + 12), shadow)
        im.paste(rotated, (x, y), rotated)

    title_font = font(SERIF_BOLD, 72)
    sub_font = font(SANS, 30)
    foot_font = font(SANS, 24)
    left, text_w = 64, 520
    y = 110
    for line in wrap(d, TITLE, title_font, text_w):
        d.text((left, y), line, font=title_font, fill=PURPLE)
        y += 86
    y += 24
    for line in wrap(d, SUBTITLE, sub_font, text_w):
        d.text((left, y), line, font=sub_font, fill=MUTED)
        y += 42
    ico = icon(56)
    im.paste(ico, (left, H - 112), ico)
    d.text((left + 72, H - 98), FOOTER, font=foot_font, fill=PURPLE)
    return im


def main():
    icon(48).save(SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    icon(180, rounded=False).convert("RGB").save(SITE / "apple-touch-icon.png", optimize=True)
    preview().save(SITE / "og-image.jpg", quality=85, optimize=True, progressive=True)
    for name in ("favicon.ico", "apple-touch-icon.png", "og-image.jpg"):
        print(f"{name}: {(SITE / name).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
