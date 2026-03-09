# tagger.py

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from .model import Token


def default_training_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "data" / "training"


def _resolve_training_data(
    training_data: Path, period: int | str | None = None
) -> Path:
    period_tag = _period_tag(period)
    training_dir = (
        training_data if training_data is not None else default_training_dir()
    )
    return training_dir / f"training_{period_tag}.jsonl"


def _period_tag(period: int | str | None) -> str | None:
    if period is None:
        return None
    if isinstance(period, int):
        return f"{period}c"
    p = str(period).strip()
    if not p:
        return None
    return p if p.endswith("c") else f"{p}c"


def _resolve_data_file(filename: str, *, period: int | str | None = None) -> Path:
    """
    Preferred: <repo_root>/data/<period_tag>/<filename>
    Fallback: <this_module_dir>/<filename>
    """
    period_tag = _period_tag(period)
    if period_tag is not None:
        repo_root = Path(__file__).resolve().parents[2]
        cand = repo_root / "data" / period_tag / filename
        if cand.exists():
            return cand
    return Path(__file__).with_name(filename)


def load_infl_suffixes(period: int | str | None = None) -> list[str]:
    path = _resolve_data_file("infl_suffixes.txt", period=period)
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    suffixes = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        suffixes.append(line)

    return sorted(suffixes, key=len, reverse=True)


def load_lemma_lexicon(
    period: int | str | None = None, *, training_data: Path
) -> dict[str, str]:

    def _assign_pos(form_pos: str) -> tuple[str, str]:
        """
        Expected input: kwoksik/N or mwot/NEG/PREFIX-ho/V, returns form and pos
        Fallback: kwoksik or mwot/NEG/PREFIX-ho, returns form and "UNK"
        """

        lem = None
        pos = None

        if "/PREFIX-" in form_pos:
            if "/" in form_pos.split("/PREFIX-")[0]:
                prefix = form_pos.split("/PREFIX")[0].split("/")[0]
                lem = form_pos.split("/PREFIX-")[1].split("/")[0]
                lem = prefix + lem
                pos = form_pos
            else:
                lem = form_pos.split("/PREFIX-")[1]
                pos = form_pos + "/UNK"

        elif "/" in form_pos:
            lem = form_pos.split("/")[0]
            pos = form_pos

        else:
            lem = form_pos
            pos = form_pos + "/UNK"

        if lem is None:
            raise ValueError(
                f"[LEMMA ERROR] Could not extract lemma from form_pos: '{form_pos}'"
            )

        return (lem, pos)

    def _add_from_gold_morph(m: str) -> None:
        """
        Expected input: (LEMMA)/(POS)/LEM or (LEMMA)/(POS)/LEM-(SUFFIXES)
        Fallback: (Lemma)/LEM or (LEMMA)/LEM-(SUFFIXES)
        """
        if m is None:
            return

        m1 = m.split("/LEM")[0]  # The part before "/LEM", e.g., kwoksik/N <-

        [lem, pos] = _assign_pos(m1)

        if lem in lex.keys():
            return
        lex[lem] = pos

    path = _resolve_data_file("lemma_whitelist.txt", period=period)
    lex: dict[str, str] = {}
    current_pos: str | None = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):  # Setting POS tag if line starts with #
                header = line.lstrip("#").strip()
                current_pos = header.split()[0].upper() if header else None
                continue
            if current_pos is None:
                raise ValueError(
                    f"Lemma '{line}' appears before any POS header in {path}"
                )
            pos = line + "/" + current_pos
            lex[line] = pos

    if training_data is not None:
        training_file = _resolve_training_data(training_data, period)

        try:
            with open(training_file, encoding="utf-8") as f:
                for raw in f:
                    obj = json.loads(raw)

                    if not obj:
                        continue

                    for k in ("gold_morph", "gold_morph_a", "gold_morph_b"):
                        m = obj.get(k)
                        if m:
                            _add_from_gold_morph(m)
        except (OSError, json.JSONDecodeError):
            return lex

    return lex


def contains_han(s: str) -> bool:
    for ch in s:
        if "CJK UNIFIED IDEOGRAPH" in unicodedata.name(ch, ""):
            return True
    return False


def analyze_yale(
    yale: str,
    infl_suffixes: list[str],
    lexicon: dict[str, str] | None = None,
    rest_set: set[str] | None = None,
) -> str:

    if not yale:
        return ""  # guard against missing yale

    if not rest_set:
        rest_set = set()

    if not lexicon:
        lexicon = dict()

    lemma_list = sorted(lexicon.keys(), key=len, reverse=True)

    # Check if yale starts with an item in the whitelist.

    for lem in lemma_list:
        if yale.startswith(lem):
            lem_pos = lexicon[lem]
            suffix = yale[len(lem) :]
            if not suffix:
                return f"{lem_pos}/LEM"
            if suffix in rest_set:
                return f"{lem_pos}/LEM-{suffix}/INFL"

    has_han = contains_han(yale)

    # 1. check if yale contains Chinese character
    if has_han:

        # compiling regex pattern for Chinse characters
        m1 = re.match(
            r"^([\u4E00-\u9FFF]+hw?o)(.+?)$", yale
        )  # verb with a Sino-Korean root
        m2 = re.match(
            r"^([\u4E00-\u9FFF]+)([^\u4E00-\u9FFF]+)$", yale
        )  # yale containing a non-Chinese character

        # 1-1. If yale contains a verbalizer, CH+ho/LEM.../INFL
        if m1:
            lem = m1.group(1)
            suf = m1.group(2)
            return f"{lem}/V.CH/LEM-{suf}/INFL"

        # 1-2. If yale contains any non-Chinese characters, parse a boundary between CH/LEM-...
        elif m2:
            lem = m2.group(1)
            suf = m2.group(2)
            return f"{lem}/N.CH/LEM-{suf}/INFL"

        # 1-3. else, yale is lemma.
        else:
            return f"{yale}/N.CH/LEM"

    for suf in infl_suffixes:
        if yale.endswith(suf):
            stem = yale[: -len(suf)]
            if not stem:
                return f"{yale}/LEM"
            if stem not in lexicon:
                continue
            pos = lexicon[stem]
            return f"{pos}/LEM-{suf}/INFL"

    # 3. the whole yale is lemma.

    return f"{yale}/LEM"


def tag_tokens(
    tokens: list[Token],
    rules: list[str],
    *,
    lexicon: dict[str, str],
    rest_set: set[str],
    infl_decomp: dict[str, str] | None = None,
    debug_suffixes: bool = False,
) -> list[Token]:
    """Enrich tokens with morphological tagging for downstream processing."""

    for i, token in enumerate(tokens):
        prev_token = tokens[i - 1] if i > 0 else None
        analyzed = analyze_yale(token.yale, rules, lexicon, rest_set)

        aux_context = False
        if (
            prev_token
            and prev_token.source_id == token.source_id
            and prev_token.is_note == token.is_note
            and prev_token.lang == "kor"
            and token.lang == "kor"
            and prev_token.tagged_form
        ):
            if "/V" in prev_token.tagged_form and (
                "/LEM-a/" in prev_token.tagged_form
                or "/LEM-e/" in prev_token.tagged_form
            ):
                aux_context = True

        if "/INFL" not in analyzed:
            continue

        if infl_decomp is not None:
            infl = infl_from_tagged_form(analyzed)
            segmented_list = infl_decomp.get(infl)
            if not segmented_list:
                continue
            if aux_context and "/V" in analyzed and "/AUX" not in analyzed:
                token.tagged_form = (
                    analyzed.split("/LEM", 1)[0] + "/AUX/LEM-" + segmented_list[0]
                )
            else:
                token.tagged_form = (
                    analyzed.split("/LEM", 1)[0] + "/LEM-" + segmented_list[0]
                )

    return tokens


def infl_from_tagged_form(tagged_form: str) -> str | None:
    if not tagged_form:
        return None
    if "/LEM-" not in tagged_form or "/INFL" not in tagged_form:
        return None
    return tagged_form.split("/LEM-", 1)[1].split("/INFL", 1)[0]
