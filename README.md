# MidKrRegexTool

A regex-based search and morphological annotation tool for Middle Korean texts, designed to support research on morphosyntactic patterns.

The tool operates over Middle Korean texts encoded in the Hanyang PUA format, converts them into Unicode and Yale romanized forms, assigns morphological analyses, and supports regex search over tagged forms. It also provides an interactive training mode for building period-specific gold-annotated morphological data.

## Installation

```bash
pip install -e .
```

## Pipeline Overview

The tool processes corpus files through five stages. Below is a worked example using one sentence from an NIKL XML corpus file.

**Input**:
```xml
<sent type="main" lang="kor" page="03b-4a" n="8">도라와 어마니ᄆᆞᆯ 濟渡ᄒᆞ야</sent>
```
The characters inside `<sent>` are Hanyang PUA encoded — they appear as Korean on screen but occupy the Unicode Private Use Area. 

---

### Stage 1 — `parser.py` → `list[Token]`

Splits the sentence on whitespace. Each word becomes a `Token` with metadata extracted from the XML attributes and the document's TEI header. Fields not yet populated are `None`.

```
Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=1,
      pua="도라와",    lang="kor", is_note="main",
      unicode_form=None, yale=None, context=None, matched_part=None, tagged_form=None)

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=2,
      pua="어마니ᄆᆞᆯ", lang="kor", is_note="main",
      unicode_form=None, yale=None, context=None, matched_part=None, tagged_form=None)

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=3,
      pua="濟渡ᄒᆞ야",  lang="kor", is_note="main",
      unicode_form=None, yale=None, context=None, matched_part=None, tagged_form=None)
```

`source_id` encodes document name, page, sentence number, and language. `pua` holds the raw Hanyang PUA characters as-is; no normalization is done at this stage.

---

### Stage 2 — `yale.py` → `Token.unicode_form`, `Token.yale`

Converts each `pua` string to Unicode Hangul (`unicode_form`) and then to Yale romanization (`yale`) via the `YaleKorean` package. Tokens with `lang="chi"` are filtered out here unless `--classical-ch` is set.

```
Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=1,
      pua="도라와",    lang="kor", is_note="main",
      unicode_form="도라와", yale="twolawa", # ← new
      context=None, matched_part=None, tagged_form=None)

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=2,
      pua="어마니ᄆᆞᆯ", lang="kor", is_note="main",
      unicode_form="어마니ᄆᆞᆯ", yale="emanimol",  # ← new
      context=None, matched_part=None, tagged_form=None)

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=3,
      pua="濟渡ᄒᆞ야",  lang="kor", is_note="main",
      unicode_form="濟渡ᄒᆞ야",  yale="濟渡hoya",   # ← new
      context=None, matched_part=None, tagged_form=None)
```

All downstream processing — tagging and search — operates on `yale`.

---

### Stage 3 — `tagger.py` → `Token.tagged_form`

Looks up each `yale` form in the lemma lexicon and inflection suffix table to assign a morphological analysis.

```
Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=1,
      pua="도라와",    lang="kor", is_note="main",
      unicode_form="도라와",    yale="twolawa",
      context=None, matched_part=None,
      tagged_form="twolaw(o)/V/LEM-a/CONN")   # ← new

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=2,
      pua="어마니ᄆᆞᆯ", lang="kor", is_note="main",
      unicode_form="어마니ᄆᆞᆯ", yale="emanimol",
      context=None, matched_part=None,
      tagged_form="emanim/N/LEM-ol/ACC")       # ← new

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=3,
      pua="濟渡ᄒᆞ야",  lang="kor", is_note="main",
      unicode_form="濟渡ᄒᆞ야",  yale="濟渡hoya",
      context=None, matched_part=None,
      tagged_form="濟渡ho/V.CH/LEM-ya/CONN")   # ← new
```

Tag notation: everything before `/LEM` is the lemma with POS (e.g., `emanim/N`); segments after `/LEM-` are inflectional morphemes with grammatical functions (`/CONN` = connective ending, `/ACC` = accusative case, `/V.CH` = Sino-Korean verb).

---

### Stage 4 — `search.py` → matched hits

Compiles the pattern as a regex and tests it against each token's `tagged_form` (default) or `yale`. Example with `--pattern "emanim"`:

```
Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=1,
      pua="도라와",    lang="kor", is_note="main",
      unicode_form="도라와",    yale="twolawa",
      context=None, matched_part=None,          # ← no match
      tagged_form="twolaw(o)/V/LEM-a/CONN")

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=2,
      pua="어마니ᄆᆞᆯ", lang="kor", is_note="main",
      unicode_form="어마니ᄆᆞᆯ", yale="emanimol",
      context=None, matched_part="emanim",      # ← new: match found
      tagged_form="emanim/N/LEM-ol/ACC")

Token(path="HXRW2320000612.xml", source_id="1447_석보상절6:03b-4a:8:kor", token_index=3,
      pua="濟渡ᄒᆞ야",  lang="kor", is_note="main",
      unicode_form="濟渡ᄒᆞ야",  yale="濟渡hoya",
      context=None, matched_part=None,          # ← no match
      tagged_form="濟渡ho/V.CH/LEM-ya/CONN")
```

A pattern containing a literal space triggers **bigram mode**, which matches the concatenated `tagged_form` of two adjacent tokens.

---

### Stage 5 — `report.py` → CLI output

Token 2 is returned as a hit. `report.py` formats it for display:

```
1447_석보상절6:03b-4a:8:kor  2  main  [HXRW2320000612.xml]
    [TOKEN]        어마니ᄆᆞᆯ
    [TAGGED-FORM]  emanim/N/LEM-ol/ACC
    [MATCHED-PART] emanim
```

Results can optionally be saved to a UTF-16 LE tab-delimited file.

## Execution Modes

### Search mode (default)

Requires `--pattern`. Runs an interactive multi-round regex loop; within-results narrowing is supported between rounds.

```bash
python -m midkrregextool --path /corpus --pattern "kwoksik" --period 15 --training-data data/
```

```bash
# Bigram search (literal space in pattern)
python -m midkrregextool --path /corpus --pattern "kwoksik /N" --period 15 --training-data data/
```

### Training mode

Interactive morphological annotation. Presents candidate analyses per token and saves confirmed gold labels to a period-specific JSONL file.

```bash
python -m midkrregextool --path /corpus --training-mode --period 15 --training-data data/
```

- `--pattern` is optional: when provided, only matching tokens are shown.
- Tokens already annotated in a previous session are skipped automatically.
- Tokens fully parseable from the existing lexicon and learned inflection data are also skipped.

### Print corpus mode

Prints `unicode_form: tagged_form` for every token, useful for reviewing tagging coverage.

```bash
python -m midkrregextool --path /corpus --print-corpus --period 15 --training-data data/
```

## Search Behavior

### Monogram search
- Applied when the pattern contains no literal space.
- Matches against `token.tagged_form` (default) or `token.yale` (with `--token-repr yale`).

### Bigram search
- Applied when the pattern **contains a literal space**.
- Matches against the concatenation of two adjacent tokens' `tagged_form` (or `yale`).

## Key Arguments

| Argument | Description |
|---|---|
| `--path` | Input file or directory (defaults to CWD) |
| `--pattern` | Regex pattern |
| `--period` | Century filter: `15`–`20` or year (e.g., `1459`) |
| `--training-mode` | Enable training mode |
| `--training-data` | Path to training data directory |
| `--print-corpus` | Enable print-corpus mode |
| `--token-repr` | `yale` or `tagged_form` (default varies by mode) |
| `--classical-ch` | Include minimally-annotated classical Chinese tokens |
| `--exclude-ch` | Exclude tokens containing Chinese characters |
| `--display-context` | Show surrounding token context for hits |
| `--sort published_year` | Sort XML files by publication year |
| `--encoding` | Input file encoding (default: `utf-16`) |
| `--purpose` | Free-form label saved with search results |

## Training Data

Gold annotations are stored in `data/training/training_{period}c.jsonl` (not committed to the repository). Each record contains the token's Unicode form and its morphological analysis, e.g.:

```json
{"period": "15c", "token": "가져시리러니라", "gold_morph": "kacy/V/LEM-e/CONN-si/AUX-li/FUT-le/IPFV-ni/ASS-la/DECL"}
```

The training file is used to:
- extend the lemma lexicon with attested POS information,
- learn inflectional suffix decompositions (`infl_decomp`) for richer candidate generation,
- skip already-annotated and fully-parseable tokens in subsequent training sessions.

## Notes

- Corpus files are **not** included in this repository.
- The tool resolves relative `--training-data` paths from the repository root.
- Classical Chinese segments (`lang="chi"`) are excluded from search and training by default.
