from collections import Counter
from .model import Token
from .tagger import split_lem_infl, contains_han
import re
from .training import extract_infl_from_gold

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

def candidate_generator(
        token: Token, 
        rules: list[str],
        *,
        infl_decomp: dict[str, str] | None = None
        ) -> list[str]:
    
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
    
    # If we have learned infl decompositions, prepend morph-level candidates
    if infl_decomp is not None:
        morph_candidates: list[str] = []
        for cand in candidates:                     # cand: stem/LEM-suf/INFL
            infl = extract_infl_from_gold(cand)
            if infl in infl_decomp:
                segmented = infl_decomp[infl]       # e.g., si/HON-li/FUT-...
                stem = cand.split("/LEM-", 1)[0]    # e.g., ka
                morph_candidates.append(f"{stem}/LEM-{segmented}")
        candidates = list(dict.fromkeys(morph_candidates + candidates))

    return candidates
