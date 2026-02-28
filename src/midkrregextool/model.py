# model.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Token:
    path: str
    source_id: str
    token_index: int
    pua: str
    lang: str
    unicode_form: Optional[str] = None
    yale: Optional[str] = None
    is_note: str = "MAIN"
    coarse_form: Optional[str] = None
    context: Optional[str] = None
    matched_part: Optional[str] = None
    # Morph-layer (optional; filled only when available)
    tagged_form: str | None = None
    morphs: list[tuple[str,str]] | None = None

