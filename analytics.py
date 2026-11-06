"""Text analytics helpers: themes, tokenising, word statistics, word clouds and quote cards."""
from __future__ import annotations

import io
import re
import textwrap
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from wordcloud import STOPWORDS, WordCloud

# --------------------------------------------------------------------------------------
# Themes — curated keyword roots used to find uplifting / topical verses
# --------------------------------------------------------------------------------------
THEMES: dict[str, dict] = {
    "Love":        {"emoji": "❤️", "words": ["love", "loved", "loveth", "loving", "beloved", "affection", "compassion"]},
    "Peace":       {"emoji": "🕊️", "words": ["peace", "peaceful", "rest", "tranquil", "tranquility", "calm", "quiet"]},
    "Mercy":       {"emoji": "🤲", "words": ["mercy", "merciful", "compassionate", "gracious", "grace", "kindness", "lovingkindness"]},
    "Hope":        {"emoji": "🌅", "words": ["hope", "hoped", "promise", "trust", "expect", "wait upon"]},
    "Patience":    {"emoji": "⏳", "words": ["patience", "patient", "patiently", "endure", "endureth", "steadfast", "persevere"]},
    "Forgiveness": {"emoji": "🌿", "words": ["forgive", "forgiven", "forgiveness", "forgiving", "pardon", "repent", "repentance"]},
    "Wisdom":      {"emoji": "🦉", "words": ["wisdom", "wise", "understanding", "knowledge", "insight", "instruction"]},
    "Gratitude":   {"emoji": "🙏", "words": ["thank", "thanks", "thankful", "grateful", "gratitude", "praise", "bless"]},
    "Strength":    {"emoji": "🦁", "words": ["strength", "strong", "courage", "courageous", "mighty", "fear not", "be not afraid"]},
    "Justice":     {"emoji": "⚖️", "words": ["justice", "just", "righteous", "righteousness", "fair", "equity", "judgment"]},
    "Light":       {"emoji": "💡", "words": ["light", "lamp", "shine", "shineth", "bright", "radiant", "dawn"]},
    "Charity":     {"emoji": "🎁", "words": ["charity", "poor", "orphan", "orphans", "needy", "give", "alms", "widow"]},
    "Joy":         {"emoji": "😊", "words": ["joy", "joyful", "rejoice", "glad", "gladness", "delight", "happy"]},
    "Faith":       {"emoji": "🌟", "words": ["faith", "believe", "believers", "faithful", "belief", "trust"]},
    "Nature":      {"emoji": "🌳", "words": ["tree", "trees", "rain", "mountain", "mountains", "sea", "river", "garden", "stars", "sun", "moon"]},
}

ARCHAIC = {
    "thee", "thou", "thy", "thine", "ye", "unto", "hath", "hast", "shall", "shalt", "saith", "said",
    "upon", "also", "even", "yea", "lo", "behold", "art", "doth", "dost", "wilt", "therefore",
    "thereof", "wherefore", "whom", "came", "come", "went", "go", "now", "one", "will", "may",
    "made", "make", "let", "man", "men", "say", "says", "us", "o", "verily", "indeed", "among",
    "according", "therein", "say", "yet", "every", "day", "things", "thing", "away", "son", "sons",
    "hand", "put", "set", "took", "take", "give", "gave", "given", "brought", "bring", "know",
    "two", "three", "according", "begat", "s", "t", "neither", "nor", "surely", "certainly", "like",
    "except", "whoever", "whatever", "within", "used", "thus", "another", "already", "rather", "perhaps",
    "besides", "toward", "concerning", "cause", "see", "way", "ones", "forth", "upon", "said", "says",
}
BASE_STOP = {w.lower() for w in STOPWORDS} | {"and", "the", "of", "to", "that", "in", "he", "his",
                                              "they", "them", "is", "it", "for", "be", "which", "not",
                                              "with", "all", "was", "a", "i", "her", "she", "him"}

WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def stopwords(archaic: bool = True) -> set[str]:
    return BASE_STOP | ARCHAIC if archaic else BASE_STOP


def word_pattern(word: str, forms: bool) -> str:
    """Regex for a word or phrase. `forms` also matches simple inflections (love -> loved, loveth...)."""
    w = re.escape(word.strip().lower()).replace(r"\ ", r"\s+")
    return rf"\b{w}\w*" if forms else rf"\b{w}\b"


def theme_pattern(theme: str) -> str:
    return "|".join(rf"\b{re.escape(w)}\b" for w in THEMES[theme]["words"])


def theme_filter(df: pd.DataFrame, theme: str | None) -> pd.DataFrame:
    if not theme or theme == "Any":
        return df
    return df[df["text"].str.contains(theme_pattern(theme), case=False, regex=True)]


def nice_verses(df: pd.DataFrame, min_words: int = 8, max_words: int = 45) -> pd.DataFrame:
    """Verses that read well on their own: not too short, not too long, not genealogies."""
    m = df["n_words"].between(min_words, max_words)
    if "complete" in df:
        m &= df["complete"]  # only verses that are a whole sentence on their own
    m &= ~df["text"].str.contains(r"\bbegat\b|\bson of\b.*\bson of\b|\bcubits?\b", case=False, regex=True)
    return df[m]


def full_passage(version_df: pd.DataFrame, book: str, chapter: int, verse: int, limit: int = 6) -> dict:
    """Expand a verse to the whole sentence it belongs to (verses before/after in the same chapter).

    Returns {"text", "ref", "verses", "truncated"}; "ref" becomes a range like "Luke 17:3–4"."""
    chap = version_df[(version_df["book"] == book) & (version_df["chapter"] == chapter)].sort_values("verse")
    rows = chap.reset_index(drop=True)
    i = int(rows.index[rows["verse"] == verse][0])
    start = end = i
    while start > 0 and i - start < limit and not (rows.at[start, "starts"] and rows.at[start - 1, "ends"]):
        start -= 1
    while end < len(rows) - 1 and end - i < limit and not rows.at[end, "ends"]:
        end += 1
    part = rows.iloc[start:end + 1]
    truncated = not (rows.at[end, "ends"] and (start == 0 or rows.at[start - 1, "ends"]))
    first, last = part.iloc[0], part.iloc[-1]
    ref = first["ref"] if start == end else f"{first['ref']}–{last['verse']}"
    return {"text": " ".join(part["text"]), "ref": ref, "verses": len(part), "truncated": truncated,
            "first": int(first["verse"]), "last": int(last["verse"])}


# --------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------
def top_words(texts: pd.Series, n: int = 25, archaic: bool = True, min_len: int = 3) -> pd.DataFrame:
    stop = stopwords(archaic)
    c = Counter(t for txt in texts for t in tokenize(txt) if t not in stop and len(t) >= min_len)
    return pd.DataFrame(c.most_common(n), columns=["word", "count"])


def count_word(df: pd.DataFrame, word: str, forms: bool) -> pd.Series:
    return df["text"].str.lower().str.count(word_pattern(word, forms))


def per_10k(count: float, total_words: float) -> float:
    return 0.0 if total_words == 0 else count / total_words * 10_000


def word_by_book(df: pd.DataFrame, words: list[str], forms: bool) -> pd.DataFrame:
    """Long table: book, book_num, word, count, per10k."""
    totals = df.groupby(["book_num", "short_book"])["n_words"].sum()
    out = []
    for w in words:
        c = count_word(df, w, forms).groupby([df["book_num"], df["short_book"]]).sum()
        t = pd.DataFrame({"count": c, "total": totals}).reset_index()
        t["word"] = w
        t["per10k"] = t["count"] / t["total"] * 10_000
        out.append(t)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def cooccurring(df: pd.DataFrame, word: str, forms: bool, n: int = 20, archaic: bool = True) -> pd.DataFrame:
    hits = df[df["text"].str.contains(word_pattern(word, forms), case=False, regex=True)]
    stop = stopwords(archaic) | set(tokenize(word))
    root = word.lower().strip()
    c = Counter(t for txt in hits["text"] for t in set(tokenize(txt))
                if t not in stop and len(t) > 2 and not t.startswith(root))
    return pd.DataFrame(c.most_common(n), columns=["word", "verses"])


def lexical_summary(df: pd.DataFrame) -> dict:
    tokens = [t for txt in df["text"] for t in tokenize(txt)]
    return {
        "verses": len(df),
        "words": len(tokens),
        "unique": len(set(tokens)),
        "avg_len": float(df["n_words"].mean()) if len(df) else 0.0,
        "books": df["book"].nunique(),
    }


def sentiment_score(texts: pd.Series) -> pd.Series:
    """Tiny lexicon-based tone score: (positive - negative) words per verse."""
    pos = set(sum((THEMES[t]["words"] for t in ["Love", "Peace", "Mercy", "Hope", "Joy", "Gratitude", "Light"]), []))
    neg = {"wrath", "anger", "punishment", "destroy", "destroyed", "death", "die", "fire", "curse",
           "cursed", "evil", "wicked", "sin", "sins", "fear", "war", "slay", "slew", "torment", "hell",
           "woe", "sword", "blood", "plague", "grievous", "enemies", "enemy"}
    def score(txt):
        toks = tokenize(txt)
        return sum(t in pos for t in toks) - sum(t in neg for t in toks)
    return texts.map(score)


# --------------------------------------------------------------------------------------
# Word cloud
# --------------------------------------------------------------------------------------
def _font_candidates() -> list[str]:
    return [
        "C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/segoeui.ttf",
        "/Library/Fonts/Georgia.ttf", "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]


def find_font(bold: bool = False, italic: bool = False) -> str | None:
    names = []
    if italic:
        names += ["C:/Windows/Fonts/georgiai.ttf", "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"]
    if bold:
        names += ["C:/Windows/Fonts/georgiab.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
    for p in names + _font_candidates():
        if Path(p).exists():
            return p
    return None


def _shape_mask(shape: str, size: int = 900) -> np.ndarray | None:
    if shape == "Rectangle":
        return None
    img = Image.new("L", (size, size), 255)
    d = ImageDraw.Draw(img)
    if shape == "Circle":
        d.ellipse((20, 20, size - 20, size - 20), fill=0)
    elif shape == "Heart":
        t = np.linspace(0, 2 * np.pi, 400)
        x = 16 * np.sin(t) ** 3
        y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
        pts = [(size / 2 + xi * size / 36, size / 2.2 - yi * size / 36) for xi, yi in zip(x, y)]
        d.polygon(pts, fill=0)
    elif shape == "Star":
        cx = cy = size / 2
        pts = []
        for i in range(10):
            r = size * 0.48 if i % 2 == 0 else size * 0.2
            a = np.pi / 2 + i * np.pi / 5
            pts.append((cx + r * np.cos(a), cy - r * np.sin(a)))
        d.polygon(pts, fill=0)
    elif shape == "Arch":  # a mihrab / window-like arch
        d.rectangle((120, size * 0.42, size - 120, size - 30), fill=0)
        d.ellipse((120, 30, size - 120, size * 0.84), fill=0)
    return np.array(img)


def make_wordcloud(texts: pd.Series, colormap: str = "viridis", max_words: int = 150,
                   archaic: bool = True, shape: str = "Rectangle", dark: bool = False,
                   extra_stop: set[str] | None = None) -> Image.Image | None:
    stop = stopwords(archaic) | (extra_stop or set())
    freqs = Counter(t for txt in texts for t in tokenize(txt) if t not in stop and len(t) > 2)
    if not freqs:
        return None
    wc = WordCloud(
        width=1400, height=800, background_color="#0e1117" if dark else "white",
        colormap=colormap, max_words=max_words, mask=_shape_mask(shape), font_path=find_font(bold=True),
        prefer_horizontal=0.9, relative_scaling=0.45, margin=4, random_state=7,
        contour_width=0,
    ).generate_from_frequencies(freqs)
    return wc.to_image()


# --------------------------------------------------------------------------------------
# Quote card image
# --------------------------------------------------------------------------------------
CARD_STYLES = {
    "Dawn":     ("#ff9a8b", "#ff6a88", "#ffffff"),
    "Emerald":  ("#0f9d76", "#064e3b", "#fdf6e3"),
    "Royal":    ("#4263eb", "#1a1b4b", "#ffffff"),
    "Gold":     ("#f6d365", "#c0841a", "#2b1d05"),
    "Midnight": ("#232526", "#414345", "#f5e6c8"),
    "Lavender": ("#a18cd1", "#fbc2eb", "#2d1b46"),
}


def _font(path: str | None, size: int):
    if path:
        return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def quote_card(text: str, ref: str, style: str = "Royal", size: tuple[int, int] = (1080, 1080)) -> bytes:
    c1, c2, fg = CARD_STYLES[style]
    w, h = size
    top = np.array(Image.new("RGB", (1, 1), c1)).reshape(3)
    bot = np.array(Image.new("RGB", (1, 1), c2)).reshape(3)
    grad = np.linspace(0, 1, h)[:, None, None]
    arr = (top * (1 - grad) + bot * grad).astype(np.uint8)
    img = Image.fromarray(np.repeat(arr, w, axis=1))
    d = ImageDraw.Draw(img)

    # Fit text size to the card
    italic = find_font(italic=True)
    for fs in range(64, 22, -2):
        f = _font(italic, fs)
        wrap = textwrap.wrap(f"“{text}”", width=max(12, int(w / (fs * 0.52))))
        line_h = fs * 1.35
        if len(wrap) * line_h < h * 0.62:
            break
    block_h = len(wrap) * line_h
    y = (h - block_h) / 2 - 40
    for line in wrap:
        tw = d.textlength(line, font=f)
        d.text(((w - tw) / 2, y), line, font=f, fill=fg)
        y += line_h

    rf = _font(find_font(bold=True), 34)
    label = f"— {ref}"
    d.line(((w / 2 - 60), y + 30, (w / 2 + 60), y + 30), fill=fg, width=2)
    d.text(((w - d.textlength(label, font=rf)) / 2, y + 55), label, font=rf, fill=fg)
    small = _font(find_font(), 22)
    mark = "Sacred Words Explorer"
    d.text(((w - d.textlength(mark, font=small)) / 2, h - 60), mark, font=small, fill=fg)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
