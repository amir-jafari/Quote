"""
Shareable quote cards (1080 x 1350, the 4:5 portrait size social feeds show in full).

A card (JPEG) carries the English verse plus every extra text that is switched on in the sidebar (Persian, Spanish,
Arabic / Hebrew original). The "Scripture theme" background is drawn per scripture and varied per book:

  * Quran  -> deep emerald with a gold eight-pointed-star lattice and an ornamental gold frame
  * Bible  -> night blue with rays of light from above and soft glowing points
  * Torah  -> parchment between two scroll rollers

Each book (surah) gets its own shade and pattern layout, derived from its name, so a Genesis card and a
Psalms card look related but different. The older flat gradient styles remain available.

Right-to-left text: when Pillow has Raqm (HarfBuzz + FriBiDi) it shapes Persian, Arabic and Hebrew itself,
marks included. Otherwise letters are joined with arabic-reshaper and reordered with python-bidi; that path
drops vowel marks, which Pillow's basic layout can't position.
"""
from __future__ import annotations

import colorsys
import hashlib
import io
import math
import random
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

FONT_DIR = Path(__file__).parent / "fonts"
W, H = 1080, 1350
RAQM = features.check("raqm")

FONTS = {
    "en": "Lora-Italic.ttf",
    "es": "Lora-Italic.ttf",
    "fa": "Vazirmatn.ttf",
    "ar": "Amiri-Regular.ttf",
    "he": "NotoSerifHebrew.ttf",
    "title": "Cinzel.ttf",
    "ref": "Lora.ttf",
}
# Relative text size per language (English = 1)
SCALE = {"en": 1.0, "es": 0.82, "fa": 0.84, "ar": 1.0, "he": 0.9}
RTL = {"fa", "ar", "he"}

THEMED = "Scripture theme"
FLAT_STYLES = {
    "Dawn": ("#ff9a8b", "#ff6a88", "#ffffff"),
    "Emerald": ("#0f9d76", "#064e3b", "#fdf6e3"),
    "Royal": ("#4263eb", "#1a1b4b", "#ffffff"),
    "Gold": ("#f6d365", "#c0841a", "#2b1d05"),
    "Midnight": ("#232526", "#414345", "#f5e6c8"),
    "Lavender": ("#a18cd1", "#fbc2eb", "#2d1b46"),
}
STYLES = [THEMED] + list(FLAT_STYLES)

# Per scripture: base colours (top, bottom), text colour, accent (ornaments, reference)
THEMES = {
    "Quran": {"top": "#0d4a3a", "bottom": "#05231b", "fg": "#fbf5e6", "accent": "#d9b45a"},
    "Bible": {"top": "#1d2f6b", "bottom": "#0a0f2a", "fg": "#ffffff", "accent": "#f2d48a"},
    "Torah": {"top": "#f6e7c6", "bottom": "#e3c48b", "fg": "#3a2410", "accent": "#8a5a1c"},
}


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
@lru_cache(maxsize=256)
def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / FONTS[kind]), max(int(size), 8))


def _rgb(hex_: str) -> tuple[int, int, int]:
    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i:i + 2], 16) for i in (0, 2, 4))


def _shift(hex_: str, dh: float, dl: float = 0.0) -> tuple[int, int, int]:
    """Rotate the hue by dh (0-1) and lightness by dl."""
    r, g, b = (c / 255 for c in _rgb(hex_))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb((h + dh) % 1, min(max(l + dl, 0), 1), s)
    return int(r * 255), int(g * 255), int(b * 255)


def _seed(*parts: str) -> int:
    return int(hashlib.md5("|".join(parts).encode()).hexdigest()[:8], 16)


def _gradient(top, bottom, w=W, h=H) -> Image.Image:
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top) * (1 - t) + np.array(bottom) * t).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, w, axis=1), "RGB")


def _radial(img: Image.Image, color, center, radius, strength) -> Image.Image:
    """Soft glow (strength > 0) or vignette (strength < 0) around a point."""
    w, h = img.size
    y, x = np.ogrid[:h, :w]
    d = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 if strength > 0 else np.clip(d - 0.55, 0, 1) ** 1.5
    a = (a * abs(strength))[..., None]
    base = np.asarray(img).astype(np.float32)
    out = base * (1 - a) + np.array(color, np.float32) * a
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")


def _overlay(img: Image.Image, layer: Image.Image) -> Image.Image:
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# --------------------------------------------------------------------------------------
# Backgrounds
# --------------------------------------------------------------------------------------
def _star8(d: ImageDraw.ImageDraw, cx, cy, r, fill=None, outline=None, width=2):
    """Eight-pointed star (two overlapping squares), the classic khatam."""
    for rot in (0, math.pi / 4):
        pts = [(cx + r * math.cos(rot + k * math.pi / 2), cy + r * math.sin(rot + k * math.pi / 2)) for k in range(4)]
        d.polygon(pts, fill=fill, outline=outline, width=width)


def _bg_quran(rng: random.Random, t: dict, dh: float) -> Image.Image:
    img = _gradient(_shift(t["top"], dh), _shift(t["bottom"], dh))
    img = _radial(img, _shift(t["top"], dh, 0.12), (W / 2, H * 0.45), W * 0.75, 0.55)
    gold = _rgb(t["accent"])
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = rng.choice([108, 120, 135])
    ox, oy = rng.randrange(step), rng.randrange(step)
    for yy in range(-step, H + step, step):
        for xx in range(-step, W + step, step):
            cx, cy = xx + ox, yy + oy
            _star8(d, cx, cy, step * 0.34, outline=gold + (34,), width=2)
            _star8(d, cx + step / 2, cy + step / 2, step * 0.12, fill=gold + (26,))
            d.line((cx + step * 0.34, cy, cx + step * 0.66, cy), fill=gold + (20,), width=1)
            d.line((cx, cy + step * 0.34, cx, cy + step * 0.66), fill=gold + (20,), width=1)
    img = _overlay(img, layer)
    # keep the pattern quiet behind the text
    img = _radial(img, _shift(t["bottom"], dh, 0.02), (W / 2, H / 2), W * 0.62, 0.65)

    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    for inset, wd in ((38, 3), (52, 1)):
        d.rectangle((inset, inset, W - inset, H - inset), outline=gold + (230,), width=wd)
    for cx, cy in ((45, 45), (W - 45, 45), (45, H - 45), (W - 45, H - 45)):
        _star8(d, cx, cy, 22, fill=_shift(t["bottom"], dh) + (255,), outline=gold + (255,), width=2)
        _star8(d, cx, cy, 8, fill=gold + (255,))
    # small stars along the top and bottom edges of the frame
    for cx in (W / 2 - 120, W / 2, W / 2 + 120):
        for cy in (45, H - 45):
            _star8(d, cx, cy, 10 if cx == W / 2 else 6, fill=gold + (255,))
    return _overlay(img, frame)


def _bg_bible(rng: random.Random, t: dict, dh: float) -> Image.Image:
    img = _gradient(_shift(t["top"], dh), _shift(t["bottom"], dh))
    src = (W / 2 + rng.uniform(-120, 120), -80)
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(rays)
    n = rng.randint(9, 13)
    for k in range(n):
        ang = math.pi / 2 + (k - (n - 1) / 2) * (1.5 / n) + rng.uniform(-0.04, 0.04)
        spread = rng.uniform(0.025, 0.06)
        far = H * 1.6
        p1 = (src[0] + far * math.cos(ang - spread), src[1] + far * math.sin(ang - spread))
        p2 = (src[0] + far * math.cos(ang + spread), src[1] + far * math.sin(ang + spread))
        d.polygon([src, p1, p2], fill=(255, 240, 200, rng.randint(14, 30)))
    img = _overlay(img, rays.filter(ImageFilter.GaussianBlur(18)))
    img = _radial(img, (255, 236, 190), (src[0], 40), W * 0.7, 0.45)
    bokeh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(bokeh)
    for _ in range(46):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.choice([2, 3, 4, 6, 10, 16])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 245, 220, rng.randint(25, 90) if r < 6 else rng.randint(12, 30)))
    img = _overlay(img, bokeh.filter(ImageFilter.GaussianBlur(2)))
    img = _radial(img, (0, 0, 0), (W / 2, H / 2), W * 0.95, -0.55)
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((40, 40, W - 40, H - 40), radius=26, outline=(242, 212, 138, 150), width=2)
    return _overlay(img, frame)


def _bg_torah(rng: random.Random, t: dict, dh: float) -> Image.Image:
    img = _gradient(_shift(t["top"], dh * 0.4), _shift(t["bottom"], dh * 0.4))
    # parchment grain and blotches
    nprng = np.random.default_rng(rng.randrange(2 ** 31))
    noise = nprng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    noise = np.asarray(Image.fromarray(((noise * 18) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC))
    grain = nprng.normal(0, 6, (H, W)).astype(np.float32)
    arr = np.asarray(img).astype(np.float32) + ((noise.astype(np.float32) - 128) * 0.35 + grain)[..., None]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")
    img = _radial(img, (120, 72, 25), (W / 2, H / 2), W * 0.9, -0.6)
    # scroll rollers top and bottom
    wood = _shift("#5b3412", dh * 0.3)
    gold = _rgb("#c99a3e")
    for y0 in (0, H - 86):
        roll = _gradient(_shift("#7a4a1e", dh * 0.3, 0.08), wood, W, 86)
        img.paste(roll, (0, y0))
        d = ImageDraw.Draw(img)
        d.line((0, y0 + 6, W, y0 + 6), fill=_shift("#a8703a", 0, 0.05), width=3)
        d.line((0, y0 + 80, W, y0 + 80), fill=(40, 22, 8), width=4)
        for x in (40, W - 40):
            d.rounded_rectangle((x - 26, y0 - 4, x + 26, y0 + 90), radius=12, fill=gold, outline=(110, 75, 20), width=3)
            d.ellipse((x - 12, y0 + 31, x + 12, y0 + 55), fill=(240, 205, 120))
    # thin column border
    d = ImageDraw.Draw(img)
    d.line((84, 112, 84, H - 112), fill=_rgb(t["accent"]), width=2)
    d.line((W - 84, 112, W - 84, H - 112), fill=_rgb(t["accent"]), width=2)
    return img


@lru_cache(maxsize=64)
def themed_background(scripture: str, book: str) -> Image.Image:
    t = THEMES[scripture]
    rng = random.Random(_seed(scripture, book))
    dh = rng.uniform(-0.05, 0.05)  # each book gets its own shade within the scripture's family
    draw = {"Quran": _bg_quran, "Bible": _bg_bible, "Torah": _bg_torah}[scripture]
    return draw(rng, t, dh)


def flat_background(style: str) -> Image.Image:
    c1, c2, _ = FLAT_STYLES[style]
    return _gradient(_rgb(c1), _rgb(c2))


# --------------------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------------------
_AR_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۜ۟-۪ۨ-ۭ࣓-ࣿ]")
_HE_MARKS = re.compile("[֑-ׇֽֿׁׂׅׄ]")


def _prep(text: str, lang: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if RAQM or lang not in RTL:
        return text
    return _HE_MARKS.sub("", text) if lang == "he" else _AR_MARKS.sub("", text)


def _visual(line: str, lang: str) -> str:
    """Logical -> drawable string (only needed without Raqm)."""
    if RAQM or lang not in RTL:
        return line
    from bidi.algorithm import get_display
    if lang in ("fa", "ar"):
        import arabic_reshaper
        line = arabic_reshaper.reshape(line)
    return get_display(line)


def _draw_kwargs(lang: str) -> dict:
    if RAQM and lang in RTL:
        return {"direction": "rtl", "language": {"fa": "fa", "ar": "ar", "he": "he"}[lang]}
    return {}


def _width(f, line: str, lang: str) -> float:
    return f.getlength(_visual(line, lang), **_draw_kwargs(lang))


def _wrap(text: str, f, lang: str, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        cand = f"{cur} {word}".strip()
        if cur and _width(f, cand, lang) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def _truncate(text: str, n_words: int) -> str:
    words = text.split(" ")
    return text if len(words) <= n_words else " ".join(words[:n_words]) + " …"


def _layout(blocks, base: float, max_w: float, limit: int | None):
    out = []
    for lang, text in blocks:
        size = int(base * SCALE[lang])
        f = font(lang, size)
        body = _truncate(text, limit) if limit else text
        if lang in ("en", "es"):
            body = f"“{body}”"
        lines = _wrap(body, f, lang, max_w)
        lh = size * (1.75 if lang in ("fa", "ar") else 1.62 if lang == "he" else 1.38)
        out.append((lang, f, lines, lh))
    return out


def _diamond(d, cx, cy, color, r=6):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=color)
    d.line((cx - 70, cy, cx - 14, cy), fill=color, width=1)
    d.line((cx + 14, cy, cx + 70, cy), fill=color, width=1)


def quote_card(blocks: list[tuple[str, str]], ref: str, scripture: str, book: str,
               style: str = THEMED, sources: str = "") -> bytes:
    """blocks: [(lang, text), ...] with lang in en / es / fa / ar / he; English first."""
    if style == THEMED:
        img = themed_background(scripture, book).copy()
        t = THEMES[scripture]
        fg, accent = _rgb(t["fg"]), _rgb(t["accent"])
    else:
        img = flat_background(style)
        fg = accent = _rgb(FLAT_STYLES[style][2])
    d = ImageDraw.Draw(img)

    title_y = 150 if style == THEMED and scripture == "Torah" else 128
    title = re.sub(r"^\d+\.\s*", "", book).upper()
    m = re.match(r"^(.*?)\s*\((.*)\)$", title)
    if m and m.group(1) == m.group(2):  # e.g. "LUQMAN (LUQMAN)"
        title = m.group(1)
    title = f"SURAH {title}" if scripture == "Quran" else title
    tf = font("title", 30)
    while tf.getlength(title) > W - 260 and tf.size > 18:
        tf = font("title", tf.size - 2)
    tw = tf.getlength(title)
    d.text(((W - tw) / 2, title_y), title, font=tf, fill=accent)
    cy = title_y + tf.size * 0.62
    for side in (-1, 1):
        x = W / 2 + side * (tw / 2 + 34)
        if style == THEMED and scripture == "Quran":
            _star8(d, x, cy, 9, fill=accent)
        else:
            d.polygon([(x, cy - 6), (x + 6, cy), (x, cy + 6), (x - 6, cy)], fill=accent)

    ry = H - (222 if scripture == "Torah" and style == THEMED else 185)  # reference line
    top, bottom = title_y + 90, ry - 48
    avail, max_w = bottom - top, W - 2 * 150
    blocks = [(lang, _prep(text, lang)) for lang, text in blocks if text and text.strip()]
    gap = 58

    # Largest text size that fits; if even the smallest doesn't, shorten the texts
    chosen = None
    for limit in (None, 120, 80, 55, 38, 26):
        for base in range(56, 23, -2):
            lay = _layout(blocks, base, max_w, limit)
            total = sum(len(lines) * lh for _, _, lines, lh in lay) + gap * (len(lay) - 1)
            if total <= avail:
                chosen = (lay, total)
                break
        if chosen:
            break
    if not chosen:
        lay = _layout(blocks, 24, max_w, 20)
        chosen = (lay, sum(len(lines) * lh for _, _, lines, lh in lay) + gap * (len(lay) - 1))
    lay, total = chosen

    y = top + (avail - total) / 2
    for i, (lang, f, lines, lh) in enumerate(lay):
        if i:
            _diamond(d, W / 2, y + gap / 2 - lh * 0.12, accent)
            y += gap
        color = fg if lang == "en" else tuple(int(c * 0.92 + a * 0.08) for c, a in zip(fg, accent))
        for line in lines:
            vis = _visual(line, lang)
            kw = _draw_kwargs(lang)
            lw = f.getlength(vis, **kw)
            d.text(((W - lw) / 2, y), vis, font=f, fill=color, **kw)
            y += lh

    rf = font("ref", 36)
    label = f"— {ref}"
    d.text(((W - rf.getlength(label)) / 2, ry), label, font=rf, fill=accent)
    if sources:
        sf = font("ref", 21)
        while sf.getlength(sources) > W - 220 and sf.size > 13:
            sf = font("ref", sf.size - 1)
        d.text(((W - sf.getlength(sources)) / 2, ry + 52), sources, font=sf, fill=fg)
    mf = font("title", 18)
    mark = "SACRED WORDS EXPLORER"
    d.text(((W - mf.getlength(mark)) / 2, H - (118 if scripture == "Torah" and style == THEMED else 95)),
           mark, font=mf, fill=accent)

    # JPEG: a fraction of the PNG size (the parchment grain and light rays compress badly as PNG), so cards
    # load fast and attach to emails easily. 4:4:4 chroma keeps the small coloured text crisp.
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=86, subsampling=0, optimize=True, progressive=True)
    return buf.getvalue()
