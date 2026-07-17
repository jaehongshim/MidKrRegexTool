# Normalization Policy

## Decision

This tool performs **no character normalization** on input text.

The input corpus uses Hanyang PUA encoding, which is already internally consistent. Normalization (e.g., combining compatibility jamo, standardizing hanja variants) would risk altering the source material in ways that are difficult to audit or reverse.

Character conversion is handled as a **separate, explicit pipeline stage** (`yale.py`):

- PUA → Unicode: via `PUAtoUni` (YaleKorean package)
- Unicode → Yale romanization: via `YaleMid` (YaleKorean package)

These conversions are read-only enrichments attached to each `Token` as `unicode_form` and `yale`. The original `pua` field is always preserved.

## Implications

- The parser (`parser.py`) produces tokens without any character transformation.
- Search and annotation operate over `yale` or `tagged_form`, never over normalized Unicode directly.
- Mixed hanja/MK tokens produce mixed Yale output (hanja unconverted); this is intentional and consistent with how the corpus represents such tokens.
