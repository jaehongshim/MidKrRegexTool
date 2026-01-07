# model.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Token:
    source_id: str
    token_index: int
    pua: str
    unicode_form: Optional[str] = None
    yale: Optional[str] = None
    is_note: str = "MAIN"
    tagged_form: Optional[str] = None

class DebugOptions:
    suffix_proposals: bool = False
    suffix_must_endwith: str | None = None
    dump_lemma_seed: bool = False