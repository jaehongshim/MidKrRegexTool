from __future__ import annotations
from .model import Token
from .tagger import _resolve_training_data
from pathlib import Path
import re, json, random


_GLOSS_RX = re.compile(r"/[A-Za-z][A-Za-z0-9_-]*")

def _period_tag(period: int | str | None) -> str | None:
    if period is None:
        return None
    if isinstance(period, int):
        return f"{period}c"
    p = str(period).strip()
    if not p:
        return None
    return p if p.endswith("c") else f"{p}c"

def candidate_generator(
        token: Token, 
        rules: list[str],
        period,
        *,
        infl_decomp: dict[str, str] | None = None,
        lexicon: dict[str, str] | None = None
        ) -> list[str]:
    
    yale = (token.yale or "").strip()
    if not yale:
        return []
    
    infl_suffixes = sorted(rules, key=len, reverse=True)
    
    # Load lemma whitelist
    if lexicon is None:
        lexicon = dict()

    candidates: list[str] = []
    
    # If we have learned infl decompositions, prepend morph-level candidates
    if infl_decomp is not None:
        morph_candidates: list[str] = []
        for cand in candidates:                     # cand: stem/LEM-suf/INFL
            infl = extract_infl_from_gold(cand)
            if infl in infl_decomp:
                segmented = infl_decomp[infl]       # e.g., si/HON-li/FUT-...
                stem = cand.split("/LEM-", 1)[0]    # e.g., ka
                if stem in lexicon.keys():
                    candidates.append(f"{lexicon[stem]}/LEM-{segmented}")
                morph_candidates.append(f"{stem}/LEM-{segmented}")
    
    for suf in infl_suffixes:
        if yale.endswith(suf):
            stem = yale[:-len(suf)]
            stem = stem.rstrip("-")

            if not stem:
                continue

            if stem in lexicon.keys():
                candidates.append(f"{lexicon[stem]}/LEM-{suf}/INFL")

            candidates.append(f"{stem}/LEM-{suf}/INFL")

        candidates = list(dict.fromkeys(morph_candidates + candidates))

    return candidates

def format_candidate(token: Token, candidates: list[str] | None = None) -> None:
    print(f"[Training] {token.source_id} [{token.path}]\n\t[Token]\t\t{token.unicode_form}\n\t[CONTEXT]\t{token.context}")
    if candidates is None:
        return    
    # Display candidates
    for i, cand in enumerate(candidates, start=1):
        if i == 1:
            print(f"\t[CANDIDATES]\t{i}. {cand}")
        else:
            print(f"\t\t\t{i}. {cand}")

def _prompt_gold(token: Token, candidates: list[str] | None = None) -> tuple[str | None, str | None, bool]:
    # Returns (gold, gold_morph, quit_training)

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
            return None, None, True
        
        if ans == "s":
            return None, None, False
        
        # Manual input
        if ans == "m":
            raw = input("Please type your desired tagged form: ").strip()

            if is_coarse_gold(raw):
                return raw, None, False
            
            parsed = parse_gold_morph_to_coarse(raw)
            if parsed is None:
                print("[Training] Invalid manual input format. Try again.")
                continue

            gold, gold_morph = parsed
            return gold, gold_morph, False
        
        # Direct gold without typing "m"
        if _GLOSS_RX.search(raw_ans) is not None: # ans contains a gloss.
            raw = raw_ans.strip()

            if is_coarse_gold(raw):
                return raw, None, False
            
            parsed = parse_gold_morph_to_coarse(raw)
            if parsed is None:
                print("[Training] Invalid tagged form. Try again.")
                continue

            gold, gold_morph = parsed
            return gold, gold_morph, False
        
        # Pick from candidates
        if candidates and ans.isdigit():
            idx = int(ans)-1
            if 0 <= idx < len(candidates):
                if candidates[idx].endswith("/LEM"):
                    return candidates[idx], candidates[idx], False
                elif candidates[idx].endswith("/INFL"):
                    return candidates[idx], None, False
                else:
                    return candidates[idx], candidates[idx], False
            else:
                print("[Training] Out of range. Try again.")
                continue
        
        print("[ERROR] Invalid input.")



def train(tokens: list[Token]|list[tuple[Token,Token]], rules: list[str], period: int, training_data: Path | None, lexicon: dict[str, str] | None = None) -> None:

    period_tag = f"{period}c"

    print(f"[INFO] Training mode is ON.")

    if not period:
        raise ValueError("Period must be specified in training mode.")

    # Locate or create training data file

    out_dir = training_data if training_data is not None else default_training_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"training_{period_tag}.jsonl"
    infl_decomp = load_infl_decomp_from_training(out_path,period=period)

    # Load token gold list
    token_gold_file = load_token_gold(out_path) 
    token_gold = load_token_gold(out_path)

    # If first item is a tuple, training unit is a bigram: (Token, Token)

    is_bigram = (len(tokens) > 0 and isinstance(tokens[0], tuple))

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

                candidates = candidate_generator(token, rules, period, infl_decomp=infl_decomp, lexicon=lexicon)

                if token.unicode_form in token_gold:
                    gold = token_gold[token.unicode_form]
                    if gold in candidates:
                        candidates = [gold] + [c for c in candidates if c != gold]

                gold, gold_morph, quit_training = _prompt_gold(token, candidates)
                if quit_training:
                    return
                
                # If skip, do nothing. 
                elif gold == None and gold_morph == None and quit_training == False:
                    continue
                
                # Normalize: if selected gold is morph-style, convert to coarse gold + gold_morph
                if gold is not None and not is_coarse_gold(gold):
                    parsed = parse_gold_morph_to_coarse(gold)
                    if parsed is not None:
                        gold, gold_morph = parsed

                obj = {"period": period_tag, "token": token.unicode_form, "gold": gold}

                if gold_morph is not None:
                    obj["gold_morph"] = gold_morph
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                f.flush()

                # IMPORTANT: do not cache None
                if gold is not None:
                    token_gold[token.unicode_form] = gold
                

        # Branch for bigram-training mode
        
        else:

            for a, b in tokens:
                skip_bigram = False
                # Bigram training: label token A then token B
                gold_a = None
                gold_b = None
                gold_morph_a: str | None = None
                gold_morph_b: str | None = None

                # Let the user know that we are entering the bigram loop
                print(f"[BIGRAM] {a.unicode_form} {b.unicode_form}")
                
                for side, token in (("a", a), ("b", b)):
                    label = "A" if side == "a" else "B"
                    
                    print(f"[BIGRAM]-{label} tagging token: {token.unicode_form}")

                    gold_morph: str | None = None
                    

                    if token.unicode_form in token_gold:
                        cached = token_gold[token.unicode_form]
                        print(f"[BIGRAM-{label}] already labeled -> {cached}")

                        if token.tagged_form in token_gold:
                            cached_morph = token_gold[token.tagged_form]
                            print(f"[BIGRAM-{label}] segmented -> {cached_morph}")

                            if side == "a":
                                gold_a = cached
                                gold_morph_a = cached_morph
                            else:
                                gold_b = cached
                                gold_morph_b = cached_morph

                            continue

                        raw = input(
                            f"Optional: provide more detailed glosses for {token.unicode_form} "
                            f"(coarse={cached}). Press Enter to skip: "
                            ).strip()
                            
                        if side == "a":
                            gold_a = cached
                            if raw:
                                gold_morph_a = raw
                                token_gold[token.tagged_form] = raw
                        
                        else:
                            gold_b = cached
                            if raw:
                                gold_morph_b = raw
                                token_gold[token.tagged_form] = raw

                        continue

                    else:
                        candidates = candidate_generator(token, rules, period, infl_decomp=infl_decomp, lexicon=lexicon)

                        gold, gold_morph, quit_training = _prompt_gold(token, candidates)

                        if quit_training:
                            return
                        elif gold == None and gold_morph == None and quit_training == False:
                            skip_bigram = True
                            break

                        # Normalize: (same as monogram)
                        if gold is not None and not is_coarse_gold(gold):
                            parsed = parse_gold_morph_to_coarse(gold)
                            if parsed is not None:
                                gold, gold_morph = parsed

                        # Cache only real labels
                        if gold is not None:
                            token_gold[token.unicode_form] = gold

                        if side == "a":
                            gold_a = gold
                            gold_morph_a = gold_morph
                        else:
                            gold_b = gold
                            gold_morph_b = gold_morph

                if skip_bigram:
                    continue

                # Save an instance of bigram as a line in the jsonl training file.
                # Use bigram as a key to avoid overlapping labeling
                obj = {
                    "period": period_tag,
                    "bigram": f"{a.unicode_form} {b.unicode_form}",
                    "gold_a": gold_a,
                    "gold_b": gold_b,
                }
                if gold_morph_a is not None:
                    obj["gold_morph_a"] = gold_morph_a
                if gold_morph_b is not None:
                    obj["gold_morph_b"] = gold_morph_b

                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

                # If dict does not have the gold of each token, save it as a monogram result as well.

                for side, token in (("a", a), ("b", b)):
                    if token.unicode_form not in token_gold_file:
                        if side == "a":
                            obj_mono = {
                                "period": period_tag,
                                "token": a.unicode_form,
                                "gold": gold_a
                            }
                            if gold_morph_a is not None:
                                obj_mono["gold_morph"] = gold_morph_a
                        else:
                            obj_mono = {
                                "period": period_tag,
                                "token": b.unicode_form,
                                "gold": gold_b
                            }
                            if gold_morph_b is not None:
                                obj_mono["gold_morph"] = gold_morph_b
                
                f.write(json.dumps(obj_mono, ensure_ascii=False) + "\n")

                token_gold_file[token.unicode_form] = obj_mono["gold"]

                f.flush()

                if quit_training:
                    break

    print(f"[INFO] Training data saved to {out_path}")

def default_training_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "data" / "training"

def load_token_gold(training_path: Path) -> dict[str, str]:
    token_gold: dict[str, str] = {}

    if not training_path.exists():
        return token_gold
    
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
            gold = obj.get("gold")
            gold_morph = obj.get("gold_morph")
            if token and isinstance(gold, str) and gold:
                token_gold[token] = gold
            elif token and isinstance(gold_morph, str) and gold_morph:
                token_gold[token] = gold_morph

    return token_gold

def is_coarse_gold(s: str) -> bool:
    s = (s or "").strip()

    if s.endswith("/LEM") and (" " not in s):
        return True
    
    return ("/LEM-" in s) and ("/INFL" in s)

def parse_gold_morph_to_coarse(gold_morph: str) -> tuple[str, str] | None:
    """
    Convert a morph-level string like:
        ho/ROOT-si/HON-li/FUT-le/ASP-la/C
    into coarse:
        ho/LEM-sililela/INFL

    Minimal assumption (intentionally simple):
    - The first morph is treated as LEM surface.
    - All remaining morph forms are concatenated as INFL surface.
    """
    parts = [p.strip() for p in gold_morph.split("-") if p.strip()]
    if len(parts) < 2:
        return None
    
    morphs: list[tuple[str, str]] = []
    for p in parts:
        if "/" not in p:
            return None
        if "/PREFIX" in p:
            form, tag = p.split("/", 1) # mwot/NEG/PREFIX -> form = mwot, tag = NEG/PREFIX 
        else:
            form, tag = p.split("/", 1) # si/SUBJ/HON -> form = si, tag = SUBJ/HON
        form = form.strip()
        tag = tag.strip()
        if not form or not tag:
            return None
        morphs.append((form,tag))

    if "PREFIX" in morphs[0][1]: # the first morpheme is a prefix.
        prefix_form = morphs[0][0] + "/PREFIX-"
        lem_form = prefix_form + morphs[1][0]  
        infl_surface = "".join(m[0] for m in morphs[2:])
    else:
        lem_form = morphs[0][0]
        infl_surface = "".join(m[0] for m in morphs[1:])
    if not lem_form or not infl_surface:
        return None
    
    coarse = f"{lem_form}/LEM-{infl_surface}/INFL"
    return coarse, gold_morph

def extract_infl_from_gold(gold: str) -> str | None:
    if "/LEM-" not in gold or "/INFL" not in gold:
        return None
    return gold.split("/LEM-", 1)[1].split("/INFL", 1)[0]

def load_learned_infl_suffixes(training_path: Path, *, period: int) -> list[str]:
    infls = set()
    """
    Load learned INFL suffixes from a JSONL training file.

    - If training_path is a directory, it resolves to: training_{period}c.jsonl
    - If training_path is a file, it is used as-is.

    The file is expected to be JSONL where each line contains a dict with key "gold."
    """

    training_path = Path(training_path)

    if training_path.is_dir():
        training_path = training_path / f"training_{period}c.jsonl"

    infls: set[str] = set()

    try:
        with open(training_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                obj = json.loads(line)
                gold = obj.get("gold")

                # If gold is properly defined, that means we are in the monogram loop.

                if isinstance(gold, str) and gold and gold != "None":
                    infl = extract_infl_from_gold(gold)
                    if infl:
                        infls.add(infl)
                    continue

                # bigram loop

                for key in ("gold_a", "gold_b"):
                    gold_part = obj.get(key)
                    if not isinstance(gold_part, str):
                        continue

                    infl = extract_infl_from_gold(gold_part)
                    if infl:
                        infls.add(infl)

    except FileNotFoundError:
        return []
    
    result = sorted(infls, key=len, reverse=True)
    return result

def load_infl_decomp_from_training(training_path: Path, *, period:int) -> dict[str, str]:
    """
    Return a dict: infl_surface -> segmented_infl_string
    Example:
        "sililela" -> "si/HON-li/FUT-le/IPFV-la/DECL"
    """
    d: dict[str, str] = {}

    try:
        f = open(training_path, "r", encoding="utf-8")
        for line in f:
            obj = json.loads(line)

            gm = obj.get("gold_morph")
            if not isinstance(gm, str) or not gm:
                continue

            gold = obj["gold"]
            gold_morph = obj["gold_morph"]
            

            infl = extract_infl_from_gold(gold)
            if infl is None:
                continue
            segmented = gold_morph.split("/LEM-",1)[1].strip()
            d[infl] = segmented
    except Exception as e:
        print(f"[ERROR] {e}. infl_decomp has not been created.")

    return d

def load_rest_surfaces_from_training(training_data: Path, period: int | str | None = None) -> set[str]:
    rest_set: set[str] = set()

    def _add_from_gold_morph(m: str) -> None:
        if len(m.split("/LEM",1)) == 1:
            return
        rest = m.split("/LEM", 1)[1]
        surfaces = [seg.split("/", 1)[0] for seg in rest.split("-")]
        rest_set.add("".join(surfaces))

    def _add_from_gold(g: str) -> None:
        m = re.search(r"/LEM-(.+?)/INFL$", g)
        if m:
            rest_set.add(m.group(1))

    training_file = _resolve_training_data(training_data, period)

    try:
        f = open(training_file, encoding="utf-8")
        for raw in f:
            obj = json.loads(raw)

            used = False
            for k in ("gold_morph", "gold_morph_a", "gold_morph_b"):
                m = obj.get(k)
                if m:
                    _add_from_gold_morph(m)
                    used = True

            if used:
                continue

            for k in ("gold", "gold_a", "gold_b"):
                g = obj.get(k)
                if g:
                    _add_from_gold(g)
    except:
        return

    return rest_set