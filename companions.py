"""
Companion translations (Persian, Spanish) shown next to the English, each switched on in the sidebar:

  * Quran          -> tanzil.net translations in that language (the translator is picked in the sidebar).
                      Verse numbering is the same in every Quran translation.
  * Bible / Torah  -> one public-domain Bible from eBible.org per language:
                      Persian Old Version (ترجمه قدیم, 1895) and Spanish Reina-Valera 1909.

Both Bibles number verses like the King James Version, so they pair directly with the English Bibles
(KJV, ASV, YLT, Webster ...). JPS 1917 uses the Hebrew numbering: there each JPS verse is mapped to the
Hebrew verse(s) and from there to the English (KJV) verse(s) that carry the same text.
"""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd
import requests

from data_loader import DATA_DIR, _bible_rows

QURAN_URL = "https://tanzil.net/trans/?transID={code}&type=txt-2"
EBIBLE_URL = "https://ebible.org/Scriptures/{id}_vpl.zip"

LANGS: dict[str, dict] = {
    "Persian": {
        "code": "fa",
        "native": "فارسی",
        "rtl": True,
        "digits": "۰۱۲۳۴۵۶۷۸۹",
        "quran": {
            "Makarem Shirazi": "fa.makarem",
            "Fooladvand": "fa.fooladvand",
            "Ansarian": "fa.ansarian",
            "Elahi Ghomshei": "fa.ghomshei",
        },
        "default_quran": "Elahi Ghomshei",
        "bible_id": "pesOPV",
        "bible_label": "Persian · Old Version (ترجمه قدیم, 1895)",
        "bible_short": "Persian Old Version",
        "missing": "No Persian translation for this verse.",
    },
    "Spanish": {
        "code": "es",
        "native": "Español",
        "rtl": False,
        "digits": "0123456789",
        "quran": {
            "Julio Cortés": "es.cortes",
            "Raúl González Bórnez": "es.bornez",
            "Isa García": "es.garcia",
        },
        "default_quran": "Julio Cortés",
        "bible_id": "spaRV1909",
        "bible_label": "Spanish · Reina-Valera 1909",
        "bible_short": "Reina-Valera 1909",
        "missing": "No Spanish translation for this verse.",
    },
}

# Bible versions numbered like the Hebrew text, and ones that can't be paired verse by verse
HEBREW_NUMBERED = {"JPS"}
NOT_PAIRED = "Douay-Rheims follows the Latin Vulgate's numbering, so it isn't paired with the {lang}."
NO_PAIRING = {"DRC"}

_VPL = re.compile(r"^(\S+) (\d+):(\d+) (.*)$")


def quran_label(lang: str, name: str) -> str:
    return f"{lang} · {name} (Tanzil)"


def load_quran(lang: str, name: str) -> dict[tuple[int, int], str]:
    code = LANGS[lang]["quran"][name]
    path = DATA_DIR / f"{lang.lower()}_quran_{code}.parquet"
    if not path.exists():
        resp = requests.get(QURAN_URL.format(code=code), timeout=120)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        rows = []
        for line in resp.text.splitlines():
            p = line.split("|", 2)
            if len(p) == 3 and p[0].isdigit() and p[1].isdigit():
                rows.append({"chapter": int(p[0]), "verse": int(p[1]), "text": p[2].strip()})
        if len(rows) != 6236:
            raise ValueError(f"{lang} Quran {code}: expected 6236 verses, got {len(rows)}")
        pd.DataFrame(rows).to_parquet(path)
    df = pd.read_parquet(path)
    return {(c, v): t for c, v, t in zip(df.chapter, df.verse, df.text)}


def load_bible(lang: str) -> dict[tuple[str, int, int], str]:
    """(English book name, chapter, verse) in KJV numbering -> text in that language."""
    bid = LANGS[lang]["bible_id"]
    path = DATA_DIR / f"{lang.lower()}_bible_{bid}.parquet"
    if not path.exists():
        resp = requests.get(EBIBLE_URL.format(id=bid), timeout=180)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            text = z.read(f"{bid}_vpl.txt").decode("utf-8-sig")
        # The 66 books come in the same order as the KJV, so codes are matched to names by position
        kjv_books = list(dict.fromkeys(r["book"] for r in _bible_rows("KJV")))
        codes, rows = [], []
        for line in text.splitlines():
            m = _VPL.match(line.strip())
            if not m or not m.group(4).strip():
                continue
            if m.group(1) not in codes:
                codes.append(m.group(1))
            rows.append({"code": m.group(1), "chapter": int(m.group(2)), "verse": int(m.group(3)),
                         "text": re.sub(r"\s+", " ", m.group(4)).strip()})
        if len(codes) != len(kjv_books):
            raise ValueError(f"{bid}: expected {len(kjv_books)} books, got {len(codes)}")
        name = dict(zip(codes, kjv_books))
        df = pd.DataFrame(rows)
        df.insert(0, "book", df.pop("code").map(name))
        df.to_parquet(path)
    df = pd.read_parquet(path)
    return {(b, c, v): t for b, c, v, t in zip(df.book, df.chapter, df.verse, df.text)}


def hebrew_to_kjv(kjv_heb: dict[tuple[str, int, int], list[tuple[int, int]]]) -> dict[tuple[str, int, int], list[tuple[int, int]]]:
    """Invert the KJV -> Hebrew versification: (book, Hebrew ch, Hebrew v) -> KJV (ch, v) list."""
    out: dict[tuple[str, int, int], list[tuple[int, int]]] = {}
    for (b, c, v), refs in kjv_heb.items():
        for hc, hv in refs:
            out.setdefault((b, hc, hv), []).append((c, v))
    return out


if __name__ == "__main__":
    # Pre-download everything: python companions.py
    for lang, meta in LANGS.items():
        for n in meta["quran"]:
            print(lang, n, len(load_quran(lang, n)))
        print(lang, meta["bible_id"], len(load_bible(lang)))
