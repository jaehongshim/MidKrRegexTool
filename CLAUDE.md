# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in development mode
pip install -e .

# Run the tool
python -m midkrregextool --path <file_or_dir> --pattern <regex>

# Search mode (default) — requires --pattern
python -m midkrregextool --path /corpus --pattern "kwoksik" --period 15

# Training mode — requires --period; --pattern is optional filter
python -m midkrregextool --path /corpus --training-mode --period 15 --training-data data/

# Print tagged corpus
python -m midkrregextool --path /corpus --print-corpus --period 15 --training-data data/

# Bigram search (pattern with literal space triggers bigram mode)
python -m midkrregextool --path /corpus --pattern "kwoksik /N"
```

No test framework is currently in place (`tests/` directory exists but is empty except for fixtures).

## Architecture

### Processing Pipeline

```
Hanyang PUA text files (.txt / .xml)
    ↓ parser.py      → list[Token]  (pua, source_id, token_index, is_note, context)
    ↓ yale.py        → Token.unicode_form, Token.yale  (via YaleKorean package)
    ↓ tagger.py      → Token.tagged_form  (lemma/POS with inflection suffix decomposition)
    ↓ search.py      → list[list[Token]]  (matched hits, monogram or bigram)
    ↓ report.py      → CLI output + optional UTF-16 file save
```

### Execution Modes (cli.py)

`main()` → `parse_cli_args()` → `run()` dispatches to one of:
- **`run_search()`** — default; interactive multi-round regex loop with within-results narrowing
- **`run_train()`** — interactive morphological annotation; saves annotations to JSONL
- **`run_print_corpus()`** — prints `unicode_form: tagged_form` for every token

### Key Modules

| Module | Role |
|---|---|
| `model.py` | `Token` dataclass — canonical data structure across all stages |
| `parser.py` | Reads PUA-encoded files; detects source markers (`<釋詳3:1a>`), `[note]...[/note]`, `[head]`/`[add]` markup; whitespace-tokenizes |
| `yale.py` | `attach_yale()` enriches tokens with `unicode_form` and `yale`; handles `--classical-ch` and `--exclude-ch` filters |
| `tagger.py` | Loads lemma lexicon; assigns `tagged_form` (e.g., `kwoksik/N`); period-aware |
| `search.py` | `search_tokens()`: monogram (no space in pattern → matches `token.yale` or `token.tagged_form`) vs. bigram (space → matches concatenation of adjacent token pair) |
| `training.py` | Interactive annotation loop; priority sorting by frequency/lexicon coverage; persists to `training_{period}c.jsonl` |
| `report.py` | `report_hits()` for CLI display; `maybe_save_hits()` for UTF-16 LE tab-delimited file output |

### Token Representation (`--token-repr`)

- Default in **search mode**: `tagged_form`
- Default in **training mode**: `yale`
- Bigram search joins adjacent tokens' `tagged_form or yale` for matching

### Period Filtering

`--period` accepts century values (15–20) or years (converted via `convert_to_century()`). XML files require a `<date>` element in their TEI header; files without one are skipped with a warning.

### Data Files (`data/`)

Training data lives in `data/` and is **not committed**. The tool resolves relative `--training-data` paths from the repo root. Per-period JSONL files follow the naming `training_{period}c.jsonl`.

### Design Principles (from `docs/design.md`)

- Guard clauses and validations are added only when required by concrete usage, not speculatively.
- The parser performs no character normalization — Yale conversion is a separate stage.
- Corpus files are **not** included in the repository.
