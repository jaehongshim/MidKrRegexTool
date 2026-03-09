# search.py

"""
Regex-based search tool over token representations (default: Yale).

search_tokens(tokens: list[Token], pattern: str, token_repr: str, flags=0)
"""

from __future__ import annotations

import re
from typing import TypeAlias

from .model import Token

Hits: TypeAlias = list[tuple[Token, ...]]


def _s(tok: Token, *, token_repr: str | None) -> str | None:
    if token_repr == "yale":
        return tok.yale
    elif token_repr == "tagged_form":
        return tok.tagged_form
    else:
        return tok.tagged_form or tok.yale


def search_tokens(tokens: list[Token], pattern: str, token_repr: str, flags=0) -> Hits:
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

            joined = f"{_s(a, token_repr=token_repr) or ''} {_s(b, token_repr=token_repr) or ''}"
            # print(f"[DEBUG] Joined: {joined}")
            # print(joined)

            # Exclude the matching result if the two tokens differ in their is_note value.
            if a.is_note != b.is_note:
                continue

            m = rx.search(joined)
            if m:
                a.matched_part = m.group(0)
                hits.append((a, b))

        return hits
    else:
        # Monogram search
        hits: Hits = []
        for tok in toks:

            m = rx.search(_s(tok, token_repr=token_repr) or "")
            if m:
                tok.matched_part = m.group(0)
                hits.append((tok,))

        return hits
