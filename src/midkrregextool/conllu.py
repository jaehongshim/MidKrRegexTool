from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .model import Token

_DEFAULT_MAPPING = Path(__file__).parent.parent.parent / "data" / "ud_mapping.json"


def load_mapping(path: Path = _DEFAULT_MAPPING) -> dict:

    raw_text = path.read_text(encoding="utf-8")

    raw = json.loads(raw_text)

    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _build_feats(feats_dict: dict) -> str:
    """{'Case': 'Nom', 'Polite':'Elev'} -> 'Case=Nom|Polite=Elev'"""

    if not feats_dict:
        return "_"

    sorted_dict = sorted(feats_dict.items())

    return "|".join(f"{k}={v}" for (k, v) in sorted_dict)


def tokens_to_conllu(
    tokens: list[Token],
    sent_id: str,
    text: Optional[str] = None,
) -> str:
    mapping = load_mapping

    lines = []
    lines.append(f"# sent_id = {sent_id}")
    lines.append(f'# text = {text or ""}')

    current_id = 1
    for token in tokens:
        rows, current_id = token_to_conllu(token, current_id, mapping)
        lines.append(rows)

    return "\n".join(lines)
