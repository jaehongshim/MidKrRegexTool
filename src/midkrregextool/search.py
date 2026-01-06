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

            joined = f"{a.yale} {b.yale}"

            # Exclude the matching result if the two tokens differ in their is_note value.
            if a.is_note != b.is_note:
                continue

            if rx.search(joined):
                hits.append((a,b))

        return hits
    else:
        # Monogram search
        hits: Hits = []
        for tok in toks:

            if rx.search(tok.tagged_form):
                hits.append((tok,))

        return hits