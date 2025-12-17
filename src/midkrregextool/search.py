# search.py

"""
Regex-based search tool over token representations (default: Yale).

Primary entry point:
    search_tokens(tokens, patterns, *, flags=0)
"""

from __future__ import annotations

import re
from typing import Iterable

from .model import Token

def search_tokens(tokens: Iterable[Token], pattern: str, *, flags=0) -> list[Token] | list[tuple[Token, Token]]:
    """
    Input:

    Output:
    
    """
    rx = re.compile(pattern, flags)
    toks = list(tokens)

    # Bigram search
    if " " in pattern:
        hits: list[tuple[Token, Token]] = []
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
        hits: list[Token] = []
        for tok in toks:

            if rx.search(tok.yale):
                hits.append(tok)

        return hits