# tagger.py

from __future__ import annotations
from .model import Token
from pathlib import Path
from collections import Counter

def load_infl_suffixes() -> list[str]:
    path = Path(__file__).with_name("infl_suffixes.txt")
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    suffixes = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        suffixes.append(line)

    return sorted(suffixes, key=len, reverse=True)

def analyze_yale(yale: str, infl_suffixes: list[str]) -> str:
    
    if not yale:
        return ""   # guard against missing yale
    
    # Inspect longer suffixes first
    for suf in infl_suffixes:
        if yale.endswith(suf):
            lem = yale[:-len(suf)]
            if not lem:
                return f"{yale}/LEM"
            return f"{lem}/LEM-{suf}/INFL"

    # If no suffix is detected, the whole yale is tagged as a lemma 
    return f"{yale}/LEM"

def split_lem_infl(yale: str, infl_suffixes: list[str]) -> tuple[str, str] | None:
    """
    Return (lem, infl) if a suffix matches; otherwise return None.
    """

    if not yale:
        return None # guard against missing yale
    for suf in infl_suffixes:
        if yale.endswith(suf) and len(yale) > len(suf):
            lem = yale[:-len(suf)]
            return (lem, suf)
    return None

def propose_infl_suffixes(
        tokens: list[Token],
        infl_suffixes: list[str],
        *,
        max_len: int = 10,
        min_count: int = 20,
        top_k: int = 50,
) -> list[tuple[str, int]]:
    """
    Look at tokens where split_lem_infl() fails, and propose frequent suffix strings (up to max_len) from the end of yale.    
    """
    c = Counter()

    # Counting suffix candidates

    for t in tokens:
        yale = t.yale
        if not yale:
            continue

        # If the given suffix is already in the suffix list, skip.
        if split_lem_infl(yale, infl_suffixes) is not None:
            continue

        # collect suffix candidates of length 1..max_len from the end of the given yale string.
        for L in range(1, min(max_len, len(yale))+1):
            cand = yale[-L:]
            c[cand] += 1

    # Keep only frequent suffix candidates above the minimum count threshold (min_k)
    # sort by suffix length (desc), frequency (desc), then alphabetically
    items = [(suf, cnt) for suf, cnt in c.items() if cnt >= min_count]
    items.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))

    return items[:top_k]

def update_suffix_counter(
        counter: Counter,
        tokens: list[Token],
        infl_suffixes: list[str],
        *,
        max_len: int = 6,
) -> None:
    for t in tokens:
        yale = t.yale
        if not yale:
            continue
        if split_lem_infl(yale, infl_suffixes) is not None:
            continue
        for L in range(1, min(len(yale), max_len) + 1):
            if L < len(yale):
                counter[yale[-L:]] += 1

def finalize_suffix_proposals(
        counter: Counter,
        infl_suffixes: list[str],
        *,
        min_count: int = 20,
        top_k: int = 50,
        min_len: int = 3
) -> list[tuple[str, int]]:
    
    items: list[tuple[str, int]] = []

    for cand, cnt in counter.items():
        if cnt < min_count:
            continue

        if len(cand) < min_len:
            continue

        if not cand.isascii():
            continue

        if any(known.endswith(cand) for known in infl_suffixes):
            continue

        items.append((cand, cnt))
     
    items.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))
    return items[:top_k]

def tag_tokens(tokens: list[Token], infl_suffixes: list[str], *, debug_suffixes: bool = False) -> list[Token]:
    """Enrich tokens with morphological tagging for downstream processing."""

    if debug_suffixes:
        proposals = propose_infl_suffixes(tokens, infl_suffixes)
        print("[DEBUG] Proposed INFL suffixes (candidate, count):")
        for suf, cnt in proposals:
            print(f"    {suf}\t{cnt}")

    for token in tokens:
        token.tagged_form = analyze_yale(token.yale, infl_suffixes)
    return tokens
