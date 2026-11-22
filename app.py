"""
📜 Sacred Words Explorer
Read, search, discover and visualise the Quran, the Bible and the Torah — in English, with optional
Persian and Spanish translations and the Arabic / Hebrew originals.

Run:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import html
import random
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import analytics as an
import originals as orig
import companions as comp
import quote_cards as qc
from data_loader import CATALOG, DEFAULT_VERSION, NEW_TESTAMENT, load_version

# Webster Bible / Ali Quli Qarai are the default Bible / Quran translations. Set here as well as
# in data_loader.py so a running deployment that still holds an older copy of data_loader picks it up.
DEFAULT_VERSION = {**DEFAULT_VERSION, "Bible": "Webster Bible", "Quran": "Ali Quli Qarai"}

# Full-width buttons: `width="stretch"` on current Streamlit, `use_container_width` on older installs
import inspect as _inspect
STRETCH = ({"width": "stretch"} if "width" in _inspect.signature(st.button).parameters
           else {"use_container_width": True})

st.set_page_config(page_title="Sacred Words Explorer", page_icon="📜", layout="wide",
                   initial_sidebar_state="expanded")


SCRIPTURES = list(CATALOG)
COLORS = {s: CATALOG[s]["color"] for s in SCRIPTURES}
# Validated categorical order for multi-word charts (fixed order, never cycled)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MAX_WORDS = len(SERIES)

# --------------------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600;700&family=Amiri+Quran&family=Amiri:wght@400;700&family=Noto+Serif+Hebrew:wght@400;500&family=Vazirmatn:wght@400;500&display=swap" rel="stylesheet">
<style>
:root { --card-bg: rgba(127,127,127,0.06); --card-border: rgba(127,127,127,0.18); --muted: rgba(127,127,127,0.95); }
html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.6rem; max-width: 1350px; }
.hero {
  border-radius: 22px; padding: 30px 36px; margin-bottom: 18px; color: #fff;
  background: radial-gradient(1200px 400px at 10% -20%, rgba(255,255,255,.25), transparent),
              linear-gradient(120deg, #0f9d76 0%, #4263eb 50%, #d08c16 100%);
  box-shadow: 0 12px 40px rgba(66,99,235,.25);
}
.hero h1 { font-family: 'Cormorant Garamond', serif; font-size: 3rem; margin: 0; line-height: 1.05; color:#fff; }
.hero p { margin: 6px 0 0; opacity: .92; font-size: 1.05rem; }
.hero .chips span { display:inline-block; margin: 12px 8px 0 0; padding: 4px 12px; border-radius: 999px;
  background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.35); font-size: .85rem; }
a.dl-btn { padding: 8px 16px; border-radius: 8px; border: 1px solid rgba(127,127,127,.35);
  text-decoration: none !important; color: inherit !important; font-weight: 500; margin: 4px 0 10px; }
a.dl-btn:hover { border-color: #ff4b4b; color: #ff4b4b !important; }
.verse-card {
  background: var(--card-bg); border: 1px solid var(--card-border); border-left: 6px solid var(--accent);
  border-radius: 16px; padding: 18px 22px; margin: 8px 0 6px;
}
.verse-card .txt { font-family: 'Cormorant Garamond', serif; font-size: 1.35rem; line-height: 1.5; }
.verse-card.big { padding: 34px 40px; border-left-width: 8px; }
.verse-card.big .txt { font-size: 2.05rem; line-height: 1.4; }
.verse-card .ref { margin-top: 10px; font-weight: 600; color: var(--accent); letter-spacing: .02em; }
.verse-card .meta { font-size: .8rem; color: var(--muted); margin-top: 2px; }
.badge { display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 600;
  color: #fff; background: var(--accent); margin-right: 6px; }
.reader { font-family: 'Cormorant Garamond', serif; font-size: 1.28rem; line-height: 1.75;
  background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 22px 30px; }
.reader sup { font-family: 'Inter', sans-serif; font-size: .68rem; color: var(--accent); font-weight: 700; margin-right: 3px; }
.orig { direction: rtl; text-align: right; margin-top: 14px; padding-top: 12px;
  border-top: 1px dashed var(--card-border); font-size: 1.6rem; line-height: 2.15; }
.orig.ar { font-family: 'Amiri Quran', 'Amiri', 'Noto Naskh Arabic', serif; }
.orig.he { font-family: 'Noto Serif Hebrew', 'SBL Hebrew', 'Times New Roman', serif; font-size: 1.5rem; line-height: 1.95; }
.orig.es { direction: ltr; text-align: left; font-family: 'Cormorant Garamond', serif; font-size: 1.25rem; line-height: 1.5; }
.olabel.es { text-align: left; }
.orig.fa { font-family: 'Vazirmatn', 'Noto Naskh Arabic', Tahoma, sans-serif; font-size: 1.15rem; line-height: 2; }
.verse-card.big .orig { font-size: 2.15rem; }
.verse-card.big .orig.fa { font-size: 1.5rem; }
.verse-card.big .orig.es { font-size: 1.7rem; line-height: 1.4; }
.olabel { font-size: .74rem; color: var(--muted); text-align: right; margin-top: 2px; }
.rgrid { display: grid; grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); column-gap: 28px; }
.rgrid > div { padding: 9px 0; border-bottom: 1px solid var(--card-border); }
.rgrid .head { font-family: 'Inter', sans-serif; font-size: .78rem; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: .05em; border-bottom: 2px solid var(--accent); }
.rgrid .orig { margin: 0; padding: 9px 0; border-top: none; font-size: 1.45rem; line-height: 1.9; }
.rgrid .orig.fa { font-size: 1.1rem; line-height: 1.95; }
.rgrid .orig.es { font-size: 1.2rem; line-height: 1.6; }
.rgrid > div.tgt, .reader span.tgt { background: rgba(255, 200, 0, .16); }
@media (max-width: 760px) { .rgrid { grid-template-columns: 1fr; } .rgrid .head { display: none; } }
mark { background: rgba(255, 200, 0, .45); padding: 0 2px; border-radius: 4px; color: inherit; }
.stat { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px 18px; }
.stat .v { font-size: 1.7rem; font-weight: 700; }
.stat .l { font-size: .8rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
div[data-testid="stTabs"] button p { font-size: 1.02rem; font-weight: 600; }
section[data-testid="stSidebar"] .sb-title { font-family: 'Cormorant Garamond', serif; font-size: 1.7rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading scripture…")
def get(scripture: str, version: str) -> pd.DataFrame:
    return load_version(scripture, version)


@st.cache_data(show_spinner="Loading all three scriptures…")
def get_defaults() -> pd.DataFrame:
    return pd.concat([get(s, DEFAULT_VERSION[s]) for s in SCRIPTURES], ignore_index=True)


@st.cache_data(show_spinner=False)
def nice_pool(scripture: str, version: str) -> pd.DataFrame:
    return an.nice_verses(get(scripture, version))


@st.cache_data(show_spinner="Building word cloud…")
def cached_cloud(texts: tuple, **kw) -> bytes | None:
    import io
    img = an.make_wordcloud(pd.Series(texts), **kw)
    if img is None:
        return None
    buf = io.BytesIO()
    # a 256-colour palette looks the same for a word cloud and is about a third of the size
    img.convert("RGB").quantize(colors=256).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# Images and downloads are embedded in the page as base64 data URIs instead of going
# through Streamlit's /media endpoint, which is unreachable on some Streamlit Cloud
# setups (broken images, downloads failing with a "<hash>.txt ... Site wasn't available").
def show_png(png: bytes, width: int | None = None, target=st) -> None:
    import base64
    w = f"{width}px" if width else "100%"
    target.markdown(f'<img src="data:image/png;base64,{base64.b64encode(png).decode()}" '
                    f'style="width:{w};max-width:100%;border-radius:10px;">', unsafe_allow_html=True)


def download_link(label: str, data: bytes, file_name: str, mime: str, target=st, full_width: bool = False) -> None:
    import base64
    style = "display:block;text-align:center;" if full_width else "display:inline-block;"
    target.markdown(
        f'<a class="dl-btn" style="{style}" download="{html.escape(file_name, quote=True)}" '
        f'href="data:{mime};base64,{base64.b64encode(data).decode()}">{html.escape(label)}</a>',
        unsafe_allow_html=True)


@st.cache_data(show_spinner="Computing statistics…")
def cached_summary(scripture: str, version: str, section: str, book: str) -> dict:
    return an.lexical_summary(filter_scope(get(scripture, version), section, book))


@st.cache_data(show_spinner=False)
def quote_jpg(blocks: tuple, ref: str, scripture: str, book: str, style: str, sources: str) -> bytes:
    return qc.quote_card(list(blocks), ref, scripture, book, style, sources)


@st.cache_data(show_spinner=False)
def theme_table() -> pd.DataFrame:
    alld = get_defaults()
    rows = []
    lc = alld["text"].str.lower()  # lowercase once: much faster than 15 case-insensitive scans
    for t in an.THEMES:
        m = lc.str.contains(an.theme_pattern(t), regex=True)
        for s, g in m.groupby(alld["scripture"]):
            rows.append({"theme": t, "scripture": s, "per1000": g.mean() * 1000})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner="Counting words…")
def cross_counts(words: tuple, forms: bool) -> pd.DataFrame:
    alld = get_defaults()
    rows = []
    for s in SCRIPTURES:
        d = alld[alld.scripture == s]
        total = d["n_words"].sum()
        for w in words:
            c = int(an.count_word(d, w, forms).sum())
            rows.append({"scripture": s, "word": w, "count": c, "per10k": an.per_10k(c, total)})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def by_book(scripture: str, version: str, section: str, words: tuple, forms: bool) -> pd.DataFrame:
    return an.word_by_book(filter_scope(get(scripture, version), section, "All books"), list(words), forms)


@st.cache_data(show_spinner=False)
def cooc(scripture: str, version: str, section: str, book: str, focus: str, forms: bool) -> pd.DataFrame:
    return an.cooccurring(filter_scope(get(scripture, version), section, book), focus, forms, n=15)


@st.cache_data(show_spinner="Comparing translations…")
def translation_counts(scripture: str, section: str, book: str, focus: str, forms: bool) -> pd.DataFrame:
    rows = []
    for v in CATALOG[scripture]["versions"]:
        vd = filter_scope(get(scripture, v), section, book)
        c = int(an.count_word(vd, focus, forms).sum())
        rows.append({"version": v, "per10k": an.per_10k(c, vd["n_words"].sum()), "count": c})
    return pd.DataFrame(rows).sort_values("per10k")


@st.cache_data(show_spinner=False)
def top_words_c(scripture: str, version: str, section: str, book: str) -> pd.DataFrame:
    return an.top_words(filter_scope(get(scripture, version), section, book)["text"], 20)


@st.cache_data(show_spinner=False)
def tone_c(scripture: str, version: str, section: str) -> pd.DataFrame:
    sc = filter_scope(get(scripture, version), section, "All books")
    tone = (sc.assign(tone=an.sentiment_score(sc["text"])).groupby(["book_num", "short_book"])
            .agg(tone=("tone", "sum"), words=("n_words", "sum")).reset_index())
    tone["per1k"] = tone["tone"] / tone["words"] * 1000
    return tone


@st.cache_data(show_spinner=False)
def length_quantiles() -> pd.DataFrame:
    """Box-plot statistics per scripture (Tukey whiskers), so the chart doesn't ship ~60,000 raw values."""
    alld = get_defaults()
    rows = []
    for s in SCRIPTURES:
        x = alld.loc[alld.scripture == s, "n_words"]
        q1, med, q3 = x.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        rows.append({"scripture": s, "q1": q1, "median": med, "q3": q3, "mean": x.mean(),
                     "lo": x[x >= q1 - 1.5 * iqr].min(), "hi": x[x <= q3 + 1.5 * iqr].max()})
    return pd.DataFrame(rows)


def filter_scope(df: pd.DataFrame, section: str, book: str) -> pd.DataFrame:
    if section != "All sections":
        df = df[df["section"] == section]
    if book != "All books":
        df = df[df["book"] == book]
    return df


def ss_init():
    st.session_state.setdefault("favs", [])
    st.session_state.setdefault("pick", None)
    st.session_state.setdefault("trio", None)


ss_init()


# --------------------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------------------
def highlight(text: str, pattern: str | None) -> str:
    safe = html.escape(text)
    if not pattern:
        return safe
    try:
        return re.sub(f"({pattern})", r"<mark>\1</mark>", safe, flags=re.IGNORECASE)
    except re.error:
        return safe


@st.cache_data(show_spinner=False)
def passage_c(scripture: str, version: str, book: str, chapter: int, verse: int) -> dict:
    return an.full_passage(get(scripture, version), book, int(chapter), int(verse))


@st.cache_resource(show_spinner="Loading the Arabic and Hebrew originals…")
def originals_data():
    return orig.load_arabic(), orig.load_hebrew()


@st.cache_resource(show_spinner=False)
def heb_map(scripture: str, version: str):
    return orig.hebrew_lookup(orig.source_code(scripture, version))


_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_CANTILLATION = re.compile("[\u0591-\u05AF\u034F]")
_POINTS = re.compile("[\u05B0-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]")


def hebrew_marks(text: str) -> str:
    mode = st.session_state.get("heb_marks", "Vowels only")
    if mode != "Vowels & cantillation":
        text = _CANTILLATION.sub("", text)
    if mode == "Consonants only":
        text = _POINTS.sub("", text)
    return text


def _ref_span(refs: list[tuple[int, int]]) -> str:
    (c1, v1), (c2, v2) = refs[0], refs[-1]
    if len(refs) == 1:
        return f"{c1}:{v1}"
    return f"{c1}:{v1}–{v2}" if c1 == c2 else f"{c1}:{v1}–{c2}:{v2}"


def original_for(row) -> dict | None:
    """Original-language text for a verse (or a joined passage).
    Returns {"text", "lang", "label"}; a dict with only "label" when there is no original to show."""
    if not st.session_state.get("show_orig", False) or "chapter" not in row:
        return None
    ar, he = originals_data()
    first, last = int(row.get("verse_first", row["verse"])), int(row.get("verse_last", row["verse"]))
    chapter = int(row["chapter"])
    if row["scripture"] == "Quran":
        parts = [f"{ar[(chapter, v)]} ﴿{str(v).translate(_AR_DIGITS)}﴾" for v in range(first, last + 1)
                 if (chapter, v) in ar]
        return {"text": " ".join(parts), "lang": "ar", "label": orig.ARABIC_LABEL} if parts else None
    if row["book"] in NEW_TESTAMENT:
        return {"label": "The New Testament was written in Greek. Hebrew originals cover the Old Testament."}
    code = orig.source_code(row["scripture"], row["version"])
    if code in orig.NO_HEBREW:
        return {"label": orig.NO_HEBREW[code]}
    lookup = heb_map(row["scripture"], row["version"])
    refs = [r for v in range(first, last + 1) for r in lookup.get((row["book"], chapter, v), [])]
    refs = list(dict.fromkeys(refs))
    if not refs:
        return {"label": "No Hebrew original for this verse (not in the Hebrew Bible)."}
    text = " ".join(hebrew_marks(he[(row["book"], c, v)]) for c, v in refs)
    label = orig.HEBREW_LABEL
    if refs != [(chapter, v) for v in range(first, last + 1)]:
        label += f" · Hebrew numbering {row['book']} {_ref_span(refs)}"
    return {"text": text, "lang": "he", "label": label}


@st.cache_resource(show_spinner="Loading the translation…")
def companion_quran(lang: str, name: str):
    return comp.load_quran(lang, name)


@st.cache_resource(show_spinner="Loading the translation…")
def companion_bible(lang: str):
    return comp.load_bible(lang)


@st.cache_resource(show_spinner=False)
def kjv_from_hebrew():
    return comp.hebrew_to_kjv(orig.hebrew_lookup("KJV"))


def lang_on(lang: str) -> bool:
    return st.session_state.get(f"show_{comp.LANGS[lang]['code']}", True)


def active_langs() -> list[str]:
    return [lang for lang in comp.LANGS if lang_on(lang)]


def companion_for(row, lang: str, force: bool = False) -> dict | None:
    """Persian / Spanish translation of a verse (or a joined passage), when its sidebar toggle is on (or forced,
    e.g. when searching in that language). Returns {"text", "lang", "label"}; only "label" when there is none."""
    if not (force or lang_on(lang)) or "chapter" not in row:
        return None
    meta = comp.LANGS[lang]
    digits = str.maketrans("0123456789", meta["digits"])
    first, last = int(row.get("verse_first", row["verse"])), int(row.get("verse_last", row["verse"]))
    chapter = int(row["chapter"])
    if row["scripture"] == "Quran":
        name = st.session_state.get(f"quran_{meta['code']}", meta["default_quran"])
        tr = companion_quran(lang, name)
        many = last > first
        parts = [tr[(chapter, v)] + (f" ({str(v).translate(digits)})" if many else "")
                 for v in range(first, last + 1) if (chapter, v) in tr]
        return ({"text": " ".join(parts), "lang": meta["code"], "label": comp.quran_label(lang, name)}
                if parts else None)
    code = orig.source_code(row["scripture"], row["version"])
    if code in comp.NO_PAIRING:
        return {"label": comp.NOT_PAIRED.format(lang=lang)}
    book = row["book"]
    if code in comp.HEBREW_NUMBERED:
        # JPS verse -> Hebrew verse(s) -> English (KJV) verse(s), the numbering these Bibles follow
        heb = heb_map(row["scripture"], row["version"])
        back = kjv_from_hebrew()
        refs = [k for v in range(first, last + 1) for h in heb.get((book, chapter, v), [])
                for k in back.get((book, *h), [])]
        refs = list(dict.fromkeys(refs)) or [(chapter, v) for v in range(first, last + 1)]
    else:
        refs = [(chapter, v) for v in range(first, last + 1)]
    bible = companion_bible(lang)
    refs = [r for r in refs if (book, *r) in bible]
    if not refs:
        return {"label": meta["missing"]}
    many = len(refs) > 1
    text = " ".join(bible[(book, c, v)] + (f" ({str(v).translate(digits)})" if many else "") for c, v in refs)
    label = meta["bible_label"]
    if refs != [(chapter, v) for v in range(first, last + 1)]:
        label += f" · English numbering {book} {_ref_span(refs)}"
    return {"text": text, "lang": meta["code"], "label": label}


@st.cache_resource(show_spinner=False)
def from_hebrew(scripture: str, version: str):
    """(book, Hebrew chapter, Hebrew verse) -> that version's (chapter, verse) list."""
    return comp.hebrew_to_kjv(heb_map(scripture, version))


def numbering(scripture: str, version: str) -> str:
    if scripture == "Quran":
        return "quran"
    code = orig.source_code(scripture, version)
    return "hebrew" if code in orig.HEBREW_NUMBERED else "vulgate" if code in orig.NO_HEBREW else "english"


def aligned_refs(scripture: str, src: str, dst: str, book: str, chapter: int, verse: int) -> list[tuple[int, int]]:
    """Where verse `chapter:verse` of version `src` is in version `dst`. JPS 1917 uses the Hebrew numbering and the
    English Bibles the English one (e.g. JPS Genesis 32:1 = KJV Genesis 31:55), so they are matched through the
    Hebrew text. Douay-Rheims (Vulgate numbering) has no mapping and keeps the same numbers."""
    a, b = numbering(scripture, src), numbering(scripture, dst)
    if a == b or "vulgate" in (a, b):
        return [(chapter, verse)]
    back = from_hebrew(scripture, dst)
    refs = [r for h in heb_map(scripture, src).get((book, chapter, verse), []) for r in back.get((book, *h), [])]
    return list(dict.fromkeys(refs)) or [(chapter, verse)]


def companions_html(row, patterns: dict | None = None) -> str:
    """The active translations under a verse; `patterns` ({lang: regex}) also shows and highlights a language
    that is searched in even when its toggle is off."""
    patterns = patterns or {}
    langs = active_langs() + [lang for lang in patterns if lang not in active_langs()]
    return "".join(original_html(companion_for(row, lang, force=True), patterns.get(lang)) for lang in langs)


def card_jpg(row, style: str = qc.THEMED) -> bytes:
    """Quote card with the English plus every translation switched on in the sidebar (and the original)."""
    blocks, sources = [("en", row["text"])], [row["version"]]
    for lang in active_langs():
        c = companion_for(row, lang)
        if c and c.get("text"):
            blocks.append((c["lang"], c["text"]))
            meta = comp.LANGS[lang]
            sources.append(st.session_state.get(f"quran_{meta['code']}", meta["default_quran"])
                           if row["scripture"] == "Quran" else meta["bible_short"])
    o = original_for(row)
    if o and o.get("text"):
        blocks.append((o["lang"], o["text"]))
        sources.append("Arabic original" if o["lang"] == "ar" else "Hebrew original")
    return quote_jpg(tuple(blocks), row["ref"], row["scripture"], row["book"], style, " · ".join(sources))


def text_dir(lang: str) -> str:
    return "ltr" if lang == "es" else "rtl"


def original_html(o: dict | None, pattern: str | None = None) -> str:
    if not o:
        return ""
    body = (f'<div class="orig {o["lang"]}" lang="{o["lang"]}" dir="{text_dir(o["lang"])}">'
            f'{highlight(o["text"], pattern)}</div>' if o.get("text") else "")
    return body + f'<div class="olabel {o.get("lang", "")}">{html.escape(o["label"])}</div>'


def as_sentence(row) -> dict:
    """Return the verse itself if it is a whole sentence, otherwise the full sentence spanning
    the neighbouring verses (e.g. Genesis 5:22 -> Genesis 5:21–24)."""
    row = dict(row)
    if row.get("complete", True) or "chapter" not in row:
        return row
    p = passage_c(row["scripture"], row["version"], row["book"], row["chapter"], row["verse"])
    if p["verses"] > 1:
        row.update(text=p["text"] + (" …" if p["truncated"] else ""), ref=p["ref"],
                   expanded=p["verses"], complete=True, verse_first=p["first"], verse_last=p["last"])
    return row


def verse_html(row, big: bool = False, pattern: str | None = None, show_version: bool = True,
               with_original: bool = True, comp_patterns: dict | None = None) -> str:
    color = COLORS[row["scripture"]]
    icon = CATALOG[row["scripture"]]["icon"]
    meta = f"{row['version']} · {row['section']}" if show_version else row["section"]
    if row.get("expanded"):
        meta += f" · full sentence across {row['expanded']} verses"
    elif row.get("complete") is False:
        meta += " · ↪ sentence continues in the next verse"
    return (f'<div class="verse-card {"big" if big else ""}" style="--accent:{color}">'
            f'<div class="txt">{highlight(row["text"], pattern)}</div>'
            f'<div class="ref">{icon} {html.escape(row["ref"])}</div>'
            f'<div class="meta">{html.escape(meta)}</div>'
            + (companions_html(row, comp_patterns) + original_html(original_for(row)) if with_original else "")
            + "</div>")


def add_fav(row):
    row = as_sentence(row)
    item = {k: row[k] for k in ["scripture", "version", "ref", "text", "section", "book", "chapter", "verse"]}
    item.update({k: row[k] for k in ["verse_first", "verse_last"] if k in row})
    o = original_for(row)
    item["original"] = o.get("text", "") if o else ""
    for lang in comp.LANGS:
        c = companion_for(row, lang)
        item[lang.lower()] = c.get("text", "") if c else ""
    if item["ref"] + item["version"] not in {f["ref"] + f["version"] for f in st.session_state.favs}:
        st.session_state.favs.append(item)
        st.toast(f"Saved {item['ref']} to your collection ⭐")
    else:
        st.toast("Already in your collection")


_CARD_JS = r"""
<style>
  html, body { margin: 0; background: transparent; font-family: "Source Sans Pro", "Inter", sans-serif; }
  img { display: block; width: 100%; max-width: 380px; aspect-ratio: 1080 / 1350; border-radius: 12px;
        box-shadow: 0 6px 22px rgba(0,0,0,.22); }
  body { padding: 2px 4px 14px; }
  .row { display: flex; gap: 8px; max-width: 380px; margin-top: 10px; }
  button { flex: 1; padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(127,127,127,.35);
           background: transparent; color: inherit; font: inherit; font-size: 15px; font-weight: 500; cursor: pointer; }
  button:hover { border-color: #ff4b4b; color: #ff4b4b; }
  #msg { font-size: 12.5px; opacity: .85; margin-top: 6px; line-height: 1.35; max-width: 380px; }
</style>
<img id="card" alt="Quote card">
<div class="row"><button id="dl">⬇️ Download</button><button id="sh">📤 Share</button></div>
<div id="msg"></div>
<script>
const DATA = "__B64__", NAME = __NAME__, SUBJECT = __SUBJECT__, BODY = __BODY__, TYPE = "image/jpeg";
const msg = t => document.getElementById("msg").textContent = t;
let P = window; try { void window.parent.document; P = window.parent; } catch (e) {}   // the Streamlit page
try { document.body.style.color = getComputedStyle(P.document.querySelector(".stApp") || P.document.body).color; } catch (e) {}
const bin = atob(DATA), bytes = new Uint8Array(bin.length);
for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
const img = document.getElementById("card");
img.src = URL.createObjectURL(new Blob([bytes], { type: TYPE }));

// Download through the page itself, so it works whatever the embedding frame allows
document.getElementById("dl").onclick = () => {
  const blob = new P.Blob([bytes], { type: TYPE }), url = P.URL.createObjectURL(blob);
  const a = P.document.createElement("a");
  a.href = url; a.download = NAME; P.document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => P.URL.revokeObjectURL(url), 5000);
};

// Clipboards only take PNG, so the card is redrawn as PNG for the copy fallback
const asPng = () => new Promise(res => {
  const c = document.createElement("canvas"); c.width = img.naturalWidth; c.height = img.naturalHeight;
  c.getContext("2d").drawImage(img, 0, 0); c.toBlob(res, "image/png");
});

document.getElementById("sh").onclick = async () => {
  // 1) The system share sheet (phones, Safari, Edge, Chrome): choose Mail and the card is attached as a picture.
  for (const n of [P.navigator, navigator]) {
    try {
      const file = new File([bytes], NAME, { type: TYPE });
      if (n.canShare && n.canShare({ files: [file] })) {
        await n.share({ files: [file], title: SUBJECT, text: BODY });
        msg("");
        return;
      }
    } catch (e) { if (e.name === "AbortError") return; }
  }
  // 2) No file sharing in this browser: copy the card, then open a new email to paste it into.
  let copied = false;
  for (const n of [navigator, P.navigator]) {
    try { await n.clipboard.write([new ClipboardItem({ "image/png": asPng() })]); copied = true; break; } catch (e) {}
  }
  const mail = "mailto:?subject=" + encodeURIComponent(SUBJECT) + "&body=" + encodeURIComponent(BODY + "\n\n");
  // Streamlit's frame may not navigate the page, so the mail link is clicked from inside the page itself
  try {
    const a = P.document.createElement("a");
    a.href = mail; P.document.body.appendChild(a); a.click(); a.remove();
  } catch (e) { window.open(mail, "_blank"); }
  msg(copied ? "Card copied: paste it into the email (Ctrl/⌘+V)." : "Download the card, then attach it to the email.");
};
</script>
"""


def card_panel(row, style: str = qc.THEMED) -> None:
    """Preview of the quote card with ⬇️ Download and 📤 Share. The image is embedded once and made only when
    asked for. Share opens the system share sheet with the card attached (an email shows the picture); where a
    browser can't share files it copies the card and opens a new email to paste it into."""
    import base64
    import json

    def js(v: str) -> str:  # a JS string literal that can't close the <script> element
        return json.dumps(v).replace("</", "<\\/")

    page = (_CARD_JS.replace("__B64__", base64.b64encode(card_jpg(row, style)).decode())
            .replace("__NAME__", js(f"{row['ref'].replace(' ', '_').replace(':', '-')}.jpg"))
            .replace("__SUBJECT__", js(f"A verse for you: {row['ref']}"))
            .replace("__BODY__", js(f"“{row['text']}”\n— {row['ref']} ({row['version']})")))
    if hasattr(st, "iframe"):  # Streamlit ≥ 1.5x: sizes itself to the content
        st.iframe(page, height="content")
    else:
        components.html(page, height=600)


def _flip(key: str) -> None:
    st.session_state[key] = not st.session_state.get(key, False)


def card_toggle(key: str, target=st) -> bool:
    """🖼️ Quote card button that opens / closes the card panel; returns whether it is open."""
    k = f"card_open_{key}"
    target.button("🖼️ Hide card" if st.session_state.get(k) else "🖼️ Quote card", key=f"cardbtn_{key}",
                  on_click=_flip, args=(k,), **STRETCH,
                  help="Make a shareable picture of this verse with the translations that are switched on.")
    return st.session_state.get(k, False)


def verse_actions(row, key: str, card: bool = True):
    row = as_sentence(row)
    c1, c2, _ = st.columns([1, 1, 3])
    c1.button("⭐ Save", key=f"fav_{key}", on_click=add_fav, args=(row,), **STRETCH)
    if card and card_toggle(key, c2):
        card_panel(row)


def stat_tile(col, value, label):
    col.markdown(f'<div class="stat"><div class="v">{value}</div><div class="l">{label}</div></div>',
                 unsafe_allow_html=True)


def style_fig(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10),
                      font=dict(family="Inter, sans-serif"), bargap=0.25, hoverlabel=dict(font_size=13),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(127,127,127,.15)", zeroline=False)
    return fig


def guard(key: str, options) -> None:
    """Drop a stale widget value (e.g. a Bible book after switching to the Quran)."""
    if key in st.session_state and st.session_state[key] not in list(options):
        del st.session_state[key]


def parse_words(raw: str) -> list[str]:
    words = [w.strip().lower() for w in re.split(r"[,;\n]", raw) if w.strip()]
    return list(dict.fromkeys(words))[:MAX_WORDS]


@st.cache_data(show_spinner=False)
def chapter_map(scripture: str, version: str) -> dict[str, list[int]]:
    d = get(scripture, version)
    return {b: sorted(int(c) for c in g.unique()) for b, g in d.groupby("book")["chapter"]}


def read_step(delta: int, rbooks: list[str], chmap: dict) -> None:
    """◀ / ▶ in the reader: next or previous chapter, moving on to the next / previous book at the ends."""
    b = st.session_state.get("read_book", rbooks[0])
    chs = chmap[b]
    cur = st.session_state.get("read_ch", chs[0])
    j = (chs.index(cur) if cur in chs else 0) + delta
    if 0 <= j < len(chs):
        st.session_state.read_ch = chs[j]
    else:
        i = rbooks.index(b) + delta
        if 0 <= i < len(rbooks):
            st.session_state.read_book = rbooks[i]
            st.session_state.read_ch = chmap[rbooks[i]][0 if delta > 0 else -1]
    st.session_state.pop("read_target", None)
    st.session_state.pop("read_msg", None)


_BOOK_ALIASES = {"songofsongs": "songofsolomon", "canticles": "songofsolomon", "revelation": "revelationofjohn",
                 "revelations": "revelationofjohn", "qoheleth": "ecclesiastes", "psalm": "psalms"}


def _norm_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"^(iii|3)\s*(?=[a-z])", "3", n)
    n = re.sub(r"^(ii|2)\s*(?=[a-z])", "2", n)
    n = re.sub(r"^(i|1)\s+(?=[a-z])", "1", n)
    n = re.sub(r"^1(?=[a-z])", "1", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return _BOOK_ALIASES.get(n, n)


def find_book(name: str, books: list[str], scripture: str) -> str | None:
    q = _norm_name(name)
    if not q:
        return None
    if scripture == "Quran":
        keyed = {b: re.sub(r"[^a-z]", "", re.sub(r"^\d+\.\s*", "", b.lower())) for b in books}
        q = q.rstrip("h")  # Baqarah / Baqara
        for test in (lambda k: k.startswith(q), lambda k: re.sub(r"^a[lnrstdz]", "", k).startswith(q),
                     lambda k: q in k):
            hits = [b for b, k in keyed.items() if test(k)]
            if hits:
                return hits[0]
        return None
    keyed = {b: _norm_name(b) for b in books}
    for test in (lambda k: k == q, lambda k: k.startswith(q), lambda k: q in k):
        hits = [b for b, k in keyed.items() if test(k)]
        if hits:
            return hits[0]
    return None


def go_to_ref(scripture: str, version: str, rbooks: list[str]) -> None:
    """Parse the reader's "Go to a verse" box (John 3:16, Psalm 23, 1 Cor 13:4, 2:255, Al-Baqara 255)."""
    raw = st.session_state.get("read_goto", "").strip()
    st.session_state.pop("read_msg", None)
    if not raw:
        return
    m = re.match(r"^(.*?)\s*(\d+)(?:\s*[:.,]\s*(\d+))?\s*$", raw)
    if not m:
        st.session_state.read_msg = f"Couldn't read “{raw}”. Try e.g. John 3:16."
        return
    name, n1, n2 = m.group(1).strip(), int(m.group(2)), int(m.group(3)) if m.group(3) else None
    if name.lower() in ("quran", "qur'an", "koran", "surah", "sura"):
        name = ""
    chmap = chapter_map(scripture, version)
    allbooks = list(chmap)
    d = get(scripture, version)
    if scripture == "Quran":
        if name:
            bk, verse = find_book(name, allbooks, scripture), (n2 if n2 else n1)
        else:
            hits = d.loc[d["chapter"] == n1, "book"]
            bk, verse = (hits.iloc[0] if len(hits) else None), n2
        ch = chmap[bk][0] if bk else None
    else:
        bk = find_book(name, allbooks, scripture) if name else None
        ch, verse = n1, n2
    if not bk:
        st.session_state.read_msg = f"No {CATALOG[scripture]['unit'].lower()} matches “{name or raw}” in the {scripture}."
        return
    if bk not in rbooks:
        st.session_state.read_msg = f"{bk} isn't in the selected section. Choose “All sections” in the sidebar."
        return
    if ch not in chmap[bk]:
        st.session_state.read_msg = f"{bk} has chapters 1–{chmap[bk][-1]}."
        return
    if verse is not None and not ((d["book"] == bk) & (d["chapter"] == ch) & (d["verse"] == verse)).any():
        st.session_state.read_msg = f"{bk} {'' if scripture == 'Quran' else f'{ch}:'}{verse} isn't in {version}."
        verse = None
    st.session_state.read_book = bk
    st.session_state.read_ch = ch
    st.session_state.read_target = ((bk, ch), verse) if verse else None


def quran_choice(lang: str) -> str:
    meta = comp.LANGS[lang]
    return st.session_state.get(f"quran_{meta['code']}", meta["default_quran"])


@st.cache_data(show_spinner="Preparing the translation…")
def comp_series(scripture: str, version: str, lang: str, quran_name: str) -> pd.Series:
    """The Persian / Spanish text for every verse of a version, aligned with get(scripture, version)."""
    d = get(scripture, version)
    if scripture == "Quran":
        tr = companion_quran(lang, quran_name)
        vals = [tr.get((c, v), "") for c, v in zip(d["chapter"], d["verse"])]
    else:
        code = orig.source_code(scripture, version)
        bible = companion_bible(lang)
        if code in comp.NO_PAIRING:
            vals = [""] * len(d)
        elif code in comp.HEBREW_NUMBERED:
            heb, back = heb_map(scripture, version), kjv_from_hebrew()
            vals = []
            for b, c, v in zip(d["book"], d["chapter"], d["verse"]):
                refs = list(dict.fromkeys(k for h in heb.get((b, c, v), []) for k in back.get((b, *h), []))) or [(c, v)]
                vals.append(" ".join(bible.get((b, *r), "") for r in refs).strip())
        else:
            vals = [bible.get((b, c, v), "") for b, c, v in zip(d["book"], d["chapter"], d["verse"])]
    return pd.Series(vals, index=d.index)


# Search in Persian and Spanish: letters that are written several ways match each other
_ES_CLASS = {"a": "aáàâä", "e": "eéèêë", "i": "iíìîï", "o": "oóòôö", "u": "uúùûü", "n": "nñ", "c": "cç"}
_FA_CLASS = {"ی": "یيى", "ي": "یيى", "ى": "یيى", "ک": "کك", "ك": "کك", "ه": "هةۀ", "ة": "هة", "ۀ": "ۀهة",
             "ا": "اآأإ", "آ": "آا", "و": "وؤ"}
_FA_MARKS = "ً-ٰٟ‌‍"


def search_pattern(q: str, lang: str, mode: str) -> str:
    q = q.strip()
    if lang == "English":
        if mode == "Anywhere in text":
            return re.escape(q).replace(r"\ ", r"\s+")
        return an.word_pattern(q, mode == "Word & its forms")
    import unicodedata
    if lang == "Spanish":
        plain = "".join(ch for ch in unicodedata.normalize("NFD", q.lower()) if unicodedata.category(ch) != "Mn")
        body = "".join(r"\s+" if ch.isspace() else f"[{_ES_CLASS[ch]}]" if ch in _ES_CLASS else re.escape(ch)
                       for ch in plain)
        body = re.sub(r"(\\s\+)+", r"\\s+", body)
        if mode == "Exact word":
            return rf"(?<!\w){body}(?!\w)"
        return rf"(?<!\w){body}" if mode == "Word & its forms" else body
    # Persian: ignore vowel marks and zero-width joiners, in the query and between the letters of the text
    plain = re.sub(f"[{_FA_MARKS}]", "", q)
    parts = []
    for ch in plain:
        if ch.isspace():
            parts.append(r"[\s‌]+")
        else:
            parts.append((f"[{_FA_CLASS[ch]}]" if ch in _FA_CLASS else re.escape(ch)) + f"[{_FA_MARKS}]*")
    body = re.sub(r"(\[\\s\\u200c\]\+)+", r"[\\s\\u200c]+", "".join(parts))
    if mode == "Exact word":
        return rf"(?<!\w){body}(?![\w‌])"
    return rf"(?<!\w){body}" if mode == "Word & its forms" else body


# --------------------------------------------------------------------------------------
# Sidebar — global selection
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sb-title">📜 Sacred Words</div>', unsafe_allow_html=True)
    st.caption("Pick a scripture, a translation and a part to explore.")
    scripture = st.selectbox("Scripture", SCRIPTURES, index=SCRIPTURES.index("Bible"), format_func=lambda s: f"{CATALOG[s]['icon']}  {s}")
    versions = list(CATALOG[scripture]["versions"])
    version = st.selectbox("Version / translation", versions,
                           index=versions.index(DEFAULT_VERSION[scripture]))
    df = get(scripture, version)
    sections = ["All sections"] + list(dict.fromkeys(df.sort_values("book_num")["section"]))
    section = st.selectbox("Section", sections)
    books_df = filter_scope(df, section, "All books")
    books = ["All books"] + list(dict.fromkeys(books_df.sort_values("book_num")["book"]))
    unit = CATALOG[scripture]["unit"]
    book = st.selectbox(unit, books)
    scope = filter_scope(df, section, book)
    accent = COLORS[scripture]
    st.markdown(f'<span class="badge" style="--accent:{accent}">{len(scope):,} verses in view</span>',
                unsafe_allow_html=True)
    st.divider()
    st.toggle("Show Arabic / Hebrew original", False, key="show_orig",
              help="Arabic for the Quran; Hebrew for the Torah and the Old Testament.")
    if scripture != "Quran" and st.session_state.get("show_orig", False):
        st.radio("Hebrew marks", ["Vowels only", "Vowels & cantillation", "Consonants only"], key="heb_marks",
                 help="Cantillation marks are the chanting accents; consonant-only text is how a Torah scroll is written.")
    for lang, meta in comp.LANGS.items():
        st.toggle(f"Show {lang} translation ({meta['native']})", True, key=f"show_{meta['code']}",
                  help=f"Adds the {lang} translation under every verse, in the reader and in Compare Translations. "
                       f"Bible and Torah: {meta['bible_label'].split(' · ')[1]}. Quran: choose the translator below.")
        if lang_on(lang):
            st.selectbox(f"{lang} Quran translation", list(meta["quran"]), key=f"quran_{meta['code']}",
                         index=list(meta["quran"]).index(meta["default_quran"]))
    st.divider()
    st.markdown(f"**⭐ Collection:** {len(st.session_state.favs)} saved")
    with st.expander("ℹ️ About & sources"):
        st.markdown(
            "- **Quran** (English translations): tanzil.net, with full punctuation\n"
            "- **Bible & Torah/Tanakh** (public-domain translations): `scrollmapper/bible_databases`\n"
            "- **Arabic Quran**: Uthmani script from tanzil.net\n"
            "- **Persian**: Quran translations from tanzil.net (Makarem Shirazi, Fooladvand, Ansarian, "
            "Elahi Ghomshei); Bible & Torah from the Persian Old Version (1895, public domain) via eBible.org. "
            "It follows English verse numbers, so JPS verses are matched through the Hebrew numbering\n"
            "- **Spanish**: Quran translations from tanzil.net (Julio Cortés, Raúl González Bórnez, Isa García); "
            "Bible & Torah from the Reina-Valera 1909 (public domain) via eBible.org, matched the same way\n"
            "- **Hebrew Bible**: Westminster Leningrad Codex. English verse numbers are converted to Hebrew "
            "numbering with the standard Copenhagen Alliance versification table (e.g. KJV Malachi 4:1 = Hebrew 3:19)\n"
            "- *Torah* here covers the Hebrew Bible: the five books of Moses plus Nevi'im and Ketuvim. "
            "Choose **Section → Torah** for the five books alone.\n\n"
            "All texts are cached locally in `./data` after the first load.")

# --------------------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------------------
tot_verses = sum(len(get(s, DEFAULT_VERSION[s])) for s in SCRIPTURES)
n_versions = sum(len(CATALOG[s]["versions"]) for s in SCRIPTURES)
st.markdown(f"""
<div class="hero">
  <h1>Sacred Words Explorer</h1>
  <p>Discover, read, compare and visualise the words of the Quran, the Bible and the Torah — in English, Persian and Spanish.</p>
  <div class="chips"><span>☪️ Quran</span><span>✝️ Bible</span><span>✡️ Torah</span>
  <span>📚 {n_versions} translations</span><span>📖 {tot_verses:,} verses</span></div>
</div>""", unsafe_allow_html=True)

def matched_version(s: str) -> str:
    """Translation to use for scripture `s` given the sidebar choice: the sidebar version for the
    sidebar scripture; for the others the same translation when the user picked a non-default one
    they also have (KJV / ASV / YLT), otherwise their default (so the Torah stays on JPS 1917)."""
    if s == scripture:
        return version
    if version != DEFAULT_VERSION[scripture] and version in CATALOG[s]["versions"]:
        return version
    return DEFAULT_VERSION[s]


tabs = st.tabs(["✨ Inspire", "📖 Read", "🔍 Search", "☁️ Word Cloud", "📊 Word Insights",
                "⚖️ Compare Translations", "⭐ My Collection"])
THEME_OPTS = ["Any"] + list(an.THEMES)
theme_label = lambda t: "🎲 Any theme" if t == "Any" else f"{an.THEMES[t]['emoji']} {t}"

# ======================================================================================
# 1. INSPIRE
# ======================================================================================
with tabs[0]:
    st.subheader("A word for you")
    c1, c2, c3 = st.columns([2, 2, 3])
    theme = c1.selectbox("Theme", THEME_OPTS, format_func=theme_label, key="insp_theme")
    source = c2.selectbox("Draw from", ["Current selection", "Any scripture"], key="insp_src")
    c3.write("")
    b1, b2 = c3.columns(2)
    draw = b1.button("✨ Inspire me", type="primary", **STRETCH)
    daily = b2.button("📅 Verse of the day", **STRETCH)

    if source == "Any scripture":
        pool = pd.concat([nice_pool(s, matched_version(s)) for s in SCRIPTURES])
    else:
        pool = an.nice_verses(scope)
        if pool.empty:
            pool = scope
    pool = an.theme_filter(pool, theme)

    # Redraw automatically whenever the sidebar selection (or theme / source) changes,
    # so the verse always comes from what is currently selected.
    # "Verse of the day" mode is remembered until "Inspire me" is pressed, so a dropdown
    # change shows today's verse for the new selection rather than a random one.
    if daily:
        st.session_state.insp_daily = True
    elif draw:
        st.session_state.insp_daily = False
    daily_mode = st.session_state.get("insp_daily", False)
    ctx = (theme, source, scripture, version) + ((section, book) if source == "Current selection" else ())
    changed = st.session_state.get("pick_ctx") != ctx
    if draw or daily or changed or st.session_state.pick is None:
        st.session_state.pick_ctx = ctx
        if pool.empty:
            st.warning("No verse matches that theme in this selection. Try another theme or a wider selection.")
        else:
            seed = int(dt.date.today().strftime("%Y%m%d")) if daily_mode else None
            # Every book (surah) in the pool is equally likely, however many matching verses it has.
            # With "Any scripture", each scripture is also equally likely: its share is split evenly
            # across its books, so weight = 1 / (verses in the book x books in the scripture).
            weights = 1.0 / pool.groupby(["scripture", "book"])["book"].transform("size")
            if source == "Any scripture":
                weights = weights / pool.groupby("scripture")["book"].transform("nunique")
            st.session_state.pick = pool.sample(1, weights=weights, random_state=seed).iloc[0].to_dict()

    if st.session_state.pick:
        pick = st.session_state.pick
        pat = an.theme_pattern(theme) if theme != "Any" else None
        st.markdown(verse_html(pick, big=True, pattern=pat), unsafe_allow_html=True)
        if daily_mode:
            st.caption(f"📅 Verse of the day for {dt.date.today():%B %d, %Y}, drawn from your current choices. "
                       "Press ✨ Inspire me for a random verse.")
        verse_actions(pick, "pick")

    st.divider()
    st.subheader("🌍 One theme, three traditions")
    st.caption("The same theme drawn from each scripture side by side. Your sidebar scripture comes first and "
               "uses your chosen translation, section and book; the others use the same translation where they have it. "
               "Hit shuffle for a new set.")
    t1, t2 = st.columns([2, 5])
    trio_theme = t1.selectbox("Theme", list(an.THEMES), format_func=theme_label, key="trio_theme")
    trio_order = [scripture] + [s for s in SCRIPTURES if s != scripture]
    trio_ctx = (trio_theme, scripture, version, section, book)
    if t2.button("🔄 Shuffle trio") or st.session_state.trio is None or st.session_state.trio[0] != trio_ctx:
        picks, notes = [], []
        for s in trio_order:
            note = None
            if s == scripture:
                base = an.nice_verses(scope)
                p = an.theme_filter(base if len(base) else scope, trio_theme)
                if p.empty and (section != "All sections" or book != "All books"):
                    # Nothing on this theme in the narrowed scope: widen to the whole scripture.
                    p = an.theme_filter(nice_pool(s, version), trio_theme)
                    note = f"No {trio_theme.lower()} verse in your current selection, so this one is from the whole {s}."
            else:
                p = an.theme_filter(nice_pool(s, matched_version(s)), trio_theme)
            # Give every book (surah for the Quran) an equal chance, however many matching verses it has.
            w = 1.0 / p.groupby("book")["book"].transform("size") if len(p) else None
            picks.append(p.sample(1, weights=w).iloc[0].to_dict() if len(p) else None)
            notes.append(note)
        st.session_state.trio = (trio_ctx, trio_order, picks, notes)
    _, order, picks, notes = st.session_state.trio
    cols = st.columns(3)
    for col, p, s, note in zip(cols, picks, order, notes):
        with col:
            if p:
                st.markdown(verse_html(p, pattern=an.theme_pattern(trio_theme)), unsafe_allow_html=True)
                if note:
                    st.caption(note)
                st.button("⭐ Save", key=f"trio_{s}", on_click=add_fav, args=(p,))
            else:
                st.info(f"No {trio_theme.lower()} verse found in the {s}.")

    st.divider()
    st.subheader("🎡 Theme explorer")
    st.caption("How often each theme appears in each scripture (matching verses per 1,000 verses).")
    tdf = theme_table()
    fig = go.Figure()
    for s in SCRIPTURES:
        d = tdf[tdf.scripture == s]
        fig.add_trace(go.Scatterpolar(r=list(d.per1000) + [d.per1000.iloc[0]],
                                      theta=list(d.theme) + [d.theme.iloc[0]], name=s, fill="toself",
                                      line=dict(color=COLORS[s], width=2), opacity=0.55,
                                      hovertemplate="%{theta}: %{r:.0f} per 1,000 verses<extra>" + s + "</extra>"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, gridcolor="rgba(127,127,127,.2)")))
    st.plotly_chart(style_fig(fig, 520), key="radar")
    with st.expander("Show as table"):
        st.dataframe(tdf.pivot(index="theme", columns="scripture", values="per1000").round(1))

# ======================================================================================
# 2. READ
# ======================================================================================
with tabs[1]:
    st.subheader(f"Read the {scripture}")
    rbooks = list(dict.fromkeys(books_df.sort_values("book_num")["book"]))
    chmap = chapter_map(scripture, version)
    # Follow the sidebar's book when it changes; otherwise keep the reader where it is
    if st.session_state.get("read_sync") != (scripture, section, book):
        st.session_state.read_sync = (scripture, section, book)
        st.session_state.read_book = book if book in rbooks else rbooks[0]
        st.session_state.pop("read_ch", None)
        st.session_state.pop("read_target", None)
    guard("read_book", rbooks)
    st.session_state.setdefault("read_book", rbooks[0])

    g1, g2 = st.columns([3, 4])
    g1.text_input("🔎 Go to a verse", key="read_goto", on_change=go_to_ref, args=(scripture, version, rbooks),
                  placeholder="e.g. 2:255 or Al-Baqara 255" if scripture == "Quran" else "e.g. John 3:16 or Psalm 23",
                  help="Type a reference and press Enter. Book names can be shortened (Gen 1:1, 1 Cor 13).")
    if st.session_state.get("read_msg"):
        g2.write("")
        g2.warning(st.session_state.read_msg)

    r1, r2, r3, r4 = st.columns([3, 1, 3, 2])
    rbook = r1.selectbox(unit, rbooks, key="read_book", on_change=lambda: (st.session_state.pop("read_ch", None),
                                                                          st.session_state.pop("read_target", None)))
    bdf = df[df["book"] == rbook]
    chapters = chmap[rbook]
    guard("read_ch", chapters)
    if scripture == "Quran":
        rch = chapters[0]
        r2.metric("Verses", len(bdf))
    else:
        rch = r2.selectbox("Chapter", chapters, key="read_ch",
                           on_change=lambda: st.session_state.pop("read_target", None))
    others = ["— none —"] + [v for v in versions if v != version]
    parallel = r3.selectbox("Side-by-side with", others, key="read_par")
    hl = r4.text_input("Highlight word", key="read_hl", placeholder="e.g. light")
    pat = an.word_pattern(hl, True) if hl.strip() else None

    chap = bdf[bdf["chapter"] == rch].sort_values("verse")
    title = rbook if scripture == "Quran" else f"{rbook} {rch}"
    target = st.session_state.get("read_target")
    target = target[1] if target and target[0] == (rbook, rch) else None

    def nav(where: str):
        i, j = rbooks.index(rbook), chapters.index(rch)
        has_prev = j > 0 or i > 0
        has_next = j < len(chapters) - 1 or i < len(rbooks) - 1
        step = "surah" if scripture == "Quran" else "chapter"
        n1, _, n2 = st.columns([1, 3, 1])
        n1.button(f"◀ Previous {step}", key=f"prev_{where}", on_click=read_step, args=(-1, rbooks, chmap),
                  disabled=not has_prev, **STRETCH)
        n2.button(f"Next {step} ▶", key=f"next_{where}", on_click=read_step, args=(1, rbooks, chmap),
                  disabled=not has_next, **STRETCH)

    def reader_grid(frames: list[tuple[str, pd.DataFrame]]) -> str:
        """Verse-by-verse grid: the chosen version, an optional second version (matched verse by verse, also where
        the two number verses differently), the active translations and the original language."""
        base = frames[0][1]
        recs = base.to_dict("records")
        par = None
        if len(frames) > 1:
            pname, pbook = frames[1]
            ptext = {(c, v): t for c, v, t in zip(pbook["chapter"], pbook["verse"], pbook["text"])}
            par = []
            for r in recs:
                refs = aligned_refs(scripture, version, pname, rbook, r["chapter"], r["verse"])
                txt = " ".join(ptext.get(x, "") for x in refs).strip()
                num = str(r["verse"]) if refs == [(r["chapter"], r["verse"])] else _ref_span(refs)
                par.append((num, txt))
        origs = [original_for(r) for r in recs]
        comps = {lang: [companion_for(r, lang) for r in recs] for lang in active_langs()}
        comps = {k: v for k, v in comps.items() if any(c and c.get("text") for c in v)}
        has_orig = any(o and o.get("text") for o in origs)
        lang = next((o["lang"] for o in origs if o and o.get("text")), "")
        heads = ([lbl for lbl, _ in frames] + list(comps)
                 + (["Arabic original" if lang == "ar" else "Hebrew original"] if has_orig else []))
        cells = "".join(f'<div class="head">{html.escape(h)}</div>' for h in heads)

        def rtl_cell(o, cls):
            return (f'<div class="orig {o["lang"]}{cls}" lang="{o["lang"]}" dir="{text_dir(o["lang"])}">'
                    f'{html.escape(o["text"])}</div>' if o and o.get("text") else f'<div class="{cls}"></div>')

        for i, (r, o) in enumerate(zip(recs, origs)):
            cls = " tgt" if r["verse"] == target else ""
            cells += f'<div class="{cls}"><sup>{r["verse"]}</sup>{highlight(r["text"], pat)}</div>'
            if par is not None:
                cells += f'<div class="{cls}"><sup>{par[i][0]}</sup>{highlight(par[i][1], pat)}</div>'
            for cs in comps.values():
                cells += rtl_cell(cs[i], cls)
            if has_orig:
                cells += rtl_cell(o, cls)
        note = " · ".join(dict.fromkeys(x["label"] for x in origs + [c for cs in comps.values() for c in cs]
                                        if x and not x.get("text")))
        if par is not None and any(num != str(r["verse"]) for (num, _), r in zip(par, recs)):
            note = ((note + " · ") if note else "") + (f"{frames[1][0]} numbers some of these verses differently; "
                                                       "its own numbers are shown.")
        return (f'<div class="reader" style="--accent:{accent}"><h3 style="font-family:Cormorant Garamond,serif;'
                f'margin:.2rem 0 .8rem">{html.escape(title)}</h3>'
                f'<div class="rgrid" style="--cols:{len(heads)}">{cells}</div>'
                + (f'<div class="olabel" style="margin-top:10px">{html.escape(note)}</div>' if note else "")
                + "</div>")

    def reader(frame, label):
        body = " ".join((f'<span class="tgt">' if v == target else "<span>") + f"<sup>{v}</sup>{highlight(t, pat)}</span>"
                        for v, t in zip(frame.verse, frame.text))
        return (f'<div class="reader" style="--accent:{accent}"><div class="badge" style="--accent:{accent}">'
                f'{html.escape(label)}</div><h3 style="font-family:Cormorant Garamond,serif;margin:.4rem 0 1rem">'
                f'{html.escape(title)}</h3>{body}</div>')

    nav("top")
    if st.session_state.get("show_orig", False) or active_langs() or parallel != "— none —":
        frames = [(version, chap)]
        if parallel != "— none —":
            pdf = get(scripture, parallel)
            frames.append((parallel, pdf[pdf["book"] == rbook]))
        st.markdown(reader_grid(frames), unsafe_allow_html=True)
    else:
        st.markdown(reader(chap, version), unsafe_allow_html=True)
    nav("bottom")

    with st.expander("⭐ Save or share a verse from this chapter", expanded=target is not None):
        vlist = chap["verse"].tolist()
        guard("read_vsel", vlist)
        if target in vlist and st.session_state.get("read_vsel_for") != (rbook, rch, target):
            st.session_state.read_vsel_for = (rbook, rch, target)
            st.session_state.read_vsel = target
        vnum = st.selectbox("Verse", vlist, key="read_vsel")
        vrow = as_sentence(chap[chap["verse"] == vnum].iloc[0])
        st.markdown(verse_html(vrow), unsafe_allow_html=True)
        verse_actions(vrow, "read")

# ======================================================================================
# 3. SEARCH
# ======================================================================================
with tabs[2]:
    st.subheader("Search the scriptures")
    s1, s0, s2, s3 = st.columns([4, 2, 2, 2])
    qlang = s0.selectbox("Language", ["English"] + list(comp.LANGS), key="q_lang",
                         format_func=lambda l: l if l == "English" else f"{l} ({comp.LANGS[l]['native']})",
                         help="Search the English text or the Persian / Spanish translation. Persian matches "
                              "ي/ی and ك/ک alike and ignores vowel marks; Spanish ignores accents (senor finds Señor).")
    placeholder = {"English": "e.g. light upon light, patience, the good shepherd",
                   "Persian": "مثلاً: رحمت، نور، صبر", "Spanish": "p. ej.: misericordia, luz, paciencia"}[qlang]
    q = s1.text_input("Word or phrase", placeholder=placeholder, key="q")
    where = s2.selectbox("Where", ["Current selection", "All three scriptures"], key="q_where")
    mode = s3.selectbox("Match", ["Word & its forms", "Exact word", "Anywhere in text"], key="q_mode")
    whole = st.toggle("Show full sentences (join verses that continue into the next one)", True, key="q_whole")
    if q.strip():
        qpat = search_pattern(q, qlang, mode)
        # (scripture, version, verses) to search: the current selection, or each scripture in its default version
        parts = ([(s_, DEFAULT_VERSION[s_], get(s_, DEFAULT_VERSION[s_])) for s_ in SCRIPTURES]
                 if where == "All three scriptures" else [(scripture, version, scope)])
        hit_parts, n_base = [], 0
        for s_, v_, d_ in parts:
            n_base += len(d_)
            col = d_["text"] if qlang == "English" else comp_series(s_, v_, qlang, quran_choice(qlang)).loc[d_.index]
            hit_parts.append(d_[col.str.contains(qpat, case=False, regex=True)])
        hits = pd.concat(hit_parts)
        if qlang != "English" and any(numbering(s_, v_) == "vulgate" for s_, v_, _ in parts):
            st.caption(f"ℹ️ Douay-Rheims isn't paired with the {qlang} translation, so it can't be searched in {qlang}.")
        m1, m2, m3 = st.columns(3)
        stat_tile(m1, f"{len(hits):,}", "matching verses")
        stat_tile(m2, f"{hits['book'].nunique():,}", f"{'books / surahs' if where != 'Current selection' else unit.lower() + 's'}")
        stat_tile(m3, f"{(len(hits) / max(n_base, 1) * 100):.2f}%", "of verses in scope")
        st.write("")
        if len(hits):
            by = (hits.groupby(["scripture", "book_num", "short_book"]).size()
                  .reset_index(name="verses").sort_values(["scripture", "book_num"]))
            fig = px.bar(by, x="short_book", y="verses", color="scripture", color_discrete_map=COLORS,
                         title=f"Where “{q}” appears", labels={"short_book": "", "verses": "Matching verses"})
            fig.update_traces(marker_line_width=0, hovertemplate="%{x}: %{y} verses<extra></extra>")
            st.plotly_chart(style_fig(fig, 360), key="search_bar")

            n_show = st.slider("Results to show", 10, 200, 30, 10, key="q_n")
            order = st.radio("Order", ["Canonical", "Random", "Shortest first"], horizontal=True, key="q_order")
            show = hits.sort_values(["scripture", "book_num", "chapter", "verse"])
            if order == "Random":
                show = show.sample(frac=1, random_state=1)
            elif order == "Shortest first":
                show = show.sort_values("n_words")
            for i, (_, r) in enumerate(show.head(n_show).iterrows()):
                row = as_sentence(r) if whole else dict(r)
                if qlang == "English":
                    st.markdown(verse_html(row, pattern=qpat), unsafe_allow_html=True)
                else:
                    st.markdown(verse_html(row, comp_patterns={qlang: qpat}), unsafe_allow_html=True)
            # CSV: the English plus the searched language and every translation that is switched on
            out_langs = list(dict.fromkeys(([] if qlang == "English" else [qlang]) + active_langs()))
            csv_parts = []
            for (s_, v_, _), h_ in zip(parts, hit_parts):
                h_ = h_[["scripture", "version", "ref", "text"]].copy()
                for lang in out_langs:
                    h_[lang] = comp_series(s_, v_, lang, quran_choice(lang)).loc[h_.index]
                csv_parts.append(h_)
            download_link("⬇️ Download all results (CSV)", pd.concat(csv_parts).to_csv(index=False).encode("utf-8-sig"),
                          "search_" + re.sub(r"\W+", "_", q.strip()) + ".csv", "text/csv")
        else:
            st.info("No matches. Try “Word & its forms”, “Anywhere in text” or a wider scope.")
    else:
        st.info({"English": "Type a word above. Try **mercy**, **light**, **neighbour**, **orphan**, **garden** or **covenant**.",
                 "Persian": "Type a Persian word above, e.g. **رحمت**، **نور**، **صبر** or **بهشت**.",
                 "Spanish": "Type a Spanish word above, e.g. **misericordia**, **luz**, **paciencia** or **huérfano**."}[qlang])

# ======================================================================================
# 4. WORD CLOUD
# ======================================================================================
with tabs[3]:
    st.subheader("Word clouds")
    w1, w2, w3, w4 = st.columns(4)
    cmode = w1.selectbox("Mode", ["Current selection", "Three scriptures side by side", "Words around a keyword"],
                         key="wc_mode")
    cmap = w2.selectbox("Palette", ["viridis", "plasma", "cividis", "magma", "Blues", "Greens", "YlOrBr",
                                    "PuBuGn", "twilight", "Dark2"], key="wc_cmap")
    shape = w3.selectbox("Shape", ["Rectangle", "Circle", "Heart", "Star", "Arch"], key="wc_shape")
    maxw = w4.slider("Max words", 30, 300, 150, 10, key="wc_max")
    o1, o2, o3 = st.columns([2, 2, 3])
    archaic = o1.toggle("Hide archaic & filler words (thee, unto, hath…)", True, key="wc_arch")
    dark = o2.toggle("Dark background", False, key="wc_dark")
    extra = o3.text_input("Also hide these words (comma separated)", key="wc_extra", placeholder="lord, god, allah")
    extra_stop = set(parse_words(extra.replace(" ", ","))) if extra else set()
    opts = dict(colormap=cmap, max_words=maxw, archaic=archaic, shape=shape, dark=dark,
                extra_stop=frozenset(extra_stop))

    def cloud_and_download(texts, name, key):
        try:
            png = cached_cloud(tuple(texts), **opts)
        except Exception as e:  # show the real cause instead of a blank area
            st.error(f"Could not build the word cloud: {type(e).__name__}: {e}")
            st.exception(e)
            return
        if png is None:
            st.info("Not enough words to draw a cloud.")
            return
        show_png(png)
        download_link("⬇️ Download PNG", png, f"wordcloud_{name}.png", "image/png")

    if cmode == "Current selection":
        label = f"{scripture} · {version}" + ("" if book == "All books" else f" · {book}")
        st.caption(f"Cloud for **{label}** ({len(scope):,} verses)")
        cloud_and_download(scope["text"], scripture, "dl_cloud")
    elif cmode == "Three scriptures side by side":
        cols = st.columns(3)
        alld = get_defaults()
        for col, s in zip(cols, SCRIPTURES):
            with col:
                st.markdown(f"#### {CATALOG[s]['icon']} {s}")
                cloud_and_download(alld[alld.scripture == s]["text"], s, f"dl_{s}")
    else:
        kw = st.text_input("Keyword", "mercy", key="wc_kw")
        if kw.strip():
            kp = an.word_pattern(kw, True)
            sub = scope[scope["text"].str.contains(kp, case=False, regex=True)]
            st.caption(f"Words that share a verse with **{kw}** in {scripture} ({len(sub):,} verses)")
            opts["extra_stop"] = frozenset(extra_stop | set(an.tokenize(kw)))
            cloud_and_download(sub["text"], f"around_{kw}", "dl_kw")

# ======================================================================================
# 5. WORD INSIGHTS
# ======================================================================================
with tabs[4]:
    st.subheader("Word insights")
    i1, i2 = st.columns([4, 2])
    raw = i1.text_input(f"Words to analyse (comma separated, up to {MAX_WORDS})",
                        "love, mercy, peace, fear, light", key="ins_words")
    forms = i2.toggle("Include word forms (love → loved, loveth…)", True, key="ins_forms")
    words = parse_words(raw)
    wcolor = {w: SERIES[i] for i, w in enumerate(words)}

    if not words:
        st.info("Enter at least one word.")
    else:
        # ---- A. Cross-scripture comparison
        cdf = cross_counts(tuple(words), forms)
        fig = px.bar(cdf, x="word", y="per10k", color="scripture", barmode="group", color_discrete_map=COLORS,
                     text=cdf["per10k"].map(lambda v: f"{v:.1f}"), custom_data=["count", "scripture"],
                     title="How often each word appears — per 10,000 words (default translation of each scripture)",
                     labels={"per10k": "Occurrences per 10k words", "word": ""})
        fig.update_traces(textposition="outside", marker_line_width=0,
                          hovertemplate="<b>%{x}</b> in %{customdata[1]}<br>%{y:.2f} per 10k words"
                                        "<br>%{customdata[0]:,} occurrences<extra></extra>")
        st.plotly_chart(style_fig(fig, 430), key="ins_cross")
        st.caption("Normalised counts make scriptures of different lengths comparable. "
                   f"Versions: {', '.join(f'{s} — {DEFAULT_VERSION[s]}' for s in SCRIPTURES)}.")

        # ---- B. Across books of the current scope
        st.markdown(f"#### 📈 Across the {unit.lower()}s of the {scripture} ({version})")
        wb = by_book(scripture, version, section, tuple(words), forms)
        fig = px.line(wb, x="short_book", y="per10k", color="word", markers=True,
                      color_discrete_map=wcolor, custom_data=["count", "word"],
                      labels={"short_book": "", "per10k": "per 10k words"},
                      title=f"Word frequency through the {unit.lower()}s, in canonical order")
        fig.update_traces(line_width=2, marker_size=8,
                          hovertemplate="<b>%{x}</b><br>%{customdata[1]}: %{y:.1f} per 10k "
                                        "(%{customdata[0]} times)<extra></extra>")
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(style_fig(fig, 430), key="ins_line")

        # ---- C. Heatmap
        hm = wb.pivot_table(index="word", columns=["book_num", "short_book"], values="per10k").reindex(words)
        fig = go.Figure(go.Heatmap(z=hm.values, x=[b for _, b in hm.columns], y=hm.index, colorscale="Blues",
                                   xgap=2, ygap=2, colorbar=dict(title="per 10k"),
                                   hovertemplate="%{y} in %{x}: %{z:.1f} per 10k words<extra></extra>"))
        fig.update_layout(title="Heatmap — where each word concentrates")
        st.plotly_chart(style_fig(fig, 160 + 46 * len(words)), key="ins_heat")

        # ---- D. Co-occurrence + translations
        d1, d2 = st.columns(2)
        with d1:
            focus = st.selectbox("Word companions for", words, key="ins_focus")
            co = cooc(scripture, version, section, book, focus, forms)
            if len(co):
                fig = px.bar(co.iloc[::-1], x="verses", y="word", orientation="h", text="verses",
                             title=f"Words that most often share a verse with “{focus}”",
                             labels={"verses": "Shared verses", "word": ""})
                fig.update_traces(marker_color=wcolor[focus], marker_line_width=0, textposition="outside",
                                  hovertemplate="%{y}: %{x} verses<extra></extra>")
                st.plotly_chart(style_fig(fig, 480), key="ins_co")
            else:
                st.info(f"“{focus}” doesn't appear in the current selection.")
        with d2:
            st.selectbox("Translation comparison for", [focus], key="ins_tr_dummy", disabled=True,
                         help="Uses the word chosen on the left")
            tr = translation_counts(scripture, section, book, focus, forms)
            fig = px.bar(tr, x="per10k", y="version", orientation="h",
                         text=tr["per10k"].map(lambda v: f"{v:.1f}"), custom_data=["count"],
                         title=f"“{focus}” across {scripture} translations",
                         labels={"per10k": "per 10k words", "version": ""})
            fig.update_traces(marker_color=accent, marker_line_width=0, textposition="outside",
                              hovertemplate="%{y}<br>%{x:.2f} per 10k (%{customdata[0]:,} times)<extra></extra>")
            st.plotly_chart(style_fig(fig, 480), key="ins_tr")

    # ---- E. Corpus profile (independent of chosen words)
    st.divider()
    st.markdown(f"#### 🧮 Profile of the current selection: {scripture} · {version}"
                + ("" if book == "All books" else f" · {book}"))
    summ = cached_summary(scripture, version, section, book)
    k = st.columns(5)
    stat_tile(k[0], f"{summ['verses']:,}", "verses")
    stat_tile(k[1], f"{summ['words']:,}", "words")
    stat_tile(k[2], f"{summ['unique']:,}", "unique words")
    stat_tile(k[3], f"{summ['avg_len']:.1f}", "avg words / verse")
    stat_tile(k[4], f"{summ['unique'] / max(summ['words'], 1) * 100:.1f}%", "vocabulary richness")
    st.write("")
    e1, e2 = st.columns(2)
    with e1:
        tw = top_words_c(scripture, version, section, book)
        fig = px.bar(tw.iloc[::-1], x="count", y="word", orientation="h", text="count",
                     title="Top 20 meaningful words", labels={"count": "Occurrences", "word": ""})
        fig.update_traces(marker_color=accent, marker_line_width=0, textposition="outside",
                          hovertemplate="%{y}: %{x:,}<extra></extra>")
        st.plotly_chart(style_fig(fig, 560), key="top_words")
    with e2:
        sb = (filter_scope(df, section, "All books").groupby(["section", "short_book"])["n_words"].sum()
              .reset_index())
        fig = px.sunburst(sb, path=["section", "short_book"], values="n_words",
                          title="Where the words are — sections and books by length",
                          color_discrete_sequence=SERIES)
        fig.update_traces(hovertemplate="<b>%{label}</b><br>%{value:,} words<extra></extra>",
                          marker=dict(line=dict(width=2)))
        st.plotly_chart(style_fig(fig, 560), key="sunburst")

    f1, f2 = st.columns(2)
    with f1:
        fig = go.Figure([go.Box(x=[r.scripture], q1=[r.q1], median=[r.median], q3=[r.q3], mean=[r.mean],
                                lowerfence=[r.lo], upperfence=[r.hi], name=r.scripture, marker_color=COLORS[r.scripture],
                                boxmean=True) for r in length_quantiles().itertuples()])
        fig.update_layout(showlegend=False, title="Verse length by scripture", yaxis_title="Words per verse")
        st.plotly_chart(style_fig(fig, 420), key="box_len")
    with f2:
        tone = tone_c(scripture, version, section)
        lim = max(abs(tone["per1k"]).max(), 1)
        fig = go.Figure(go.Bar(x=tone["short_book"], y=tone["per1k"], marker=dict(
            color=tone["per1k"], cmin=-lim, cmax=lim, line_width=0,
            colorscale=[[0, "#e34948"], [0.5, "#c9c8c3"], [1, "#2a78d6"]]),
            hovertemplate="%{x}: %{y:+.1f} per 1k words<extra></extra>"))
        fig.update_layout(title="Tone arc — uplifting (blue) vs. stern (red) words per 1k")
        st.plotly_chart(style_fig(fig, 420), key="tone")
    st.caption("The tone arc is a simple word-list heuristic (words like mercy, joy and light vs. wrath, sword "
               "and death). It's for exploration only, not a judgement of any text.")

# ======================================================================================
# 6. COMPARE TRANSLATIONS
# ======================================================================================
with tabs[5]:
    st.subheader(f"One verse, every {scripture} translation")
    def random_compare():
        pool_ = an.nice_verses(books_df)
        pool_ = pool_ if len(pool_) else books_df
        # Every book (surah) is equally likely, however many verses it has.
        r = pool_.sample(1, weights=1.0 / pool_.groupby("book")["book"].transform("size")).iloc[0]
        st.session_state.cmp_book, st.session_state.cmp_ch, st.session_state.cmp_v = \
            r.book, int(r.chapter), int(r.verse)

    guard("cmp_book", rbooks)
    c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
    cbook = c1.selectbox(unit, rbooks, index=rbooks.index(book) if book in rbooks else 0, key="cmp_book")
    cb = df[df["book"] == cbook]
    cchs = [int(c) for c in sorted(cb["chapter"].unique())]
    guard("cmp_ch", cchs)
    cch = c2.selectbox("Chapter", cchs, key="cmp_ch",
                       disabled=scripture == "Quran")
    cvs = [int(v) for v in sorted(cb[cb["chapter"] == cch]["verse"].unique())]
    guard("cmp_v", cvs)
    cv = c3.selectbox("Verse", cvs, key="cmp_v")
    c4.write("")
    c4.button("🎲 Random verse", **STRETCH, on_click=random_compare)

    # The chosen translation first; in the others the same verse may carry another number (JPS 1917 follows the
    # Hebrew numbering, the English Bibles the English one), so each is located through the Hebrew text.
    found, renumbered = [], False
    for v in [version] + [x for x in versions if x != version]:
        bd = get(scripture, v)
        bd = bd[bd["book"] == cbook]
        refs = aligned_refs(scripture, version, v, cbook, cch, cv)
        m = bd[[(c, x) in refs for c, x in zip(bd["chapter"], bd["verse"])]].sort_values(["chapter", "verse"])
        if not len(m):
            continue
        r = m.iloc[0].to_dict()
        if len(m) > 1:
            last = m.iloc[-1]
            r.update(text=" ".join(m["text"]), n_words=int(m["n_words"].sum()),
                     ref=r["ref"] + (f"–{last.verse}" if last.chapter == r["chapter"] else f"–{last.chapter}:{last.verse}"))
            if last.chapter == r["chapter"]:
                r.update(verse_first=int(r["verse"]), verse_last=int(last.verse))
        renumbered |= refs != [(cch, cv)]
        found.append(r)
    if renumbered:
        st.caption("ℹ️ This verse has a different number in some translations: JPS 1917 follows the Hebrew "
                   "numbering, the English Bibles the English one. Each card shows that translation's own reference.")
    if scripture == "Bible" and cbook not in NEW_TESTAMENT and any(numbering(scripture, r["version"]) == "vulgate"
                                                                   for r in found):
        st.caption("ℹ️ Douay-Rheims follows the Latin Vulgate's numbering (e.g. most Psalms are one number lower), "
                   "so its verse here may not be the same one.")
    if found:
        o = original_for(found[0])
        if o and o.get("text"):
            st.markdown(f'<div class="verse-card" style="--accent:{accent}"><div class="meta">Original</div>'
                        f'{original_html(o)}</div>', unsafe_allow_html=True)
        for lang in active_langs():
            c = companion_for(found[0], lang)
            if c and c.get("text"):
                st.markdown(f'<div class="verse-card" style="--accent:{accent}"><div class="meta">{lang}</div>'
                            f'{original_html(c)}</div>', unsafe_allow_html=True)
    for i, r in enumerate(found):
        st.markdown(verse_html(r, with_original=False), unsafe_allow_html=True)
    if found:
        lens = pd.DataFrame({"version": [r["version"] for r in found], "words": [r["n_words"] for r in found]})
        fig = px.bar(lens, x="words", y="version", orientation="h", text="words",
                     title="Words used by each translation for this verse", labels={"version": "", "words": "Words"})
        fig.update_traces(marker_color=accent, marker_line_width=0, textposition="outside")
        st.plotly_chart(style_fig(fig, 120 + 40 * len(found)), key="cmp_len")
        sets = [set(an.tokenize(r["text"])) - an.stopwords() for r in found]
        shared = set.intersection(*sets) if sets else set()
        if shared:
            st.markdown("**Words every translation agrees on:** " + " · ".join(f"`{w}`" for w in sorted(shared)))

# ======================================================================================
# 7. COLLECTION
# ======================================================================================
with tabs[6]:
    st.subheader("⭐ My collection")
    favs = st.session_state.favs
    if not favs:
        st.info("Nothing saved yet. Use **⭐ Save** on any verse to build your collection.")
    else:
        style = st.selectbox("Quote-card style", qc.STYLES, key="card_style",
                             help="Scripture theme: a background drawn for each scripture, with its own shade "
                                  "and pattern for every book.")
        for i, f in enumerate(favs):
            fid = re.sub(r"\W+", "_", f["ref"] + "_" + f["version"])  # stable key, survives removing others
            st.markdown(verse_html(f), unsafe_allow_html=True)
            a, b, _ = st.columns([1, 1, 4])
            show_card = card_toggle(f"fav_{fid}", a)
            if b.button("🗑️ Remove", key=f"rm_{fid}", **STRETCH):
                favs.pop(i)
                st.rerun()
            if show_card:
                card_panel(f, style)
        md = "\n\n".join(f"> {f['text']}\n>\n" + (f"> {f['original']}\n>\n" if f.get("original") else "")
                           + "".join(f"> {f[k.lower()]}\n>\n" for k in comp.LANGS if f.get(k.lower()))
                           + f"> — **{f['ref']}** ({f['version']})" for f in favs)
        x1, x2, _ = st.columns([1, 1, 3])
        download_link("⬇️ Export as Markdown", md.encode(), "my_verses.md", "text/markdown", target=x1)
        download_link("⬇️ Export as CSV", pd.DataFrame(favs).to_csv(index=False).encode(),
                      "my_verses.csv", "text/csv", target=x2)

