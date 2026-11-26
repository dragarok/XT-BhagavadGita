# Bhagavad Gita for the Xteink X4 Pro

An Ink App for the X4 Pro's firmware, XT Licorice (API 2.18), with all 701 verses on the reader.
It never uses Wi-Fi.

**Download:** `bhagavadgita.xtapp` from the [latest release](https://github.com/dragarok/XT-BhagavadGita/releases/latest).

## What it does

- **Verse:** the shloka in Devanagari, then its padachheda (the verse with sandhi undone, compound
  members joined by hyphens) with a short English meaning under every word, then Annie Besant's
  English translation and her footnotes.
- **Word meanings:**
  - Grammar shapes each meaning: न जातु नासम् reads "not ever not I was", फलेषु "in fruits",
    अर्जुन "O Arjuna", मोक्षयिष्यामि "I will liberate".
  - They come from `tools/glossary.tsv`, which covers 80% of the words in the text; any line there
    can be edited. The rest use the corpus's sense or its first dictionary meaning.
- **Padachheda on or off:** the middle button of the verse screen, or Settings. Off shows only the
  shloka and the translation.
- **Long verses** take two pages. The translation is kept on one page.
- **Long press any word**, in the verse or in its padachheda. The word's page opens with
  the words it is made of. Each word comes with its base form, its grammar ("noun, masculine nominative
  plural", "verb: imperfect 1st person singular", "first part of a compound") and its meaning.
  - < Word and Word > step through the verse word by word.
  - A long word, such as 2.2's अनार्यजुष्टमस्वर्ग्यमकीर्तिकरमर्जुन, takes two pages.
- **Moving around:**
  - Home lists the 18 chapters. A chapter shows its Devanagari name and a grid of its verses.
  - Next and Prev (also the side keys and swipes) go through the pages of a verse, then on to
    the next verse, across chapters.
  - Back goes up one level. Back on Home leaves the app.
  - Continue opens the last verse read.
- **Settings:** padachheda and meanings, translation, notes, English text size and Devanagari
  size (small, medium or large each), and About and sources.

## Install

1. Copy `bhagavadgita.xtapp` (about 2 MB, from the
   [latest release](https://github.com/dragarok/XT-BhagavadGita/releases/latest)) to the root of
   the SD card.
2. Copy `TiroDevanagariHindi-Regular.ttf`
   ([Google Fonts](https://fonts.google.com/specimen/Tiro+Devanagari+Hindi)) into the card's
   `Pushed Fonts` folder, and pick it in Ink App settings. The app's Devanagari is drawn in that
   font. A `.ttf` without Devanagari shows no Sanskrit.
3. On the reader, open All Files, tap `bhagavadgita.xtapp`, then Install.
4. Open it from ≡ → Ink App.

## Devanagari: the reader's own font

The reader draws Devanagari correctly when its `.ttf` has it: with Tiro Devanagari Hindi, conjuncts
join and the i-sign goes before its consonant, in books and in Ink Apps alike. So since 0.3.0 the
Sanskrit is plain UTF-8 text, and the app lays out every word itself. That's how it knows each
word's place for the long press, and how it centres the meaning under each word.

Versions 0.1 and 0.2 drew the Devanagari as 1-bit pictures made on the Mac. They were 8-9 MB, and
some verses took up to 15 s to open:
- the data was in five 900 KB files;
- when the reader can't seek within a file, the app reads it from the top to the verse;
- every picture also had to be decoded while the screen was being drawn.

Now:
- the data is 1.9 MB, cut into 108 files of at most 19 KB, so a read from the top stays short;
- reading and laying out a verse happen when it is opened, not while drawing;
- the slow steps ask the reader for more time (`ctx.budget:extend`).

The `.bin` fonts can't do Devanagari: a `.bin` holds one bitmap per code point, so letters
never join.

## Sources and licences

| What | Source | Licence |
|---|---|---|
| Sanskrit text, translation, notes | Annie Besant, *The Bhagavad-Gita*, 4th ed. (1922), as proofread on English Wikisource | public domain |
| Padachheda, base forms, grammar, meanings | Oliver Hellwig: Digital Corpus of Sanskrit (DCS). 2010-2024 (GitHub `OliverHellwig/sanskrit`) | CC BY 4.0 |
| Devanagari typeface (the reader's `.ttf`, not in the package) | Tiro Devanagari Hindi, Tiro Typeworks, from `google/fonts` | SIL OFL 1.1 |
| The app, its tools and `tools/glossary.tsv` | this repository | MIT (`LICENSE`) |
| The build kit in `kit/` | see [`kit/README.md`](kit/README.md) | MIT |

The data files in `data/` and `sources/gita.json` are derived from the DCS, so they stay under
CC BY 4.0: credit the DCS as above when you reuse them.

Chapter 13 follows Besant's numbering: 35 verses, with Arjuna's question as verse 1. Editions that
leave that verse out have 34.

The translations on heritage.iitk.ac.in/SBG (Gambhirananda, Adidevananda, Sankaranarayan, and
the commentary translations) aren't included. That site's licence (HCAL 1.2) forbids copying
them by automated means. Public-domain commentaries are planned instead: Shankara's in Alladi
Mahadeva Sastri's translation (1897) and Ramanuja's in A. Govindacharya's (1898).

## Build

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt     # once

.venv/bin/python -I kit/lualint55.py src/*.lua
.venv/bin/python -I test_gita.py                       # bundles src/ into index.lua, then tests
.venv/bin/python -I kit/xtpack.py . -o dist/bhagavadgita.xtapp
```

- Edit `src/main.lua`, never `index.lua`: `bundle.py` makes it from `kit/gamekit.lua` and `src/`.
  It is committed, because it is what the package carries.
- `data/` and `sources/gita.json` are committed too, so building needs no download. To make them
  again from the sources:

  ```sh
  .venv/bin/python -I tools/fetch_sources.py    # Wikisource, DCS, the font -> sources/cache/ (not committed)
  .venv/bin/python -I tools/build_data.py       # -> sources/gita.json
  .venv/bin/python -I tools/write_data.py       # -> data/*.txt (texts, padachheda, meanings)
  .venv/bin/python -I make_icon.py              # -> icon.png
  ```

- `tools/gloss.py` makes the meanings: the base meaning from `glossary.tsv`, then English for the
  grammar:
  - nouns get a plural and a case word (with, for, from, of, in, O);
  - pronouns become I / me / my / in me;
  - verbs get person and tense (I was, we will be, is said, fight!, let it be);
  - participles become seen / seeing / having seen / to be seen.
  After editing the glossary, run `write_data.py` again.
- `build_data.py` aligns Besant's printed words with the DCS analysis: both texts go to SLP1
  and are matched letter by letter, which agrees on 98-100% of letters in every chapter.
  - 26 of the 6554 printed words have no analysis.
  - 43 more borrow theirs from another place where the same word is printed.

**`test_gita.py`** runs the app under Lua 5.4 against the packed data. The stubs act like the
device: seek on package files, method calls only, a clear at the start of every frame, text at
whole pixels. It checks that:
- every verse and word page opens;
- a long press on any word, or on its meaning, opens that word;
- Back leaves the app only from Home, on the release of a press made there (the reader leaves
  when the app passes a release on);
- no screen goes over the draw-command budget;
- opening a verse reads little, even when seek fails (at most 4 KB with seek, 31 KB without);
- settings survive a restart.

## Data format

See the docstring of `tools/write_data.py`. In short:
- `chapters.txt` holds the chapter titles and Devanagari names.
- `index.txt` is a record file: verse k gives its file `vNNN.txt` and byte offset.
- A verse is one `V` line, then one `T` line per printed word:
  - the `V` line holds the texts, and the shloka as lines of words and punctuation;
  - each `T` line holds the printed word, its padas with their meanings, and its words for the
    word page.
- 108 verse files of at most 19 KB; lines are at most 1.4 KB.

## Releases

`.github/workflows/release.yml` lints, tests and packs the app on every push and pull request.
On `main`, if `manifest.json` has a version with no release yet, it creates the release
`v<version>` with `bhagavadgita.xtapp` attached. Bumping `"version"` in `manifest.json` is all a
release takes.

## Layout

| Path | What |
|---|---|
| `manifest.json`, `icon.png`, `index.lua`, `data/` | the app as packed |
| `src/main.lua` | the app's source |
| `tools/` | fetch the sources, align them, make the glosses and the data files |
| `sources/gita.json` | the aligned text: Besant's verses with the DCS analysis of every word |
| `test_gita.py` | the offline tests |
| `kit/` | the vendored build kit: packer, bundler, test harness, Lua 5.5 lint |
