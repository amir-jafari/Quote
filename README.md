# 📜 Sacred Words Explorer

A Streamlit app for exploring the **Quran**, the **Bible** and the **Torah** in English: read them,
search them, find inspiring verses, make word clouds and compare word statistics.

## Run

```bash
pip install -r requirements.txt
python data_loader.py      # optional: pre-downloads and caches all 18 translations into ./data
python originals.py        # optional: pre-downloads the Arabic & Hebrew originals and verse mappings
python companions.py       # optional: pre-downloads the Persian & Spanish translations
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
- **📖 Read**: chapter reader with **Go to a verse** (`John 3:16`, `Psalm 23`, `1 Cor 13:4`, `2:255`, `Al-Baqara 255`),
  ◀ / ▶ chapter buttons, a side-by-side second translation matched verse by verse, and word highlighting.
- **🔍 Search**: word, word-form or phrase search in **English, Persian or Spanish**, in the current selection or across
  all three; hit chart and CSV export (with the active translations). Persian matches ي/ی and ك/ک alike and ignores
  vowel marks; Spanish ignores accents (*senor* finds *Señor*).
- **☁️ Word Cloud**: shapes (heart, star, arch, circle), palettes, filler-word filtering, three-scripture
  comparison, "words around a keyword", PNG download.
- **📊 Word Insights**: pick words, then compare frequency per 10k words across the scriptures, across books
  (line and heatmap), word companions (co-occurrence) and frequency across translations. Also a corpus profile
  (top words, sunburst, verse length, tone arc).
- **⚖️ Compare Translations**: one verse in every translation, plus the words they all share. Where translations number
  a verse differently (JPS 1917 follows the Hebrew numbering: JPS Genesis 32:1 = KJV 31:55) the right verse is shown.
- **⭐ My Collection**: save verses, export Markdown/CSV and download shareable **quote-card images**.

## Quote cards
Cards are 1080 × 1350 (the 4:5 portrait size social feeds show in full). Each card carries the English plus every
translation switched on in the sidebar (Persian, Spanish, and the Arabic / Hebrew original when that is on), with the
sources listed under the reference. The default **Scripture theme** background is drawn per scripture and given its
own shade and pattern for every book: emerald with a gold eight-pointed-star lattice for the Quran, night blue with
rays of light for the Bible, parchment between scroll rollers for the Torah. The older flat gradients remain in the
style menu.

Press **🖼️ Quote card** under a verse to preview the card, then **⬇️ Download** or **📤 Share**. Share opens the device's share sheet with the card attached as a picture: choose Mail
and the recipient sees the card in the email (or pick WhatsApp, Messages…). Browsers that can't share files, such as
Firefox on desktop, copy the card instead and open a new email: paste it in with Ctrl/⌘+V.

Fonts (Lora, Cinzel, Vazirmatn, Amiri, Noto Serif Hebrew; SIL Open Font License) are bundled in
`./fonts`; Persian and Arabic letters are joined with `arabic-reshaper` and ordered with `python-bidi`.

## Original languages
With **Show Arabic / Hebrew original** switched on (sidebar, off by default), each verse shows its original text next to the English:
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

## Persian & Spanish translations
Both are on by default (switch them off in the sidebar with **Show Persian translation** / **Show Spanish translation**). They appear under every
verse card (Inspire, Search, Collection…), as extra columns in the **Read** grid, and in **Compare Translations**.
Saved verses keep them and the Markdown export includes them.
- **Quran**: Persian — Elahi Ghomshei (default), Makarem Shirazi, Fooladvand, Ansarian; Spanish — Julio Cortés
  (default), Raúl González Bórnez, Isa García (tanzil.net). The translator is picked in the sidebar.
- **Bible & Torah**: Persian Old Version (ترجمه قدیم, 1895) and Spanish Reina-Valera 1909, both public domain
  (eBible.org). They use English verse numbers; JPS 1917 verses are matched through the Hebrew numbering.
  Douay-Rheims (Vulgate numbering) shows a note instead.

## Data sources
- Quran: [tanzil.net](https://tanzil.net/trans/) translations (surah names from fawazahmed0/quran-api)
- Bible / Tanakh, including the Hebrew WLC: [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
- Arabic Quran: [tanzil.net](https://tanzil.net/download/)
- Persian & Spanish Bibles: [eBible.org](https://ebible.org/) (pesOPV, spaRV1909)
- Versification: [Copenhagen Alliance versification-specification](https://github.com/Copenhagen-Alliance/versification-specification)

## Sentence quality
Scripture verses don't always line up with sentences. About 15–25% of verses end with `,` `;` or `:` and
continue into the next verse. The app handles this as follows:
- **Inspire / random picks** only draw verses that are complete sentences on their own.
- **Search, Save and quote cards** expand a partial verse to its whole sentence (e.g. *Genesis 5:21–24*).
- Partial verses shown on their own are labelled "↪ sentence continues in the next verse".
