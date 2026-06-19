from __future__ import annotations

import json
from pathlib import Path

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
