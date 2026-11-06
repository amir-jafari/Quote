# 📜 Sacred Words Explorer

A Streamlit app for exploring the **Quran**, the **Bible** and the **Torah** in English: read them,
search them, find inspiring verses, make word clouds and compare word statistics.

## Run

```bash
pip install -r requirements.txt
python data_loader.py      # optional: pre-downloads and caches all 18 translations into ./data
python originals.py        # optional: pre-downloads the Arabic & Hebrew originals and verse mappings
streamlit run app.py
```

## Scriptures & versions (selectable from the sidebar drop-downs)

| Scripture | Versions |
|---|---|
| ☪️ Quran | Saheeh International, Pickthall, Yusuf Ali, Talal Itani (The Clear Quran), Ali Quli Qarai, Muhammad Sarwar |
| ✝️ Bible | KJV, ASV, BBE, Young's Literal, Darby, Webster, Douay-Rheims (with Deuterocanon), Geneva 1599 |
| ✡️ Torah | JPS 1917, KJV, YLT, ASV. Covers the full Tanakh; choose *Section → Torah* for the five books |

The sidebar filters cascade **Scripture → Version → Section → Book/Surah**, and every tab respects that selection.

## Tabs

- **✨ Inspire**: random or "verse of the day" by theme (Love, Peace, Mercy, Hope, Patience…),
  *One theme, three traditions* (one verse from each scripture side by side), and a theme radar chart.
- **📖 Read**: chapter reader with a side-by-side parallel translation and word highlighting.
- **🔍 Search**: word, word-form or phrase search in the current selection or across all three; hit chart and CSV export.
- **☁️ Word Cloud**: shapes (heart, star, arch, circle), palettes, filler-word filtering, three-scripture
  comparison, "words around a keyword", PNG download.
- **📊 Word Insights**: pick words, then compare frequency per 10k words across the scriptures, across books
  (line and heatmap), word companions (co-occurrence) and frequency across translations. Also a corpus profile
  (top words, sunburst, verse length, tone arc).
- **⚖️ Compare Translations**: one verse in every translation, plus the words they all share.
- **⭐ My Collection**: save verses, export Markdown/CSV and download shareable **quote-card images**.

## Original languages
With **Show Arabic / Hebrew original** switched on (sidebar), each verse shows its original text next to the English:
- **Quran → Arabic** (Uthmani script, tanzil.net).
- **Torah and Bible Old Testament → Hebrew** (Westminster Leningrad Codex). You can show vowels only, vowels with
  cantillation marks, or consonants only.
- The **Read** tab becomes a verse-by-verse grid: English | (second translation) | original.

English Bibles number some verses differently from the Hebrew (e.g. KJV Malachi 4:1 = Hebrew 3:19,
Joel 2:28 = Hebrew 3:1, psalm headings are verse 1 in Hebrew). English references are converted with the
standard Copenhagen Alliance versification table, and the card shows the Hebrew reference whenever it differs.
For the JPS 1917 text, the few chapters where this copy numbers verses differently (e.g. the Ten Commandments in
Exodus 20 and Deuteronomy 5) are matched verse by verse. The New Testament (written in Greek) and Douay-Rheims
(Latin Vulgate numbering) show a note instead of Hebrew.

## Data sources
- Quran: [tanzil.net](https://tanzil.net/trans/) translations (surah names from fawazahmed0/quran-api)
- Bible / Tanakh, including the Hebrew WLC: [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
- Arabic Quran: [tanzil.net](https://tanzil.net/download/)
- Versification: [Copenhagen Alliance versification-specification](https://github.com/Copenhagen-Alliance/versification-specification)

## Sentence quality
Scripture verses don't always line up with sentences. About 15–25% of verses end with `,` `;` or `:` and
continue into the next verse. The app handles this as follows:
- **Inspire / random picks** only draw verses that are complete sentences on their own.
- **Search, Save and quote cards** expand a partial verse to its whole sentence (e.g. *Genesis 5:21–24*).
- Partial verses shown on their own are labelled "↪ sentence continues in the next verse".
