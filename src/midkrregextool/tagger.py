# tagger.py

from __future__ import annotations
from .model import Token
from pathlib import Path
from collections import Counter
import unicodedata, re
import json, random

def load_infl_suffixes() -> list[str]:
    path = Path(__file__).with_name("infl_suffixes.txt")
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

def load_lemma_whitelist() -> set[str]:
    path = Path(__file__).with_name("lemma_whitelist.txt")
    lemmas: set[str] = set()

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            lemmas.add(line)

    return lemmas

def contains_han(s: str) -> bool:
    for ch in s:
        if "CJK UNIFIED IDEOGRAPH" in unicodedata.name(ch, ""):
            return True
    return False

def analyze_yale(
        yale: str, 
        infl_suffixes: list[str],
        lemmas: list[str]) -> str:
    
    if not yale:
        return ""   # guard against missing yale
    
    # Check if yale starts with an item in the whitelist.

    for lem in lemmas:
        if yale.startswith(lem):
            suffix = yale[len(lem):]
            if not suffix:
                return f"{lem}/LEM"
            else:
                return f"{lem}/LEM-{suffix}/INFL"

    # If not, 

    has_han = contains_han(yale)

    # 1. check if yale contains Chinese character
    if has_han:

        # compiling regex pattern for Chinse characters
        m1 = re.match(r"^([\u4E00-\u9FFF]+ho)(.+)$",yale)    # verb with a Sino-Korean root
        m2 = re.match(r"^([\u4E00-\u9FFF]+)([^\u4E00-\u9FFF]+)$",yale)  # yale containing a non-Chinese character

        # 1-1. If yale contains a verbalizer, CH+ho/LEM.../INFL
        if m1:
            lem = m1.group(1)
            suf = m1.group(2)
            return f"{lem}/LEM-{suf}/INFL"

        # 1-2. If yale contains any non-Chinese characters, parse a boundary between CH/LEM-...
        elif m2:
            lem = m2.group(1)
            suf = m2.group(2)
            return f"{lem}/LEM-{suf}/INFL"

        # 1-3. else, yale is lemma.
        else:
            return f"{yale}/LEM"

    
    for suf in infl_suffixes:
    # 2. Check if yale ends with an item in the inflection list

        # Inspect longer suffixes first

        if yale.endswith(suf):
            lem = yale[:-len(suf)]
            if not lem:
                return f"{yale}/LEM"
            if not re.search(r"[aeiou]", lem):
                continue
            else:
                return f"{lem}/LEM-{suf}/INFL"
        else:
            continue
        
    # 3. the whole yale is lemma.

    return f"{yale}/LEM"


def split_lem_infl(yale: str, infl_suffixes: list[str]) -> tuple[str, str] | None:
    """
    Return (lem, infl) if a suffix matches; otherwise return None.
    """

    if not yale:
        return None # guard against missing yale
    for suf in infl_suffixes:
        if yale.endswith(suf) and len(yale) > len(suf):
            # If lem does not contain any vowels, it is not lem.
            if not re.search(r"[aeiou]", yale[:-len(suf)]):
                continue
            else:
                lem = yale[:-len(suf)]
                return (lem, suf)
    return None

def dump_known_lemmas(
        tokens: list[Token],
        infl_suffixes: list[str],
        lemmas: set[str],
        *,
        min_count: int = 5,
        top_k: int | None = None
) -> list[tuple[str, int]]:
    c = Counter()
    for t in tokens:
        yale = t.yale

        if not yale: # guard clause
            continue

        if any(yale.startswith(L) for L in lemmas):
            continue

        else:
            
            r = split_lem_infl(yale, infl_suffixes)
            
            # If any inflectional suffix is not detected, suggest yale as a potential lemma.
            if r is None:
                if not contains_han(yale):
                    c[yale] += 1

            else:
            
                # Assign the part prior to the suffix as potential lemma
                lem, _ = r

                # if any(lem.startswith(L) for L in lemmas):
                #     continue

                # Check if lem has Chinese character
                has_han = contains_han(lem)

                # If lem has any Chinese character, no need to suggest.
                if has_han:
                    continue

                else:

                    # Filter if the candidate does not have any vowel
                    if re.search(r"[aeiou]", lem) is None:
                        continue
                    else:

                        # If the lemma starts with a consonantal cluster, lemma must be longer than two characters. 
                        if lem.startswith("."):
                            if len(lem) > 2:
                                c[lem] += 1

                        elif len(lem) > 1:
                            c[lem] += 1

        
    
    items = [(lem, cnt) for lem, cnt in c.items() if cnt >= min_count]
    items.sort(key=lambda x: (-x[1], x[0]))
    if top_k is not None:
        items = items[:top_k]
    return items

def display_lemma_candidates(
        counter: Counter
) -> None:
    lemmas = [(lem, cnt) for lem, cnt in counter.items()]
    lemmas.sort(key=lambda x: (-x[1],x[0]))
    print("[DEBUG] Comprehensive list of the potential lemma list (candidate, count):")
    for (lem, cnt) in lemmas:
        print(f"\t{lem}\t{cnt}")
    
    save_lemma_candidates(lemmas)

def save_lemma_candidates(
        items: list[tuple[str,int]],
        *,
        header: str | None = None,
) -> None:
    if ask_yes_no("Save lemma candidates?"):
        out_path = Path(__file__).parent / "lemma_candidates.txt"
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            for (lem, cnt) in items:
                f.write(f"{lem}\n")

        print(f"[DEBUG] Saved lemma candidates to {out_path}")

def ask_yes_no(msg: str) -> bool:
    while True:
        ans = input(f"{msg} (y/n) ").strip().lower()                
        # Clean up user input:
        #   - remove extra spaces
        #   - ignore upper/lower case differences

        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        
        print("Please type 'y' or 'n'.")


def propose_infl_suffixes(
        tokens: list[Token],
        infl_suffixes: list[str],
        *,
        max_len: int = 10,
        min_count: int = 20,
        top_k: int = 50,
) -> list[tuple[str, int]]:
    """
    Look at tokens where split_lem_infl() fails, and propose frequent suffix strings (up to max_len) from the end of yale.    
    """
    c = Counter()

    # Counting suffix candidates

    for t in tokens:
        yale = t.yale
        if not yale:
            continue

        # If the given suffix is already in the suffix list, skip.
        if split_lem_infl(yale, infl_suffixes) is not None:
            continue

        # collect suffix candidates of length 1..max_len from the end of the given yale string.
        for L in range(1, min(max_len, len(yale))+1):
            cand = yale[-L:]
            c[cand] += 1

    # Keep only frequent suffix candidates above the minimum count threshold (min_k)
    # sort by suffix length (desc), frequency (desc), then alphabetically
    items = [(suf, cnt) for suf, cnt in c.items() if cnt >= min_count]
    items.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))

    return items[:top_k]

def update_suffix_counter(
        counter: Counter,
        tokens: list[Token],
        infl_suffixes: list[str],
        *,
        max_len: int = 6,
        suffix_must_endwith: str | None = None
) -> None:
    for t in tokens:
        yale = t.yale
        if not yale:
            continue
        if split_lem_infl(yale, infl_suffixes) is not None:
            continue

        for L in range(1, min(len(yale), max_len) + 1):
            if L < len(yale):
                if suffix_must_endwith is not None:
                    if len(suffix_must_endwith) >= len(yale):
                        continue

                    if yale.endswith(suffix_must_endwith) == False:
                        continue
                    counter[yale[-L:]] += 1
                else:
                    counter[yale[-L:]] += 1

def finalize_suffix_proposals(
        counter: Counter,
        infl_suffixes: list[str],
        *,
        min_count: int = 20,
        top_k: int = 50,
        min_len: int = 3
) -> list[tuple[str, int]]:
    
    items: list[tuple[str, int]] = []

    for cand, cnt in counter.items():
        if cnt < min_count:
            continue

        if len(cand) < min_len:
            continue

        if not cand.isascii():
            continue

        if any(known.endswith(cand) for known in infl_suffixes):
            continue

        items.append((cand, cnt))
     
    items.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))
    return items[:top_k]

def display_suffix_candidates(proposed_suffixes: list[tuple[str,int]]) -> None:
    print("[DEBUG] Comprehensive list of the proposed INFL suffixes including (candidate, count):")
    for (suf, cnt) in proposed_suffixes:
        print(f"\t{suf}\t{cnt}")

def tag_tokens(tokens: list[Token], infl_suffixes: list[str], lemma_list: list[str], *, debug_suffixes: bool = False) -> list[Token]:
    """Enrich tokens with morphological tagging for downstream processing."""

    if debug_suffixes:
        proposals = propose_infl_suffixes(tokens, infl_suffixes)
        print("[DEBUG] Proposed INFL suffixes (candidate, count):")
        for suf, cnt in proposals:
            print(f"    {suf}\t{cnt}")

    for token in tokens:
        token.tagged_form = analyze_yale(token.yale, infl_suffixes, lemma_list)
    return tokens

def candidate_generator(token: Token, rules: list[str]) -> list[str]:
    yale = (token.yale or "").strip()
    if not yale:
        return []
    
    infl_suffixes = sorted(rules, key=len, reverse=True)

    candidates: list[str] = []

    for suf in infl_suffixes:
        if yale.endswith(suf):
            stem = yale[:-len(suf)]
            stem = stem.rstrip("-")

            if not stem:
                continue

            candidates.append(f"{stem}/LEM-{suf}/INFL")

    return candidates

def format_candidate(token: Token, candidates: list[str]) -> None:
    print(f"[Training] {token.source_id} [{token.path}]\n\t[Token]\t\t{token.unicode_form}\n\t[CONTEXT]\t{token.context}")
    # Display candidates
    for i, cand in enumerate(candidates, start=1):
        if i == 1:
            print(f"\t[CANDIDATES]\t{i}. {cand}")
        else:
            print(f"\t\t\t{i}. {cand}")

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
            if token and gold:
                token_gold[token] = gold

    return token_gold

def extract_infl_from_gold(gold: str) -> str | None:
    if "/LEM-" not in gold or "/INFL" not in gold:
        return None
    return gold.split("/LEM-", 1)[1].split("/INFL", 1)[0]

def load_learned_infl_suffixes(training_path: Path) -> None:
    infls = set()

    with open(training_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)
            gold = obj.get("gold")

            if not isinstance(gold, str) or gold == "None":
                continue

            infl = extract_infl_from_gold(gold)
            if infl:
                infls.add(infl)

    result = sorted(infls, key=len, reverse=True)
    return result

# debug_collect_infls(Path("data/training/training_15c.jsonl"))

def train(tokens: list[Token], rules: list[str], period: int, training_data: Path | None) -> None:

    period_tag = f"{period}c"

    print(f"[INFO] Training mode is ON.")

    if not period:
        raise ValueError("Period must be specified in training mode.")


    # Locate or create training data file

    out_dir = training_data if training_data is not None else default_training_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"training_{period_tag}.jsonl"

    # Load token gold list
    token_gold = load_token_gold(out_path)

    with open(out_path, "a", encoding="utf-8") as f:

        quit_training = False

        random.shuffle(tokens)

        for token in tokens:

            if token.unicode_form in token_gold:
                continue

            candidates = candidate_generator(token, rules)

            if not candidates:
                continue

            if token.unicode_form in token_gold:
                gold = token_gold[token.unicode_form]
                if gold in candidates:
                    candidates = [gold] + [c for c in candidates if c != gold]


            format_candidate(token, candidates)

            while True:

                raw_ans = input(
                    f"[Training] What is the optimal candidate for {token.unicode_form}?\n"
                    f"(1-{len(candidates)} to select / s=skip / m=manual input / q=quit) > "
                ).strip()
                ans = raw_ans.lower()

                if ans == "q":
                    quit_training = True
                    return

                if ans == "s":
                    break

                gold = None

                if ans == "m":
                    gold = input("Please type your desired tagged form: ").strip()
                    if not gold:
                        print("[Training] Empty manual input. Skipping.")
                        continue

                elif ans.isdigit():
                    idx = int(ans) - 1
                    if 0 <= idx < len(candidates):
                        gold = candidates[idx]
                    else:
                        print("[Training] Out of range. Skipping.")
                        continue

                elif ("/lem" in ans) or ("/infl" in ans):
                    gold = raw_ans

                else:
                    print("[ERROR] Invalid input.")
                    continue


                f.write(
                    f'{{"period":"{period_tag}","token":"{token.unicode_form}","gold":"{gold}"}}\n'
                )
                f.flush()

                token_gold[token.unicode_form] = gold
                
                break
            
            if quit_training:
                break

    print(f"[INFO] Training data saved to {out_path}")

