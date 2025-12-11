# MidKrRegexTool — Design Overview

This document summarizes the core architecture of the tool.  
Low-level implementation details are documented inside the code and in `DEVLOG.md`.

---

## 1. Processing Pipeline

### Input
- Middle Korean texts encoded in **Hanyang PUA**.
- The repository does **not** contain corpus files.
- The command-line interface will accept:
  - a single text file, or  
  - a folder containing multiple `.txt` files.

---

## 2. Stage 1 — Parsing (`parser.py`)

The parser:

1. Reads PUA-encoded text line by line.
2. Detects **source markers** (e.g., `<釋詳3:1a>`) and resets `token_index` per source block.
3. Handles markup:
   - `[note] ... [/note]` → tracked via `is_note=True`
   - `[head]`, `[add]` → tags removed; contents preserved
4. Splits segments on whitespace to create `Token` objects with:
   - `source_id`
   - `token_index`
   - `pua` (raw Hanyang PUA string)
   - `is_note`

The parser deliberately performs **no character normalization or Yale conversion**.  
Its output is the canonical internal representation of the text.

---

## 3. Stage 2 — Yale Conversion (`yale.py`)

This stage enriches each token with:

- `unicode_form` — via `PUAtoUni`
- `yale` — via `YaleMid`

Characteristics:

- Runs **after** parsing.
- Leaves parser behavior unchanged.
- Hanja remain unconverted; mixed hanja/MK tokens produce mixed Yale output.
- Some Yale outputs include package-specific markers (e.g., `.`, `$`).

---

## 4. Post-processing (planned)

Potential refinements (not yet implemented):

1. Decide how to treat hanja appearing inside Yale outputs.
2. Normalize or remove special Yale markers (e.g., `.`, `$`).
3. Handle mixed hanja + compatibility jamo tokens (e.g., `香山ㅅ`).

These decisions will follow the implementation of the search module.

---

## 5. Stage 3 — Search Module (planned)

The upcoming `search.py` will:

- Perform **regex-based search** over:
  - Yale (default),
  - optionally Unicode or PUA.
- Return matched tokens with full metadata:
  - `source_id`, `token_index`, `is_note`
  - `pua`, `unicode_form`, `yale`

Additional features (e.g., multi-token patterns, context windows) may be added later.

---
