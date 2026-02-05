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
    unicode_form: Optional[str] = None
    yale: Optional[str] = None
    is_note: str = "MAIN"
    tagged_form: Optional[str] = None
    context: Optional[str] = None
    matched_part: Optional[str] = None
    # Morph-layer (optional; filled only when available)
    morph_str: str | None = None
    morphs: list[tuple[str,str]] | None = None

