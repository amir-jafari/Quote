"""
Original-language texts shown next to the English:

  * Quran  -> Arabic, Uthmani script (tanzil.net). Verse numbering is identical in every translation.
  * Hebrew Bible (Torah / Bible Old Testament) -> Hebrew, Westminster Leningrad Codex (WLC).

The WLC uses Hebrew verse numbering, as does JPS 1917. English Bibles (KJV, ASV, ...) number some
passages differently, e.g. KJV Malachi 4:1 = Hebrew Malachi 3:19 and KJV Joel 2:28 = Hebrew Joel 3:1.
English references are converted with the standard English -> original versification table published
by the Copenhagen Alliance (the mapping Paratext uses).
"""
from __future__ import annotations

import json
import re

import pandas as pd
import requests

from data_loader import CATALOG, DATA_DIR, NEW_TESTAMENT, _bible_rows

ARABIC_URL = "https://tanzil.net/pub/download/index.php?quranType=uthmani&outType=txt-2&agree=true&marks=true&sajdah=true"
WLC_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/WLC.json"
JPS_VERSION = "JPS 1917 (Jewish Publication Society)"

ARABIC_LABEL = "Arabic · Uthmani script (Tanzil)"
HEBREW_LABEL = "Hebrew · Westminster Leningrad Codex"


# --------------------------------------------------------------------------------------
# Arabic Quran
# --------------------------------------------------------------------------------------
def load_arabic() -> dict[tuple[int, int], str]:
    path = DATA_DIR / "original_quran_arabic.parquet"
    if not path.exists():
        resp = requests.get(ARABIC_URL, timeout=120)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        rows = []
        for line in resp.text.splitlines():
            p = line.split("|", 2)
            if len(p) == 3 and p[0].isdigit() and p[1].isdigit():
                rows.append({"chapter": int(p[0]), "verse": int(p[1]), "text": p[2].strip()})
        if len(rows) != 6236:
            raise ValueError(f"Arabic Quran: expected 6236 verses, got {len(rows)}")
        pd.DataFrame(rows).to_parquet(path)
    df = pd.read_parquet(path)
    return {(c, v): t for c, v, t in zip(df.chapter, df.verse, df.text)}


# --------------------------------------------------------------------------------------
# Hebrew Bible
# --------------------------------------------------------------------------------------
_MASORETIC_NOTE = re.compile(r"\s(?:[0-9]+|X)(?=\s|$)")  # verse counts printed at the end of some books


def load_hebrew() -> dict[tuple[str, int, int], str]:
    """(book, chapter, verse) in Hebrew numbering -> pointed Hebrew text."""
    path = DATA_DIR / "original_hebrew_wlc.parquet"
    if not path.exists():
        data = requests.get(WLC_URL, timeout=180).json()
        rows = [{"book": b["name"], "chapter": int(c["chapter"]), "verse": int(v["verse"]),
                 "text": _MASORETIC_NOTE.sub("", " " + v["text"]).strip()}
                for b in data["books"] for c in b["chapters"] for v in c["verses"]]
        pd.DataFrame(rows).to_parquet(path)
    df = pd.read_parquet(path)
    return {(b, c, v): t for b, c, v, t in zip(df.book, df.chapter, df.verse, df.text)}


VRS_URL = ("https://raw.githubusercontent.com/Copenhagen-Alliance/versification-specification/master/"
           "versification-mappings/standard-mappings/eng.json")
USFM = {"Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM", "Deuteronomy": "DEU",
        "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT", "I Samuel": "1SA", "II Samuel": "2SA",
        "I Kings": "1KI", "II Kings": "2KI", "I Chronicles": "1CH", "II Chronicles": "2CH", "Ezra": "EZR",
        "Nehemiah": "NEH", "Esther": "EST", "Job": "JOB", "Psalms": "PSA", "Proverbs": "PRO",
        "Ecclesiastes": "ECC", "Song of Solomon": "SNG", "Isaiah": "ISA", "Jeremiah": "JER",
        "Lamentations": "LAM", "Ezekiel": "EZK", "Daniel": "DAN", "Hosea": "HOS", "Joel": "JOL",
        "Amos": "AMO", "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC", "Nahum": "NAM", "Habakkuk": "HAB",
        "Zephaniah": "ZEP", "Haggai": "HAG", "Zechariah": "ZEC", "Malachi": "MAL"}
BOOK_OF = {v: k for k, v in USFM.items()}

# Versions numbered like the Hebrew text (identity) vs. like the English Bible (needs the table).
HEBREW_NUMBERED = {"JPS"}
NO_HEBREW = {"DRC": "Douay-Rheims follows the Latin Vulgate's numbering, so it isn't paired with the Hebrew."}

_REF = re.compile(r"^([1-4A-Z]{3}) (\d+):(\d+)(?:-(\d+))?$")


def _english_to_hebrew_table() -> dict[tuple[str, int, int], tuple[int, int]]:
    """Standard English -> original (Hebrew) versification (Copenhagen Alliance / Paratext 'eng' mapping)."""
    path = DATA_DIR / "versification_eng.json"
    if not path.exists():
        path.write_text(requests.get(VRS_URL, timeout=60).text, encoding="utf-8")
    mapped = json.loads(path.read_text(encoding="utf-8"))["mappedVerses"]
    table = {}
    for k, v in mapped.items():
        a, b = _REF.match(k), _REF.match(v)
        if not a or not b or a.group(1) not in BOOK_OF or a.group(1) != b.group(1):
            continue  # Greek additions (e.g. ESG 1:1a) or cross-book entries
        book = BOOK_OF[a.group(1)]
        c1, v1, v1e = int(a.group(2)), int(a.group(3)), int(a.group(4) or a.group(3))
        c2, v2 = int(b.group(2)), int(b.group(3))
        for i in range(v1e - v1 + 1):
            table[(book, c1, v1 + i)] = (c2, v2 + i)
    return table


def _to_hebrew(table, book: str, c: int, v: int) -> list[tuple[int, int]]:
    if book == "Psalms" and v == 1 and (book, c, 0) in table:
        # English editions merge the psalm heading (verse 0) into verse 1; Hebrew numbers the heading as
        # verse 1 (sometimes 1-2), so English v1 = Hebrew 1 .. (Hebrew of English v1).
        hc, hv = table.get((book, c, 1), (c, 1))
        return [(hc, i) for i in range(1, hv + 1)]
    return [table.get((book, c, v), (c, v))]


def hebrew_map(code: str) -> pd.DataFrame:
    """For an English Bible source (KJV, ASV, JPS, ...): book, chapter, verse -> heb_refs ("3:1|3:2")."""
    path = DATA_DIR / f"hebmap_{code}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    heb = load_hebrew()
    table = {} if code in HEBREW_NUMBERED else _english_to_hebrew_table()
    out = []
    if code in HEBREW_NUMBERED:
        return _jps_map(path, heb)
    if code not in NO_HEBREW:
        for r in _bible_rows(code):
            if r["book"] not in USFM:
                continue  # New Testament / Deuterocanon: no Hebrew original
            refs = [(c, v) for c, v in _to_hebrew(table, r["book"], r["chapter"], r["verse"])
                    if (r["book"], c, v) in heb]
            if refs:
                out.append({"book": r["book"], "chapter": r["chapter"], "verse": r["verse"],
                            "heb_refs": "|".join(f"{c}:{v}" for c, v in refs)})
    df = pd.DataFrame(out, columns=["book", "chapter", "verse", "heb_refs"])
    df.to_parquet(path)
    return df


_WORD = re.compile(r"[a-z]+")
_STOP = {"the", "and", "of", "to", "in", "that", "he", "his", "unto", "a", "for", "is", "be", "with", "they",
         "them", "not", "all", "him", "shall", "thou", "thy", "thee", "i", "it", "was", "which", "ye", "me",
         "shalt", "neither", "nor", "hath", "thine", "my", "o", "also", "therefore", "said", "saith", "lord", "god"}
# JPS writes G-d / HaShem and "murder" where KJV has God / LORD and "kill"
_NORMALISE = [(re.compile(r"\bg-d\b"), "god"), (re.compile(r"\bhashem\b"), "lord"), (re.compile(r"\bkill\b"), "murder")]


def _bag(text: str) -> set[str]:
    t = text.lower()
    for pat, rep in _NORMALISE:
        t = pat.sub(rep, t)
    return {w for w in _WORD.findall(t) if w not in _STOP}


def _jps_map(path, heb) -> pd.DataFrame:
    """JPS 1917 mostly follows the Hebrew numbering. In a few chapters (e.g. Exodus 20, Deuteronomy 5)
    this copy of JPS numbers verses differently and leaves blank verses at the chapter end. There each
    JPS verse is paired with the KJV verses it contains, and through them with the Hebrew."""
    jps = _bible_rows("JPS")
    odd = {(r["book"], r["chapter"]) for r in jps if not r["text"]}
    kjv_heb = hebrew_lookup("KJV")
    # KJV verses grouped by the Hebrew chapter they belong to, in Hebrew order
    by_heb_ch: dict[tuple[str, int], list[tuple[set, list]]] = {}
    for r in _bible_rows("KJV"):
        refs = kjv_heb.get((r["book"], r["chapter"], r["verse"]))
        if refs and (r["book"], refs[0][0]) in odd:
            by_heb_ch.setdefault((r["book"], refs[0][0]), []).append((_bag(r["text"]), refs))
    for v in by_heb_ch.values():
        v.sort(key=lambda x: x[1][0])

    def contained(k_bag: set, j_bag: set) -> float:
        return len(k_bag & j_bag) / max(len(k_bag), 1)

    out, ptr = [], {}
    for r in jps:
        if not r["text"] or r["book"] not in USFM:
            continue
        key = (r["book"], r["chapter"])
        refs = [(r["chapter"], r["verse"])]
        if key in odd and by_heb_ch.get(key):
            # Walk through the chapter in order: start at the best KJV verse near the pointer, then take
            # following KJV verses that this JPS verse also contains (JPS sometimes merges verses).
            kv, jb, p = by_heb_ch[key], _bag(r["text"]), ptr.get(key, 0)
            if p < len(kv):
                s = max(range(p, min(p + 3, len(kv))), key=lambda i: (contained(kv[i][0], jb), -i))
                e = s
                while e + 1 < len(kv) and contained(kv[e + 1][0], jb) >= 0.6:
                    e += 1
                refs = [hr for _, hrs in kv[s:e + 1] for hr in hrs]
                ptr[key] = e + 1
        refs = [(c, v) for c, v in dict.fromkeys(refs) if (r["book"], c, v) in heb]
        if refs:
            out.append({"book": r["book"], "chapter": r["chapter"], "verse": r["verse"],
                        "heb_refs": "|".join(f"{c}:{v}" for c, v in refs), "jps_text": r["text"]})
    df = pd.DataFrame(out, columns=["book", "chapter", "verse", "heb_refs", "jps_text"])

    # In each odd chapter keep whichever pairing (walked or plain numbering) agrees better with the KJV
    # wording of the Hebrew verses: some chapters are renumbered, others only miss a single verse.
    kjv_text_of_heb = {}
    for r in _bible_rows("KJV"):
        for hc, hv in kjv_heb.get((r["book"], r["chapter"], r["verse"]), []):
            kjv_text_of_heb.setdefault((r["book"], hc, hv), r["text"])

    def agreement(rows) -> float:
        sc = []
        for b, refs, t in rows:
            k = " ".join(kjv_text_of_heb.get((b, *map(int, x.split(":"))), "") for x in refs.split("|"))
            kb, jb = _bag(k), _bag(t)
            sc.append(0 if not kb or not jb else 2 * len(kb & jb) / (len(kb) + len(jb)))
        return sum(sc) / max(len(sc), 1)

    for book, ch in odd:
        m = (df.book == book) & (df.chapter == ch)
        if not m.any():
            continue
        plain = [f"{ch}:{v}" if (book, ch, v) in heb else refs for v, refs in zip(df.loc[m, "verse"], df.loc[m, "heb_refs"])]
        walked_score = agreement(zip(df.loc[m, "book"], df.loc[m, "heb_refs"], df.loc[m, "jps_text"]))
        plain_score = agreement(zip(df.loc[m, "book"], plain, df.loc[m, "jps_text"]))
        if plain_score > walked_score:
            df.loc[m, "heb_refs"] = plain
    df = df.drop(columns="jps_text")
    df.to_parquet(path)
    return df


def hebrew_lookup(code: str) -> dict[tuple[str, int, int], list[tuple[int, int]]]:
    m = hebrew_map(code)
    return {(b, c, v): [tuple(map(int, x.split(":"))) for x in refs.split("|")]
            for b, c, v, refs in zip(m.book, m.chapter, m.verse, m.heb_refs)}


def source_code(scripture: str, version: str) -> str:
    return CATALOG[scripture]["versions"][version]


if __name__ == "__main__":
    load_arabic()
    load_hebrew()
    for s in ["Bible", "Torah"]:
        for v, code in CATALOG[s]["versions"].items():
            m = hebrew_map(code)
            moved = (m.heb_refs != m.chapter.astype(str) + ":" + m.verse.astype(str)).mean() * 100
            print(f"{s:5} {v:42} paired {len(m):6,} verses  renumbered {moved:4.1f}%")
