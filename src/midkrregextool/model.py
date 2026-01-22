# model.py
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

