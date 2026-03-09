from __future__ import annotations

import json
import random
import re
from pathlib import Path

from prompt_toolkit import prompt

from .model import Token
from .tagger import _resolve_training_data, default_training_dir

_GLOSS_RX = re.compile(r"/[A-Za-z][A-Za-z0-9_-]*")


def prompt_with_default(message: str, default: str) -> str:
    return prompt(message, default=default)


def candidate_generator(
    token: Token,
    rules: list[str],
    period,
    *,
    token_lookup: dict[tuple[str, int], Token] | None = None,
    infl_decomp: dict[str, list[str]] | None = None,
    lexicon: dict[str, str] | None = None,
) -> list[str]:

    yale = (token.yale or "").strip()
    if not yale:
        return []

    if lexicon is None:
        lexicon = {}
    if infl_decomp is None:
        infl_decomp = {}

    candidates: list[str] = []

    prev_token = None
    if token_lookup is not None:
        prev_token = token_lookup.get((token.source_id, token.token_index - 1))

    aux_context = False
    if prev_token and prev_token.tagged_form:
        if "/V" in prev_token.tagged_form and (
            "/LEM-a/" in prev_token.tagged_form or "/LEM-e/" in prev_token.tagged_form
        ):
            aux_context = True

    if aux_context and infl_decomp:
        for lem, lem_pos in lexicon.items():
            if "/V" not in lem_pos:
                continue
            if yale.startswith(lem):  # lem을 aux 목록으로 바꿀 것.
                rest = yale[len(lem) :]
                if rest in infl_decomp:
                    for segmented in infl_decomp[rest]:
                        candidates.append(f"{lem}/AUX/LEM-{segmented}")
                elif not rest:
                    candidates.append(f"{lem_pos}/LEM")

    m = re.match(r"^([\u4E00-\u9FFF]+hw?o)([^\u4E00-\u9FFF]+)$", yale)
    if m:
        lem = m.group(1)
        rest = m.group(2)
        if rest in infl_decomp:
            for segmented in infl_decomp[rest]:
                candidates.append(f"{lem}/V.CH/LEM-{segmented}")

    else:
        m = re.match(r"^([\u4E00-\u9FFF]+)([^\u4E00-\u9FFF]+)$", yale)
        if m:
            lem = m.group(1)
            rest = m.group(2)
            if rest in infl_decomp:
                for segmented in infl_decomp[rest]:
                    candidates.append(f"{lem}/N.CH/LEM-{segmented}")

    m = re.match(r"^([\u4E00-\u9FFF]+)$", yale)
    if m:
        lem = m.group(1)
        candidates.append(f"{lem}/N.CH/LEM")

    # 1. lexicon-first + learned exact suffix
    for lem, lem_pos in lexicon.items():
        if yale.startswith(lem):
            rest = yale[len(lem) :]
            if rest in infl_decomp:
                for segmented in infl_decomp[rest]:
                    candidates.append(f"{lem_pos}/LEM-{segmented}")
            elif not rest:
                candidates.append(f"{lem_pos}/LEM")

    # 2. suffix-first + learned exact suffix
    for rest, segmented_list in infl_decomp.items():
        if yale.endswith(rest):
            stem = yale[: -len(rest)]
            if stem and stem in lexicon:
                for segmented in segmented_list:
                    candidates.append(f"{lexicon[stem]}/LEM-{segmented}")

    # 3. fallback: lexicon-first + base rules
    for lem, lem_pos in lexicon.items():
        if yale.startswith(lem):
            rest = yale[len(lem) :]
            if not rest:
                continue
            for suf in rules:
                if rest == suf:
                    candidates.append(f"{lem_pos}/LEM-{suf}/INFL")

    # 4. fallback: suffix-first + base rules
    for suf in rules:
        if yale.endswith(suf):
            stem = yale[: -len(suf)]
            if stem and stem in lexicon:
                candidates.append(f"{lexicon[stem]}/LEM-{suf}/INFL")

    return list(dict.fromkeys(candidates))


def format_candidate(token: Token, candidates: list[str] | None = None) -> None:
    print(
        f"[Training] {token.source_id} [{token.path}]\n\t[Token]\t\t{token.unicode_form}\n\t[LANGUAGE]\t{token.lang}\n\t[CONTEXT]\t{token.context}"
    )
    if candidates is None:
        return
    # Display candidates
    for i, cand in enumerate(candidates, start=1):
        if i == 1:
            print(f"\t[CANDIDATES]\t{i}. {cand}")
        else:
            print(f"\t\t\t{i}. {cand}")


def _prompt_gold(
    token: Token, candidates: list[str] | None = None
) -> tuple[str | None, bool]:
    # Returns (gold_morph, quit_training)

    format_candidate(token, candidates)

    while True:
        if candidates:
            raw_ans = input(
                f"[Training] What is the optimal candidate for {token.unicode_form}?\n"
                f"(1-{len(candidates)} to select / s=skip / m=manual input / q=quit) > ".strip()
            )
        else:
            raw_ans = input(
                f"[Training] No candidates for {token.unicode_form} ({token.yale}). "
                f"(m=manual / s=skip / q=quit) > "
            ).strip()

        ans = raw_ans.lower()

        if ans == "q":
            return None, True

        if ans == "s":
            return None, False

        # Manual input
        if ans == "m":
            default = ""

            if any("\u4e00" <= ch <= "\u9fff" for ch in token.yale):
                default = "".join(
                    ch for ch in token.unicode_form if "\u4e00" <= ch <= "\u9ffff"
                )

            raw = prompt_with_default(
                "Please type your desired gold_morph: ", default
            ).strip()

            if not raw:
                print("[Training] Empty input. Try again.")
                continue

            return raw, False

        # Direct gold without typing "m"
        if _GLOSS_RX.search(raw_ans) is not None:
            raw = raw_ans.strip()
            return raw, False

        # Pick from candidates
        if candidates and ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx], False
            else:
                print("[Training] Out of range. Try again.")
                continue

        print("[ERROR] Invalid input.")


def training_priority(
    token: Token,
    *,
    lexicon: dict[str, str],
    known_rests: set[str],
    candidates: list[str],
) -> tuple[int, str]:
    yale = (token.yale or "").strip()

    known_stem = False
    known_rest = False

    for lem in lexicon.keys():
        if yale.startswith(lem):
            known_stem = True
            rest = yale[len(lem) :]
            if rest in known_rests:
                known_rest = True
            break

    if not known_rest:
        for rest in known_rests:
            if yale.endswith(rest):
                known_rest = True
                stem = yale[: -len(rest)]
                if stem in lexicon:
                    known_stem = True
                break

    # lower number = higher priority
    if not known_stem and not known_rest:
        return (0, yale)
    if known_stem and not known_rest:
        return (1, yale)
    if not known_stem and known_rest:
        return (2, yale)
    return (3, yale)


def train(
    tokens: list[Token] | list[tuple[Token, Token]],
    rules: list[str],
    period: int,
    training_data: Path | None,
    lexicon: dict[str, str] | None = None,
    token_lookup: dict[tuple[str, int], Token] | None = None,
) -> None:

    period_tag = f"{period}c"

    print("[INFO] Training mode is ON.")

    if not period:
        raise ValueError("Period must be specified in training mode.")

    out_dir = training_data if training_data is not None else default_training_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"training_{period_tag}.jsonl"

    infl_decomp = load_infl_decomp_from_training(out_path)

    # Load token gold list
    token_gold_file = load_token_gold_morph(out_path)
    token_gold = load_token_gold_morph(out_path)

    # If first item is a tuple, training unit is a bigram: (Token, Token)

    is_bigram = len(tokens) > 0 and isinstance(tokens[0], tuple)

    with open(out_path, "a", encoding="utf-8") as f:

        quit_training = False

        random.shuffle(tokens)

        # Branch for monogram-training mode

        if not is_bigram:

            for token in tokens:
                # Guard clause
                gold_morph: str | None = None

                if token.unicode_form in token_gold:
                    continue

                candidates = candidate_generator(
                    token,
                    rules,
                    period,
                    token_lookup=token_lookup,
                    infl_decomp=infl_decomp,
                    lexicon=lexicon,
                )
                gold_morph, quit_training = _prompt_gold(token, candidates)

                if quit_training:
                    return

                if gold_morph is None:
                    continue

                obj = {
                    "period": period_tag,
                    "token": token.unicode_form,
                    "gold_morph": gold_morph,
                }

                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                f.flush()

                token_gold[token.unicode_form] = gold_morph

        # Branch for bigram-training mode

        else:

            for a, b in tokens:
                skip_bigram = False
                # Bigram training: label token A then token B
                gold_morph_a: str | None = None
                gold_morph_b: str | None = None

                # Let the user know that we are entering the bigram loop
                print(f"[BIGRAM] {a.unicode_form} {b.unicode_form}")

                for side, token in (("a", a), ("b", b)):
                    label = "A" if side == "a" else "B"

                    print(f"[BIGRAM]-{label} tagging token: {token.unicode_form}")

                    gold_morph: str | None = None

                    if token.unicode_form in token_gold:
                        cached_gold_morph = token_gold[token.unicode_form]
                        print(
                            f"[BIGRAM-{label}] already labeled -> {cached_gold_morph}"
                        )

                        if side == "a":
                            gold_morph_a = cached_gold_morph
                        else:
                            gold_morph_b = cached_gold_morph

                        continue

                    else:
                        candidates = candidate_generator(
                            token,
                            rules,
                            period,
                            token_lookup=token_lookup,
                            infl_decomp=infl_decomp,
                            lexicon=lexicon,
                        )
                        gold_morph, quit_training = _prompt_gold(token, candidates)

                        if quit_training:
                            return
                        if gold_morph is None:
                            skip_bigram = True
                            break

                        token_gold[token.unicode_form] = gold_morph

                        if side == "a":
                            gold_morph_a = gold_morph
                        else:
                            gold_morph_b = gold_morph

                if skip_bigram:
                    continue

                # Save an instance of bigram as a line in the jsonl training file.
                # Use bigram as a key to avoid overlapping labeling
                obj = {
                    "period": period_tag,
                    "bigram": f"{a.unicode_form} {b.unicode_form}",
                    "gold_morph_a": gold_morph_a,
                    "gold_morph_b": gold_morph_b,
                }

                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

                # If dict does not have the gold of each token, save it as a monogram result as well.

                for side, token in (("a", a), ("b", b)):
                    if token.unicode_form in token_gold_file:
                        continue

                    if side == "a":
                        obj_mono = {
                            "period": period_tag,
                            "token": a.unicode_form,
                            "gold_morph": gold_morph_a,
                        }
                        token_gold_file[a.unicode_form] = gold_morph_a
                    else:
                        obj_mono = {
                            "period": period_tag,
                            "token": b.unicode_form,
                            "gold_morph": gold_morph_b,
                        }
                        token_gold_file[b.unicode_form] = gold_morph_b

                    f.write(json.dumps(obj_mono, ensure_ascii=False) + "\n")

                f.flush()

                if quit_training:
                    break

    print(f"[INFO] Training data saved to {out_path}")


def load_token_gold_morph(training_path: Path) -> dict[str, str]:
    token_gold_morph: dict[str, str] = {}

    if not training_path.exists():
        return token_gold_morph

    with open(training_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            token = obj.get("token")
            gold_morph = obj.get("gold_morph")

            if token and isinstance(gold_morph, str) and gold_morph:
                token_gold_morph[token] = gold_morph

    return token_gold_morph


def load_infl_decomp_from_training(training_path: Path) -> dict[str, list[str]]:
    d: dict[str, list[str]] = {}

    try:
        with open(training_path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)

                for key in ("gold_morph", "gold_morph_a", "gold_morph_b"):
                    gm = obj.get(key)
                    if not isinstance(gm, str) or not gm:
                        continue

                    parts = gm.split("-")
                    if len(parts) < 2:
                        continue

                    segmented = "-".join(parts[1:]).strip()
                    infl_surface = "".join(
                        seg.split("/", 1)[0] for seg in parts[1:] if "/" in seg
                    )

                    if infl_surface:
                        if infl_surface not in d:
                            d[infl_surface] = []
                        if segmented not in d[infl_surface]:
                            d[infl_surface].append(segmented)
    except Exception as e:
        print(f"[ERROR] {e}. infl_decomp has not been created.")

    return d


def load_rest_surfaces_from_training(
    training_data: Path, period: int | str | None = None
) -> set[str]:
    rest_set: set[str] = set()

    def _add_from_gold_morph(m: str) -> None:
        parts = m.split("-")
        if len(parts) < 2:
            return

        surfaces = [seg.split("/", 1)[0] for seg in parts[1:] if "/" in seg]
        if surfaces:
            rest_set.add("".join(surfaces))

    training_file = _resolve_training_data(training_data, period)

    try:
        with open(training_file, encoding="utf-8") as f:
            for raw in f:
                obj = json.loads(raw)

                for k in ("gold_morph", "gold_morph_a", "gold_morph_b"):
                    m = obj.get(k)
                    if m:
                        _add_from_gold_morph(m)
    except (OSError, json.JSONDecodeError):
        return rest_set

    return rest_set
