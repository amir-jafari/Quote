"""
Data layer for the Sacred Words Explorer.

Downloads public scripture texts once, normalises them into one tidy table
(one row per verse) and caches the result as Parquet under ./data.

Sources
  * Bible / Tanakh : github.com/scrollmapper/bible_databases (public-domain translations)
  * Quran          : tanzil.net translations (full punctuation kept; surah names from fawazahmed0/quran-api)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BIBLE_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/{code}.json"
QURAN_URL = "https://tanzil.net/trans/?transID={code}&type=txt-2"
QURAN_INFO_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/info.json"

# --------------------------------------------------------------------------------------
# Catalogue: scripture -> {display name: source code}
# --------------------------------------------------------------------------------------
CATALOG: dict[str, dict] = {
    "Quran": {
        "icon": "☪️",
        "color": "#0f9d76",
        "unit": "Surah",
        "versions": {
            "Saheeh International": "en.sahih",
            "Pickthall": "en.pickthall",
            "Yusuf Ali": "en.yusufali",
            "Talal Itani (The Clear Quran)": "en.itani",
            "Ali Quli Qarai": "en.qarai",
            "Muhammad Sarwar": "en.sarwar",
        },
    },
    "Bible": {
        "icon": "✝️",
        "color": "#4263eb",
        "unit": "Book",
        "versions": {
            "King James Version (KJV)": "KJV",
            "American Standard Version (ASV)": "ASV",
            "Bible in Basic English (BBE)": "BBE",
            "Young's Literal Translation (YLT)": "YLT",
            "Darby Translation": "Darby",
            "Webster Bible": "Webster",
            "Douay-Rheims (DRC, with Deuterocanon)": "DRC",
            "Geneva Bible 1599": "Geneva1599",
        },
    },
    "Torah": {
        "icon": "✡️",
        "color": "#d08c16",
        "unit": "Book",
        "versions": {
            "JPS 1917 (Jewish Publication Society)": "JPS",
            "King James Version (KJV)": "KJV",
            "Young's Literal Translation (YLT)": "YLT",
            "American Standard Version (ASV)": "ASV",
        },
    },
}

# Default version per scripture used for cross-scripture statistics
DEFAULT_VERSION = {
    "Quran": "Saheeh International",
    "Bible": "Webster Bible",
    "Torah": "JPS 1917 (Jewish Publication Society)",
}

TORAH_BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
NEVIIM = ["Joshua", "Judges", "I Samuel", "II Samuel", "I Kings", "II Kings", "Isaiah",
          "Jeremiah", "Ezekiel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
          "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"]
KETUVIM = ["Psalms", "Proverbs", "Job", "Song of Solomon", "Ruth", "Lamentations",
           "Ecclesiastes", "Esther", "Daniel", "Ezra", "Nehemiah", "I Chronicles", "II Chronicles"]
TANAKH_ORDER = TORAH_BOOKS + NEVIIM + KETUVIM

NEW_TESTAMENT = ["Matthew", "Mark", "Luke", "John", "Acts", "Romans", "I Corinthians",
                 "II Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
                 "I Thessalonians", "II Thessalonians", "I Timothy", "II Timothy", "Titus",
                 "Philemon", "Hebrews", "James", "I Peter", "II Peter", "I John", "II John",
                 "III John", "Jude", "Revelation of John"]
GOSPELS = NEW_TESTAMENT[:4]

_TAG_RE = re.compile(r"<[^>]+>|[¶‹›]|\{[^}]*\}")


def _clean(text: str) -> str:
    text = _TAG_RE.sub("", str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _fetch_json(url: str) -> dict:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------------------
# Quran
# --------------------------------------------------------------------------------------
def quran_surah_info() -> pd.DataFrame:
    path = DATA_DIR / "quran_info.parquet"
    if path.exists():
        return pd.read_parquet(path)
    info = _fetch_json(QURAN_INFO_URL)
    rows = [{
        "chapter": c["chapter"],
        "name": c["name"],
        "englishname": c["englishname"],
        "arabicname": c["arabicname"],
        "revelation": c["revelation"],
        "n_verses": len(c["verses"]),
    } for c in info["chapters"]]
    df = pd.DataFrame(rows)
    df.to_parquet(path)
    return df


def _load_quran(code: str) -> pd.DataFrame:
    resp = requests.get(QURAN_URL.format(code=code), timeout=120)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    rows = []
    for line in resp.text.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append({"chapter": int(parts[0]), "verse": int(parts[1]), "text": parts[2]})
    if len(rows) != 6236:
        raise ValueError(f"Quran translation {code}: expected 6236 verses, got {len(rows)}")
    df = pd.DataFrame(rows)
    info = quran_surah_info().set_index("chapter")
    df["text"] = df["text"].map(_clean)
    df["book_num"] = df["chapter"]
    df["book"] = df["chapter"].map(lambda c: f"{c}. {info.at[c, 'name']} ({info.at[c, 'englishname']})")
    df["section"] = df["chapter"].map(lambda c: "Meccan" if info.at[c, "revelation"] == "Mecca" else "Medinan")
    # In the Quran each surah is the unit; "chapter" = surah, kept for a uniform schema
    df["ref"] = df.apply(lambda r: f"Quran {r.chapter}:{r.verse}", axis=1)
    df["short_book"] = df["chapter"].map(lambda c: info.at[c, "name"])
    return df


# --------------------------------------------------------------------------------------
# Bible / Torah
# --------------------------------------------------------------------------------------
def _bible_rows(code: str) -> list[dict]:
    raw_path = DATA_DIR / f"raw_bible_{code}.json"
    if raw_path.exists():
        data = json.loads(raw_path.read_text(encoding="utf-8"))
    else:
        data = _fetch_json(BIBLE_URL.format(code=code))
        raw_path.write_text(json.dumps(data), encoding="utf-8")
    rows = []
    for bi, book in enumerate(data["books"], start=1):
        for ch in book["chapters"]:
            for v in ch["verses"]:
                rows.append({"book": book["name"], "book_order": bi, "chapter": int(ch["chapter"]),
                             "verse": int(v["verse"]), "text": _clean(v["text"])})
    return rows


def _bible_section(book: str, kjv_books: set[str]) -> str:
    if book in TORAH_BOOKS:
        return "Old Testament — Law"
    if book in NEW_TESTAMENT:
        return "New Testament — Gospels" if book in GOSPELS else "New Testament — Epistles & Acts"
    if book in kjv_books:
        return "Old Testament — History, Wisdom & Prophets"
    return "Deuterocanon / Apocrypha"


def _tanakh_section(book: str) -> str:
    if book in TORAH_BOOKS:
        return "Torah (Five Books of Moses)"
    if book in NEVIIM:
        return "Nevi'im (Prophets)"
    return "Ketuvim (Writings)"


def _load_bible(code: str) -> pd.DataFrame:
    df = pd.DataFrame(_bible_rows(code))
    kjv = set(TANAKH_ORDER) | set(NEW_TESTAMENT)
    df["section"] = df["book"].map(lambda b: _bible_section(b, kjv))
    df["book_num"] = df["book_order"]
    return df.drop(columns="book_order")


def _load_torah(code: str) -> pd.DataFrame:
    df = pd.DataFrame(_bible_rows(code))
    df = df[df["book"].isin(TANAKH_ORDER)].copy()
    df["book_num"] = df["book"].map({b: i for i, b in enumerate(TANAKH_ORDER, start=1)})
    df["section"] = df["book"].map(_tanakh_section)
    return df.drop(columns="book_order").sort_values(["book_num", "chapter", "verse"])


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
# A verse reads as a complete sentence when it starts like a sentence and ends with . ! or ?
# (optionally followed by closing quotes/brackets). Verses ending in , ; : or a dash
# continue into the next verse.
_START_RE = r"^[\"'“‘(\[]*[A-Z0-9]"
_END_RE = r"[.!?][\"'”’)\]]*\s*$"


def add_completeness(df: pd.DataFrame) -> pd.DataFrame:
    df["starts"] = df["text"].str.contains(_START_RE, regex=True)
    df["ends"] = df["text"].str.contains(_END_RE, regex=True)
    df["complete"] = df["starts"] & df["ends"]
    return df


def load_version(scripture: str, version: str) -> pd.DataFrame:
    """Return a verse table with columns:
    scripture, version, book_num, book, short_book, section, chapter, verse, text, ref, n_words"""
    code = CATALOG[scripture]["versions"][version]
    path = DATA_DIR / f"{scripture.lower()}_{code}.parquet"
    if path.exists():
        return add_completeness(pd.read_parquet(path))

    if scripture == "Quran":
        df = _load_quran(code)
    else:
        df = _load_bible(code) if scripture == "Bible" else _load_torah(code)
        df["short_book"] = df["book"]
        df["ref"] = df["book"] + " " + df["chapter"].astype(str) + ":" + df["verse"].astype(str)

    df = df[df["text"].str.len() > 0].copy()
    df["scripture"] = scripture
    df["version"] = version
    df["n_words"] = df["text"].str.split().str.len()
    cols = ["scripture", "version", "book_num", "book", "short_book", "section",
            "chapter", "verse", "text", "ref", "n_words"]
    df = df[cols].reset_index(drop=True)
    df.to_parquet(path)
    return add_completeness(df)


def is_arabic(version: str) -> bool:
    return version.startswith("Arabic")


if __name__ == "__main__":
    # Pre-download everything: python data_loader.py
    for s, meta in CATALOG.items():
        for v in meta["versions"]:
            d = load_version(s, v)
            print(f"{s:6} | {v:45} | {len(d):6,} verses | {d.n_words.sum():9,} words")
