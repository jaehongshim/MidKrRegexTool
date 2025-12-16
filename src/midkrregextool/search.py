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

def search_tokens(tokens: Iterable[Token], pattern: str, *, flags=0) -> list[Token]:
    """
    Input:

    Output:
    
    """
    rx = re.compile(pattern, flags)

    hits: list[Token] = []
    for tok in tokens:
        # Skip tokens that do not have a Yale form yet.
        if tok.yale is None:
            continue

        if rx.search(tok.yale):
            hits.append(tok)

    return hits