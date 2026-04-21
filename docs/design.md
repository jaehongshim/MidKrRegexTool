# MidKrRegexTool — Design Overview

This document summarizes the core architecture of the tool.  
Low-level implementation details are documented inside the code and in `DEVLOG.md`.

The design of this tool prioritizes explicit execution modes and minimal control logic. Guard clauses and validations are introduced only when required by concrete usage, rather than as speculative defensive measures.

---

## 1. Processing Pipeline

```
Hanyang PUA text files (.txt / .xml)
    ↓ parser.py      → list[Token]  (pua, source_id, token_index, is_note, context, lang)
    ↓ yale.py        → Token.unicode_form, Token.yale  (via YaleKorean package)
    ↓ tagger.py      → Token.tagged_form  (lemma/POS with inflection decomposition)
    ↓ search.py      → list[Token] or list[tuple[Token, Token]]  (monogram or bigram hits)
    ↓ report.py      → CLI output + optional UTF-16 LE file save
```

---

## 2. Execution Modes (`cli.py`)

`main()` → `parse_cli_args()` → `run()` dispatches to one of:

| Mode | Flag | Description |
|---|---|---|
| Search | *(default, requires `--pattern`)* | Interactive multi-round regex loop with within-results narrowing |
| Training | `--training-mode` | Interactive morphological annotation; saves gold analyses to JSONL |
| Print corpus | `--print-corpus` | Prints `unicode_form: tagged_form` for every token in corpus |

---

## 3. Token Model (`model.py`)

`Token` is the canonical data structure shared across all pipeline stages:

| Field | Set by | Description |
|---|---|---|
| `pua` | parser | Raw Hanyang PUA string |
| `source_id` | parser | Source marker (e.g., `釋詳3:1a`) |
| `token_index` | parser | Position within source block |
| `is_note` | parser | Whether the token appears inside `[note]...[/note]` |
| `context` | parser | Surrounding token window for display |
| `lang` | parser (XML only) | Language tag from TEI markup (`kor`, `chi`, etc.) |
| `path` | parser | Source file path |
| `unicode_form` | yale | PUA → Unicode conversion |
| `yale` | yale | Yale romanization |
| `tagged_form` | tagger | Morphological analysis (e.g., `kwoksik/N/LEM`) |

---

## 4. Stage 1 — Parsing (`parser.py`)

The parser:

1. Reads PUA-encoded `.txt` or `.xml` files.
2. Detects **source markers** (e.g., `<釋詳3:1a>`) and resets `token_index` per source block.
3. Handles markup:
   - `[note] ... [/note]` → tracked via `is_note=True`
   - `[head]`, `[add]` → tags removed; contents preserved
4. For XML files, reads TEI structure and attaches `lang` and `<date>` metadata.
5. Splits segments on whitespace to produce `Token` objects.

The parser deliberately performs **no character normalization**. Its output is the canonical internal representation of the text.

---

## 5. Stage 2 — Yale Conversion (`yale.py`)

Enriches each token with `unicode_form` and `yale` via the `YaleKorean` package.

- Runs after parsing; leaves parser behavior unchanged.
- Hanja remain unconverted; mixed hanja/MK tokens produce mixed Yale output.
- Tokens with `lang="chi"` are filtered out by default (`--classical-ch` re-enables them).
- `--exclude-ch` further excludes tokens that contain any Chinese characters (including mixed tokens).

---

## 6. Stage 3 — Morphological Tagging (`tagger.py`)

Assigns a `tagged_form` to each token.

### Tagging strategy (`analyze_yale`)

Decision order:

1. **Exact lexicon match** → `{lem}/{pos}/LEM`
2. **Lexicon prefix + known rest** (from `rest_set`) → `{lem}/{pos}/LEM-{rest}/INFL`
3. **Lexicon prefix + base suffix rule** → `{lem}/{pos}/LEM-{suf}/INFL`
4. **Sino-Korean verbalizer pattern** (`CH+ho`) → `{lem}/V.CH/LEM-{suf}/INFL`
5. **Sino-Korean noun pattern** (CH + Roman letters) → `{lem}/N.CH/LEM-{suf}/INFL`
6. **Pure Sino-Korean noun** → `{lem}/N.CH/LEM`
7. **Base suffix rules** (suffix-first) → `{lem}/{pos}/LEM-{suf}/INFL`

Tokens that cannot be analyzed receive `NO-TAGGED-FORM`.

### Inflection decomposition (`infl_decomp`)

When training data is available, inflectional suffixes are further decomposed into ordered morpheme chains (e.g., `si/SUBJ/HON-li/FUT-la/DECL`) loaded from the period-specific JSONL file.

### Data files

| File | Role |
|---|---|
| `data/{period}/lemma_whitelist.txt` | Known lemmas with POS |
| `data/{period}/infl_suffixes.txt` | Base inflectional suffixes |
| `data/training/training_{period}c.jsonl` | Gold-annotated training data (not committed) |

### Period awareness

`--period` accepts century values (15–20) or years (converted via `convert_to_century()`). XML files require a `<date>` element in their TEI header; files without one are skipped with a warning.

---

## 7. Stage 4 — Search (`search.py`)

`search_tokens()` dispatches on whether the pattern contains a literal space:

- **Monogram**: matches `token.tagged_form` or `token.yale`
- **Bigram**: matches concatenation of adjacent token pair (`tagged_form or yale`)

Returns `list[Token]` (monogram) or `list[tuple[Token, Token]]` (bigram).

---

## 8. Stage 5 — Reporting (`report.py`)

- `report_hits()` — CLI display of matched tokens with context
- `maybe_save_hits()` — interactive save to UTF-16 LE tab-delimited file

---

## 9. Training Pipeline (`training.py`)

The training loop presents candidate morphological analyses for each token and records confirmed gold labels to a JSONL file.

### Candidate generation

`candidate_generator()` builds candidates from:

1. Lexicon prefix + learned `infl_decomp` suffix
2. Learned suffix + lexicon stem
3. Lexicon prefix + base suffix rules (fallback)
4. Base suffix rules + lexicon stem (fallback)

### Skip logic

Tokens are skipped (not shown to the user) if:

- Already present in `token_gold` (annotated in a previous session), or
- `has_known_parse()` returns `True`: the Yale form can be split into a lexicon stem + a known `infl_decomp` suffix (or vice versa). This avoids re-prompting tokens that are already fully parseable from existing data.

### Training priority

Tokens are sorted before the annotation loop:

| Priority | Condition |
|---|---|
| 0 (highest) | Neither stem nor suffix is known |
| 1 | Stem known, suffix unknown |
| 2 | Suffix known, stem unknown |
| 3 (lowest) | Both stem and suffix are known |

### Bigram training

Triggered when `--pattern` contains a space. Each bigram `(Token A, Token B)` is annotated as a pair; individual gold labels are also saved as monogram entries.

---

## 10. CLI Arguments

| Argument | Mode | Description |
|---|---|---|
| `--path` | all | Input file or directory (defaults to CWD) |
| `--pattern` | search, training filter | Regex pattern |
| `--period` | all | Century filter (15–20) |
| `--training-mode` | — | Enable training mode |
| `--training-data` | all | Path to training data directory |
| `--print-corpus` | — | Enable print-corpus mode |
| `--token-repr` | search, training | `yale` or `tagged_form` |
| `--classical-ch` | all | Include classical Chinese tokens |
| `--exclude-ch` | all | Exclude tokens with Chinese characters |
| `--display-context` | all | Show surrounding context for hits |
| `--sort` | all | Sort XML files by `published_year` |
| `--encoding` | all | File encoding (default: `utf-16`) |
| `--purpose` | search | Free-form label saved with results |
