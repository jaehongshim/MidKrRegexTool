# MidKrRegexTool

A regex-based search and morphological annotation tool for Middle Korean texts, designed to support research on morphosyntactic patterns.

The tool operates over Middle Korean texts encoded in the Hanyang PUA format, converts them into Unicode and Yale romanized forms, assigns morphological analyses, and supports regex search over tagged forms. It also provides an interactive training mode for building period-specific gold-annotated morphological data.

## Installation

```bash
pip install -e .
```

## Pipeline Overview

```
Hanyang PUA text files (.txt / .xml)
    ↓ parser.py      → list[Token]  (pua, source_id, token_index, is_note, context, lang)
    ↓ yale.py        → Token.unicode_form, Token.yale
    ↓ tagger.py      → Token.tagged_form  (lemma/POS + inflection decomposition)
    ↓ search.py      → matched hits (monogram or bigram)
    ↓ report.py      → CLI output + optional UTF-16 LE file save
```

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
