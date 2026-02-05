# search.py

"""
Regex-based search tool over token representations (default: Yale).

Primary entry point:
    search_tokens(tokens, patterns, *, flags=0)
"""

from __future__ import annotations

import re
from typing import Iterable, TypeAlias

from .model import Token

Hits: TypeAlias = list[tuple[Token, ...]]

def _s(tok: Token) -> str:
    return tok.morph_str or tok.tagged_form

def search_tokens(tokens: list[Token], pattern: str, flags=0) -> Hits:
    """
    Input:

    Output:
    
    """
    rx = re.compile(pattern, flags)
    toks = list(tokens)

    # Bigram search
    if " " in pattern:
        hits: Hits = []
        for i in range(len(toks) - 1):
            a, b = toks[i], toks[i + 1]

            joined = f"{_s(a)} {_s(b)}"
            # print(joined)

            # Exclude the matching result if the two tokens differ in their is_note value.
            if a.is_note != b.is_note:
                continue

            m = rx.search(joined)
            if m:
                a.matched_part = m.group(0)
                hits.append((a,b))

        return hits
    else:
        # Monogram search
        hits: Hits = []
        for tok in toks:

            m = rx.search(_s(tok) or "")
            if m:
                tok.matched_part = m.group(0)
                hits.append((tok,))

        return hits