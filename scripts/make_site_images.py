"""Builds the site's icon and link-preview images in static/.

    static/site/favicon.svg           the icon modern browsers use (drawn by hand, not written here)
    static/site/favicon.ico           16, 32 and 48 px, for browsers and crawlers that ask /favicon.ico
    static/site/apple-touch-icon.png  180 px, for phone home screens
    static/site/og-image.jpg          1200 x 630 preview card shown when a link is shared

The preview is the site's headline on the page green beside three fanned cards. The cards are the
public-domain 1909 Rider-Waite-Smith art in static/cards/full
(see static/cards/CREDITS.md), never the copyrighted Thoth paintings.

Run `python scripts/make_site_images.py` (needs Pillow; `pip install -e ".[images]"` also adds
fontTools so the preview uses the site's own fonts) after changing the colours or text.
"""
import io
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ootk import PROJECT_ROOT

STATIC = PROJECT_ROOT / "static"
SITE = STATIC / "site"
PURPLE = (58, 29, 92)       # #3a1d5c, the favicon's purple
BEIGE = (244, 236, 220)     # #f4ecdc, the favicon's card
GREEN = (46, 138, 86)       # #2e8a56, the page background
DEEP_GREEN = (24, 82, 50)   # the darker end of the preview's gradient
CREAM = (255, 224, 160)     # #ffe0a0, text directly on green
TITLE = ["Navigate", "with Tarot."]
TAGLINE = "Draw a spread. Get every card, dignity and decan worked out. Your AI interprets it."
FOOTER = "tarotthoth.com · free and open source"
PREVIEW_CARDS = ["0---the-fool.webp", "xvii---the-star.webp", "xix---the-sun.webp"]

# The site's self-hosted fonts are variable WOFF2 files; Pillow reads them once fontTools has
# turned them back into plain TrueType. Without fontTools the preview falls back to system fonts.
SITE_FONTS = {"serif": "cinzel-latin.woff2", "sans": "inter-latin.woff2"}
FALLBACKS = {
    "serif": ["DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"],
    "sans": ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/System/Library/Fonts/Supplemental/Arial.ttf"],
}


def font(kind, size, weight=400):
    try:
        from fontTools.ttLib import TTFont
        ttf = TTFont(STATIC / "fonts" / SITE_FONTS[kind])
        ttf.flavor = None
        data = io.BytesIO()
        ttf.save(data)
        data.seek(0)
        fnt = ImageFont.truetype(data, size)
        fnt.set_variation_by_axes([weight])
        return fnt
    except (ImportError, OSError):
        pass
    for name in FALLBACKS[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


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


def with_shadow(im, layer, x, y, blur=12, offset=(8, 12), alpha=100):
    """Paste RGBA `layer` at (x, y) on `im` over a soft drop shadow."""
    pad = 3 * blur
    shadow = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, alpha), (pad, pad), mask=layer.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(shadow, (x - pad + offset[0], y - pad + offset[1]))
    im.alpha_composite(layer, (x, y))


def preview():
    W, H = 1200, 630
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    for x in range(W):                              # the page green, darkening to the right
        t = x / (W - 1)
        d.line([(x, 0), (x, H)], fill=tuple(round(a + (b - a) * t) for a, b in zip(GREEN, DEEP_GREEN)))

    # Three cards fanned on the right, in cream frames.
    for i, name in enumerate(PREVIEW_CARDS):
        card = Image.open(STATIC / "cards" / "full" / name).convert("RGBA")
        card = card.resize((round(card.width * 380 / card.height), 380), Image.LANCZOS)
        framed = Image.new("RGBA", (card.width + 12, card.height + 12), (250, 246, 236, 255))
        framed.paste(card, (6, 6))
        rotated = framed.rotate((1 - i) * 14, expand=True, resample=Image.BICUBIC)
        x = 935 + (i - 1) * 150 - rotated.width // 2
        y = 320 - rotated.height // 2 + (0 if i == 1 else 25)
        with_shadow(im, rotated, x, y)

    d = ImageDraw.Draw(im)
    title_font = font("serif", 76, 700)
    for k, line in enumerate(TITLE):
        d.text((70, 125 + 87 * k), line, font=title_font, fill=CREAM)
    sub_font = font("sans", 30)
    y = 345
    for line in wrap(d, TAGLINE, sub_font, 500):
        d.text((72, y), line, font=sub_font, fill=(255, 255, 255))
        y += 39
    d.text((72, 540), FOOTER, font=font("sans", 24, 500), fill=CREAM)
    return im.convert("RGB")


def main():
    icon(48).save(SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    icon(180, rounded=False).convert("RGB").save(SITE / "apple-touch-icon.png", optimize=True)
    preview().save(SITE / "og-image.jpg", quality=85, optimize=True, progressive=True)
    for name in ("favicon.ico", "apple-touch-icon.png", "og-image.jpg"):
        print(f"{name}: {(SITE / name).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
