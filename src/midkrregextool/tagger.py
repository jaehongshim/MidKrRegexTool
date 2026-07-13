# tagger.py

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from .model import Token

CATEGORY_CHANGERS = {
    "NMLZ": "N",
}


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

    lex: dict[str, str] = {}

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
    lexicon: dict[str, str] | None = None,
    infl_decomp: dict[str, list[str]] | None = None,
) -> list[str]:

    candidates = []

    if not yale:
        return []  # guard against missing yale

    if not infl_decomp:
        infl_decomp = {}

    if not lexicon:
        lexicon = dict()

    lemma_list = sorted(lexicon.keys(), key=len, reverse=True)

    # First, prefer exact surface lemma matches already present in the lexicon.
    if yale in lexicon:
        candidates.append(f"{lexicon[yale]}/LEM")

    # Then check lemmas with restored material in parentheses.
    # Ignore the parenthesized part only for surface matching.

    for lem in lemma_list:
        surface_lem = re.sub(r"\([^)]*\)", "", lem)

        if not surface_lem:
            continue

        if yale.startswith(surface_lem):
            suffix = yale[len(surface_lem) :]

            if "(o)" in lem and suffix and not suffix.startswith("w"):
                continue

            lem_pos = lexicon[lem]

            if not suffix:
                # print(f"[DEBUG] {yale} -> {lem_pos}/LEM")
                candidates.append(f"{lem_pos}/LEM")
            if suffix in infl_decomp:
                # print(f"[DEBUG] {yale} -> {lem_pos}/LEM-{suffix}/INFL")
                candidates.append(f"{lem_pos}/LEM-{suffix}/INFL")

    has_han = contains_han(yale)

    # 1. check if yale contains Chinese character
    if has_han:

        # compiling regex pattern for Chinse characters
        m1 = re.match(
            r"^([\u4E00-\u9FFF]+hw?o)(.+?)$", yale
        )  # verb with a Sino-Korean root
        m2 = re.match(
            r"^(.+?)([\.A-Za-z]+)$", yale
        )  # yale containing a non-Chinese character

        # 1-1. If yale contains a verbalizer, CH+ho/LEM.../INFL
        if m1:
            lem = m1.group(1)
            suf = m1.group(2)
            # print(f"[DEBUG] {yale} -> {lem}/V.CH/LEM-{suf}/INFL")
            candidates.append(f"{lem}/V.CH/LEM-{suf}/INFL")

        # 1-2. If yale contains any non-Chinese characters, parse a boundary between CH/LEM-...
        elif m2:
            lem = m2.group(1)
            suf = m2.group(2)
            # print(f"[DEBUG] {yale} -> {lem}/N.CH/LEM-{suf}/INFL")
            candidates.append(f"{lem}/N.CH/LEM-{suf}/INFL")

        # 1-3. else, yale is lemma.
        else:
            # print(f"[DEBUG] {yale} -> {yale}/N.CH/LEM")
            candidates.append(f"{yale}/N.CH/LEM")

    return list(dict.fromkeys(candidates))


def tag_tokens(
    tokens: list[Token],
    *,
    lexicon: dict[str, str],
    infl_decomp: dict[str, str] | None = None,
    pos_to_allowed_morphemes: dict[str, set[str]] | None = None,
) -> list[Token]:
    """Enrich tokens with morphological tagging for downstream processing."""

    def _segmented_chain_allowed(analyzed: str, segmented: str) -> bool:
        left = analyzed.split("/LEM", 1)[0]
        if "/" not in left:
            return True

        parts = segmented.split("-")
        if not parts:
            return True

        first_surface = parts[0].split("/", 1)[0]

        # Parenthetical vowel contraction conditions
        if "(o)" in left:
            if not first_surface.startswith("wo"):
                return False

        if "(u)" in left:
            if not first_surface.startswith("wu"):
                return False

        if "(a)" in left:
            if not first_surface.startswith("a"):
                return False

        if "(e)" in left:
            if not first_surface.startswith("e"):
                return False

        if not pos_to_allowed_morphemes:
            return True

        state = left.split("/")[-1]

        for part in parts:
            allowed = pos_to_allowed_morphemes.get(state)
            if allowed and part not in allowed:
                return False

            tag = part.split("/")[-1]
            if tag in CATEGORY_CHANGERS:
                state = CATEGORY_CHANGERS[tag]

        return True

    pending_token_idx = []

    for i, token in enumerate(tokens):
        prev_token = tokens[i - 1] if i > 0 else None

        analyzed_list = analyze_yale(
            token.yale,
            lexicon,
            infl_decomp,
        )
        # print(f"[DEBUG] {token.yale} -> {analyzed}.")

        if not analyzed_list:
            token.tagged_candidates = [token.yale + "/" + "NO-TAGGED-FORM"]
            token.tagged_form = token.tagged_candidates[0]
            continue

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
                prev_token.tagged_form.endswith("/CONN")
            ):
                aux_context = True

        candidates: list[str] = []

        for analyzed in analyzed_list:
            if "/INFL" not in analyzed:
                if analyzed.endswith("/LEM"):
                    if "/" in analyzed.split("/LEM")[0]:
                        candidates.append(analyzed)
                        continue
                else:
                    continue

            if infl_decomp is not None:
                infl = infl_from_tagged_form(analyzed)
                segmented_list = infl_decomp.get(infl)
                if not segmented_list:
                    candidates.append(analyzed)
                    continue

                filtered_segmented = [
                    segmented
                    for segmented in segmented_list
                    if _segmented_chain_allowed(analyzed, segmented)
                ]
                for segmented in filtered_segmented:
                    if aux_context and "/V" in analyzed and "/AUX" not in analyzed:
                        candidates.append(
                            analyzed.split("/LEM", 1)[0] + "/AUX/LEM-" + segmented
                        )
                    else:
                        candidates.append(
                            analyzed.split("/LEM", 1)[0] + "/LEM-" + segmented
                        )

        if not candidates:
            token.tagged_candidates = [token.yale + "/NO-TAGGED-FORM"]
        else:
            token.tagged_candidates = list(dict.fromkeys(candidates))

        token.tagged_form = token.tagged_candidates[0]

        if ("/DAT" in token.tagged_form) or ("/GEN" in token.tagged_form):
            pending_token_idx.append(i)

    # post-adjustment

    nominal_tag_re = re.compile(r"(/N(\.[A-Z]+)?|NMLZ)$")

    def _has_nominal_tag(tagged_form: str | None) -> bool:
        if tagged_form is None:
            return False

        for morph in tagged_form.split("-"):
            if nominal_tag_re.search(morph):
                return True
        return False

    for i in pending_token_idx:

        # print(f"[DEBUG] pending token: {tokens[i].tagged_form}")
        # print(f"\tNext token: {tokens[i+1].tagged_form}")

        gen_context = False
        if i + 1 >= len(tokens):
            continue

        if _has_nominal_tag(tokens[i + 1].tagged_form):
            gen_context = True
            # print(
            #     f"[DEBUG] gen_context set to {gen_context} for {tokens[i].tagged_form}"
            # )
            # print(f"\ttokens[i+1].tagged_form: {tokens[i+1].tagged_form}")

        # if tokens[i].unicode_form == "알ᄑᆡᆺ":
        #     print("[DEBUG A] i =", i)
        #     print("[DEBUG B] current =", tokens[i].tagged_form)
        #     print("[DEBUG C] next    =", tokens[i + 1].tagged_form)
        #     print("[DEBUG D] gen_context =", gen_context)
        #     print(
        #         "[DEBUG E] oy/DAT in current =",
        #         "oy/DAT" in tokens[i].tagged_form if tokens[i].tagged_form else None,
        #     )
        #     print(
        #         "[DEBUG F] uy/DAT in current =",
        #         "uy/DAT" in tokens[i].tagged_form if tokens[i].tagged_form else None,
        #     )

        if (
            gen_context
            and (tokens[i].tagged_form is not None)
            and (
                ("oy/DAT" in tokens[i].tagged_form)
                or ("uy/DAT" in tokens[i].tagged_form)
            )
        ):
            # print(f"[DEBUG] Original tag: {tokens[i].tagged_form}")
            tokens[i].tagged_form = tokens[i].tagged_form.replace("/DAT", "/GEN")
            # print(f"[DEBUG] New tag: {tokens[i].tagged_form}")

    return tokens


def infl_from_tagged_form(tagged_form: str) -> str | None:
    if not tagged_form:
        return None
    if "/LEM-" not in tagged_form or "/INFL" not in tagged_form:
        return None
    return tagged_form.split("/LEM-", 1)[1].split("/INFL", 1)[0]
