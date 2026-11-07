"""
📜 Sacred Words Explorer
Read, search, discover and visualise the Quran, the Bible and the Torah — in English.

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

import analytics as an
import originals as orig
from data_loader import CATALOG, DEFAULT_VERSION, NEW_TESTAMENT, load_version

st.set_page_config(page_title="Sacred Words Explorer", page_icon="📜", layout="wide",
                   initial_sidebar_state="expanded")


# --------------------------------------------------------------------------------------
# Password gate: the password comes from st.secrets["APP_PASSWORD"]
# (.streamlit/secrets.toml locally, the app's "Secrets" settings on Streamlit Cloud)
# --------------------------------------------------------------------------------------
def _check_password() -> bool:
    import hmac

    if st.session_state.get("password_ok"):
        return True
    try:
        expected = st.secrets["APP_PASSWORD"]
    except Exception:  # missing key or no secrets file
        st.error("This app is locked: no `APP_PASSWORD` is configured in its secrets.")
        return False

    def _entered():
        ok = hmac.compare_digest(st.session_state.get("pw_input", ""), str(expected))
        st.session_state["password_ok"] = ok
        st.session_state["pw_failed"] = not ok
        st.session_state.pop("pw_input", None)

    st.markdown("## 📜 Sacred Words Explorer")
    st.text_input("Password", type="password", key="pw_input", on_change=_entered)
    if st.session_state.get("pw_failed"):
        st.error("Incorrect password.")
    return False


if not _check_password():
    st.stop()

SCRIPTURES = list(CATALOG)
COLORS = {s: CATALOG[s]["color"] for s in SCRIPTURES}
# Validated categorical order for multi-word charts (fixed order, never cycled)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MAX_WORDS = len(SERIES)

# --------------------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600;700&family=Amiri+Quran&family=Amiri:wght@400;700&family=Noto+Serif+Hebrew:wght@400;500&display=swap" rel="stylesheet">
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
.verse-card.big .orig { font-size: 2.15rem; }
.olabel { font-size: .74rem; color: var(--muted); text-align: right; margin-top: 2px; }
.rgrid { display: grid; grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); column-gap: 28px; }
.rgrid > div { padding: 9px 0; border-bottom: 1px solid var(--card-border); }
.rgrid .head { font-family: 'Inter', sans-serif; font-size: .78rem; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: .05em; border-bottom: 2px solid var(--accent); }
.rgrid .orig { margin: 0; padding: 9px 0; border-top: none; font-size: 1.45rem; line-height: 1.9; }
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
    img.convert("RGB").save(buf, format="PNG")
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
def quote_png(text: str, ref: str, style: str) -> bytes:
    return an.quote_card(text, ref, style)


@st.cache_data(show_spinner=False)
def theme_table() -> pd.DataFrame:
    alld = get_defaults()
    rows = []
    for t in an.THEMES:
        m = alld["text"].str.contains(an.theme_pattern(t), case=False, regex=True)
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
    alld = get_defaults()
    return alld[["scripture", "n_words"]]


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
    if not st.session_state.get("show_orig", True) or "chapter" not in row:
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


def original_html(o: dict | None) -> str:
    if not o:
        return ""
    body = (f'<div class="orig {o["lang"]}" lang="{o["lang"]}">{html.escape(o["text"])}</div>'
            if o.get("text") else "")
    return body + f'<div class="olabel">{html.escape(o["label"])}</div>'


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
               with_original: bool = True) -> str:
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
            f'<div class="meta">{html.escape(meta)}</div>{original_html(original_for(row)) if with_original else ""}</div>')


def add_fav(row):
    row = as_sentence(row)
    item = {k: row[k] for k in ["scripture", "version", "ref", "text", "section", "book", "chapter", "verse"]}
    item.update({k: row[k] for k in ["verse_first", "verse_last"] if k in row})
    o = original_for(row)
    item["original"] = o.get("text", "") if o else ""
    if item["ref"] + item["version"] not in {f["ref"] + f["version"] for f in st.session_state.favs}:
        st.session_state.favs.append(item)
        st.toast(f"Saved {item['ref']} to your collection ⭐")
    else:
        st.toast("Already in your collection")


def verse_actions(row, key: str, card: bool = True):
    row = as_sentence(row)
    c1, c2, _ = st.columns([1, 1, 3])
    c1.button("⭐ Save", key=f"fav_{key}", on_click=add_fav, args=(row,), use_container_width=True)
    if card:
        style = {"Quran": "Emerald", "Bible": "Royal", "Torah": "Gold"}[row["scripture"]]
        download_link("🖼️ Quote card", quote_png(row["text"], row["ref"], style),
                      f"{row['ref'].replace(' ', '_').replace(':', '-')}.png", "image/png",
                      target=c2, full_width=True)


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
    st.toggle("Show Arabic / Hebrew original", True, key="show_orig",
              help="Arabic for the Quran; Hebrew for the Torah and the Old Testament.")
    if scripture != "Quran" and st.session_state.get("show_orig", True):
        st.radio("Hebrew marks", ["Vowels only", "Vowels & cantillation", "Consonants only"], key="heb_marks",
                 help="Cantillation marks are the chanting accents; consonant-only text is how a Torah scroll is written.")
    st.divider()
    st.markdown(f"**⭐ Collection:** {len(st.session_state.favs)} saved")
    with st.expander("ℹ️ About & sources"):
        st.markdown(
            "- **Quran** (English translations): tanzil.net, with full punctuation\n"
            "- **Bible & Torah/Tanakh** (public-domain translations): `scrollmapper/bible_databases`\n"
            "- **Arabic Quran**: Uthmani script from tanzil.net\n"
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
  <p>Discover, read, compare and visualise the words of the Quran, the Bible and the Torah — all in English.</p>
  <div class="chips"><span>☪️ Quran</span><span>✝️ Bible</span><span>✡️ Torah</span>
  <span>📚 {n_versions} translations</span><span>📖 {tot_verses:,} verses</span></div>
</div>""", unsafe_allow_html=True)

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
    draw = b1.button("✨ Inspire me", type="primary", use_container_width=True)
    daily = b2.button("📅 Verse of the day", use_container_width=True)

    if source == "Any scripture":
        pool = pd.concat([nice_pool(s, DEFAULT_VERSION[s]) for s in SCRIPTURES])
    else:
        pool = an.nice_verses(scope)
        if pool.empty:
            pool = scope
    pool = an.theme_filter(pool, theme)

    # Redraw automatically whenever the sidebar selection (or theme / source) changes,
    # so the verse always comes from what is currently selected.
    ctx = (theme, source) if source == "Any scripture" else (theme, source, scripture, version, section, book)
    changed = st.session_state.get("pick_ctx") != ctx
    if draw or daily or changed or st.session_state.pick is None:
        st.session_state.pick_ctx = ctx
        if pool.empty:
            st.warning("No verse matches that theme in this selection. Try another theme or a wider selection.")
        else:
            seed = int(dt.date.today().strftime("%Y%m%d")) if daily else None
            st.session_state.pick = pool.sample(1, random_state=seed).iloc[0].to_dict()

    if st.session_state.pick:
        pick = st.session_state.pick
        pat = an.theme_pattern(theme) if theme != "Any" else None
        st.markdown(verse_html(pick, big=True, pattern=pat), unsafe_allow_html=True)
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
                # Match the sidebar translation only when the user picked a non-default one
                # that this scripture also has (KJV / ASV / YLT); otherwise keep its default,
                # so the Torah stays on JPS 1917 while the Bible is on its default KJV.
                picked = version != DEFAULT_VERSION[scripture]
                v = version if picked and version in CATALOG[s]["versions"] else DEFAULT_VERSION[s]
                p = an.theme_filter(nice_pool(s, v), trio_theme)
            picks.append(p.sample(1).iloc[0].to_dict() if len(p) else None)
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
    r1, r2, r3, r4 = st.columns([3, 1, 3, 2])
    rbooks = list(dict.fromkeys(books_df.sort_values("book_num")["book"]))
    guard("read_book", rbooks)
    rbook = r1.selectbox(unit, rbooks, index=rbooks.index(book) if book in rbooks else 0, key="read_book")
    bdf = df[df["book"] == rbook]
    chapters = [int(c) for c in sorted(bdf["chapter"].unique())]
    guard("read_ch", chapters)
    if scripture == "Quran":
        rch = chapters[0]
        r2.metric("Verses", len(bdf))
    else:
        rch = r2.selectbox("Chapter", chapters, key="read_ch")
    others = ["— none —"] + [v for v in versions if v != version]
    parallel = r3.selectbox("Side-by-side with", others, key="read_par")
    hl = r4.text_input("Highlight word", key="read_hl", placeholder="e.g. light")
    pat = an.word_pattern(hl, True) if hl.strip() else None

    chap = bdf[bdf["chapter"] == rch].sort_values("verse")
    title = rbook if scripture == "Quran" else f"{rbook} {rch}"

    def reader_grid(frames: list[tuple[str, pd.DataFrame]]) -> str:
        """Verse-by-verse grid: one column per English version plus the original language."""
        base = frames[0][1]
        others = [f.set_index("verse")["text"] for _, f in frames[1:]]
        origs = [original_for(r) for r in base.to_dict("records")]
        has_orig = any(o and o.get("text") for o in origs)
        lang = next((o["lang"] for o in origs if o and o.get("text")), "")
        heads = [lbl for lbl, _ in frames] + (
            ["Arabic original" if lang == "ar" else "Hebrew original"] if has_orig else [])
        cells = "".join(f'<div class="head">{html.escape(h)}</div>' for h in heads)
        for (_, r), o in zip(base.iterrows(), origs):
            cells += f'<div><sup>{r.verse}</sup>{highlight(r.text, pat)}</div>'
            for s_ in others:
                cells += f'<div><sup>{r.verse}</sup>{highlight(s_.get(r.verse, ""), pat)}</div>'
            if has_orig:
                cells += (f'<div class="orig {o["lang"]}" lang="{o["lang"]}">{html.escape(o["text"])}</div>'
                          if o and o.get("text") else "<div></div>")
        note = next((o["label"] for o in origs if o and not o.get("text")), "")
        return (f'<div class="reader" style="--accent:{accent}"><h3 style="font-family:Cormorant Garamond,serif;'
                f'margin:.2rem 0 .8rem">{html.escape(title)}</h3>'
                f'<div class="rgrid" style="--cols:{len(heads)}">{cells}</div>'
                + (f'<div class="olabel" style="margin-top:10px">{html.escape(note)}</div>' if note else "")
                + "</div>")

    def reader(frame, label):
        body = " ".join(f"<sup>{v}</sup>{highlight(t, pat)}" for v, t in zip(frame.verse, frame.text))
        return (f'<div class="reader" style="--accent:{accent}"><div class="badge" style="--accent:{accent}">'
                f'{html.escape(label)}</div><h3 style="font-family:Cormorant Garamond,serif;margin:.4rem 0 1rem">'
                f'{html.escape(title)}</h3>{body}</div>')

    if st.session_state.get("show_orig", True):
        frames = [(version, chap)]
        if parallel != "— none —":
            pdf = get(scripture, parallel)
            frames.append((parallel, pdf[(pdf["book"] == rbook) & (pdf["chapter"] == rch)].sort_values("verse")))
        st.markdown(reader_grid(frames), unsafe_allow_html=True)
    elif parallel == "— none —":
        st.markdown(reader(chap, version), unsafe_allow_html=True)
    else:
        pdf = get(scripture, parallel)
        pchap = pdf[(pdf["book"] == rbook) & (pdf["chapter"] == rch)].sort_values("verse")
        a, b = st.columns(2)
        a.markdown(reader(chap, version), unsafe_allow_html=True)
        b.markdown(reader(pchap, parallel), unsafe_allow_html=True)

    st.write("")
    with st.expander("⭐ Save a verse from this chapter"):
        guard("read_vsel", chap["verse"].tolist())
        vnum = st.selectbox("Verse", chap["verse"].tolist(), key="read_vsel")
        vrow = as_sentence(chap[chap["verse"] == vnum].iloc[0])
        st.markdown(verse_html(vrow), unsafe_allow_html=True)
        verse_actions(vrow, "read")

# ======================================================================================
# 3. SEARCH
# ======================================================================================
with tabs[2]:
    st.subheader("Search the scriptures")
    s1, s2, s3 = st.columns([4, 2, 2])
    q = s1.text_input("Word or phrase", placeholder="e.g. light upon light, patience, the good shepherd",
                      key="q")
    where = s2.selectbox("Where", ["Current selection", "All three scriptures"], key="q_where")
    mode = s3.selectbox("Match", ["Word & its forms", "Exact word", "Anywhere in text"], key="q_mode")
    whole = st.toggle("Show full sentences (join verses that continue into the next one)", True, key="q_whole")
    if q.strip():
        if mode == "Anywhere in text":
            qpat = re.escape(q.strip()).replace(r"\ ", r"\s+")
        else:
            qpat = an.word_pattern(q, mode == "Word & its forms")
        base = get_defaults() if where == "All three scriptures" else scope
        hits = base[base["text"].str.contains(qpat, case=False, regex=True)]
        m1, m2, m3 = st.columns(3)
        stat_tile(m1, f"{len(hits):,}", "matching verses")
        stat_tile(m2, f"{hits['book'].nunique():,}", f"{'books / surahs' if where != 'Current selection' else unit.lower() + 's'}")
        stat_tile(m3, f"{(len(hits) / max(len(base), 1) * 100):.2f}%", "of verses in scope")
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
                st.markdown(verse_html(as_sentence(r) if whole else dict(r), pattern=qpat),
                            unsafe_allow_html=True)
            download_link("⬇️ Download all results (CSV)",
                          hits[["scripture", "version", "ref", "text"]].to_csv(index=False).encode(),
                          f"search_{q.strip().replace(' ', '_')}.csv", "text/csv")
        else:
            st.info("No matches. Try “Word & its forms” or a wider scope.")
    else:
        st.info("Type a word above. Try **mercy**, **light**, **neighbour**, **orphan**, **garden** or **covenant**.")

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
        fig = px.box(length_quantiles(), x="scripture", y="n_words", color="scripture", color_discrete_map=COLORS,
                     points=False, title="Verse length by scripture", labels={"n_words": "Words per verse",
                                                                             "scripture": ""})
        fig.update_layout(showlegend=False)
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
        r = (pool_ if len(pool_) else books_df).sample(1).iloc[0]
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
    c4.button("🎲 Random verse", use_container_width=True, on_click=random_compare)

    found = []
    for v in versions:
        vd = get(scripture, v)
        m = vd[(vd["book"] == cbook) & (vd["chapter"] == cch) & (vd["verse"] == cv)]
        if len(m):
            found.append(m.iloc[0].to_dict())
    if found:
        o = original_for(found[0])
        if o and o.get("text"):
            st.markdown(f'<div class="verse-card" style="--accent:{accent}"><div class="meta">Original</div>'
                        f'{original_html(o)}</div>', unsafe_allow_html=True)
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
        style = st.selectbox("Quote-card style", list(an.CARD_STYLES), key="card_style")
        for i, f in enumerate(favs):
            st.markdown(verse_html(f), unsafe_allow_html=True)
            a, b, _ = st.columns([1, 1, 4])
            download_link("🖼️ Quote card", quote_png(f["text"], f["ref"], style),
                          f"{f['ref'].replace(' ', '_').replace(':', '-')}.png", "image/png",
                          target=a, full_width=True)
            if b.button("🗑️ Remove", key=f"rm_{i}", use_container_width=True):
                favs.pop(i)
                st.rerun()
        md = "\n\n".join(f"> {f['text']}\n>\n" + (f"> {f['original']}\n>\n" if f.get("original") else "")
                           + f"> — **{f['ref']}** ({f['version']})" for f in favs)
        x1, x2, _ = st.columns([1, 1, 3])
        download_link("⬇️ Export as Markdown", md.encode(), "my_verses.md", "text/markdown", target=x1)
        download_link("⬇️ Export as CSV", pd.DataFrame(favs).to_csv(index=False).encode(),
                      "my_verses.csv", "text/csv", target=x2)
        st.write("")
        with st.expander("👀 Preview a quote card"):
            sel = st.selectbox("Verse", range(len(favs)), format_func=lambda j: favs[j]["ref"], key="prev_sel")
            show_png(quote_png(favs[sel]["text"], favs[sel]["ref"], style), width=420)
