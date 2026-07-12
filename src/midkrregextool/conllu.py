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
    mapping = load_mapping()

    lines = []
    lines.append(f"# sent_id = {sent_id}")
    lines.append(f'# text = {text or ""}')

    current_id = 1
    for token in tokens:
        rows, current_id = token_to_conllu(token, current_id, mapping)
        lines.append(rows)

    return "\n".join(lines)


def token_to_conllu(
    token: Token,
    start_id: int,
    mapping: dict,
) -> tuple[str, int]:

    # Guard clause for token without any morphemes
    if not token.morphs:
        form = token.yale or token.pua
        row = _morph_to_row(start_id, form, "NO-TAGGED-FORM", token.yale, mapping)
        return row, start_id + 1

    morphs = token.morphs

    # tokens with one morpheme

    if len(morphs) == 1:
        form, tag = morphs[0]
        row = _morph_to_row(start_id, form, tag, token.yale, mapping)
        return row, start_id + 1

    # tokens with more than one morpheme
    end_id = start_id + len(morphs) - 1
    mwt_row = "\t".join(
        [
            f"{start_id}-{end_id}",
            token.yale or token.pua,
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
        ]
    )
    rows = [mwt_row]
    for i, (form, tag) in enumerate(morphs):
        rows.append(_morph_to_row(start_id + i, form, tag, None, mapping))

    return "\n".join(rows), end_id + 1


def _morph_to_row(
    token_id: int,
    form: str,
    tag: str,
    yale: Optional[str],
    mapping: dict,
) -> str:
    entry = mapping.get(tag, {})
    upos = entry.get("upos", "_")
    feats = _build_feats(entry.get("feats", {}))
    deprel = entry.get("deprel", "_")

    misc = f"Yale={yale}" if yale else "_"

    return "\t".join(
        [
            str(token_id),
            form,
            form,
            upos,
            tag,
            feats,
            "_",
            deprel,
            "_",
            misc,
        ]
    )
