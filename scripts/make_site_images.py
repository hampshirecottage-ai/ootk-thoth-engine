"""Builds the site's icon and link-preview images in static/.

    static/site/favicon.svg           the icon modern browsers use (drawn by hand, not written here)
    static/site/favicon.ico           16, 32 and 48 px, for browsers and crawlers that ask /favicon.ico
    static/site/apple-touch-icon.png  180 px, for phone home screens
    static/site/og-image.jpg          1200 x 630 preview card shown when a link is shared
    static/site/front-backdrop.webp   the preview's three-card fan alone, on clear ground, which the
                                      front page shows faint behind everything (index.html)

The preview is a sample question on the page green beside the three cards drawn for it
(past, present, future), fanned. It shows only the question and the cards, never a reading. The cards are the
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
PANEL = (167, 226, 192)     # #a7e2c0, the site's panel green, for the small label
LABEL = "A THREE-CARD READING"
QUESTION = "What is it that I would really like to know?"
TAGLINE = ["Past · Present · Future", "Ask your own question."]
FOOTER = "tarotthoth.com · free and open source"
PREVIEW_CARDS = ["3-of-cups---abundance.webp", "xix---the-sun.webp", "3-of-wands---virtue.webp"]

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
    """Wrap to `width`, then narrow it while the line count holds, so the lines come out
    even and the last one is never a lone word."""
    lines = _wrap(draw, text, fnt, width)
    while width > 100 and len(_wrap(draw, text, fnt, width - 10)) == len(lines):
        width -= 10
    return _wrap(draw, text, fnt, width)


def _wrap(draw, text, fnt, width):
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


def fan(im, cx, cy, height=380, shadow=True):
    """The three preview cards in cream frames, fanned about (cx, cy), each `height` px tall."""
    k = height / 380
    for i, name in enumerate(PREVIEW_CARDS):
        card = Image.open(STATIC / "cards" / "full" / name).convert("RGBA")
        card = card.resize((round(card.width * height / card.height), height), Image.LANCZOS)
        b = round(6 * k)
        framed = Image.new("RGBA", (card.width + 2 * b, card.height + 2 * b), (250, 246, 236, 255))
        framed.paste(card, (b, b))
        rotated = framed.rotate((1 - i) * 14, expand=True, resample=Image.BICUBIC)
        x = cx + round((i - 1) * 150 * k) - rotated.width // 2
        y = cy - rotated.height // 2 + (0 if i == 1 else round(25 * k))
        if shadow:
            with_shadow(im, rotated, x, y)
        else:
            im.alpha_composite(rotated, (x, y))


def backdrop():
    """The preview's fan alone on a clear ground; the front page fades it right down."""
    im = Image.new("RGBA", (760, 600), (0, 0, 0, 0))
    fan(im, 380, 285, height=440, shadow=False)
    return im


def preview():
    W, H = 1200, 630
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    for x in range(W):                              # the page green, darkening to the right
        t = x / (W - 1)
        d.line([(x, 0), (x, H)], fill=tuple(round(a + (b - a) * t) for a, b in zip(GREEN, DEEP_GREEN)))

    fan(im, 935, 320)                               # the three cards fanned on the right

    d = ImageDraw.Draw(im)
    d.text((72, 92), LABEL, font=font("sans", 20, 600), fill=PANEL)
    size = 44                                       # shrink a long question so it clears the tagline
    while size > 30 and len(wrap(d, QUESTION, font("serif", size, 700), 530)) > 4:
        size -= 2
    title_font = font("serif", size, 700)
    for k, line in enumerate(wrap(d, QUESTION, title_font, 530)):
        d.text((70, 135 + round(size * 1.27) * k), line, font=title_font, fill=CREAM)
    sub_font = font("sans", 28)
    for k, line in enumerate(TAGLINE):
        d.text((72, 400 + 40 * k), line, font=sub_font, fill=(255, 255, 255))
    d.text((72, 540), FOOTER, font=font("sans", 24, 500), fill=CREAM)
    return im.convert("RGB")


def main():
    icon(48).save(SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    icon(180, rounded=False).convert("RGB").save(SITE / "apple-touch-icon.png", optimize=True)
    preview().save(SITE / "og-image.jpg", quality=85, optimize=True, progressive=True)
    backdrop().save(SITE / "front-backdrop.webp", quality=50, method=6)
    for name in ("favicon.ico", "apple-touch-icon.png", "og-image.jpg", "front-backdrop.webp"):
        print(f"{name}: {(SITE / name).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
