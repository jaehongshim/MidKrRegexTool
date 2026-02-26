# tagger.py

from __future__ import annotations
from .model import Token
from pathlib import Path
import unicodedata, re, json

def _resolve_training_data(training_data: Path, period: int | str | None = None) -> Path:
    period_tag = _period_tag(period)
    training_dir = training_data if training_data is not None else default_training_dir()
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

def load_lemma_lexicon(period: int | str | None = None, *, training_data: Path) -> dict[str, str]:

    def _assign_pos(form_pos: str) -> list[str, str]:
        """
        Expected input: kwoksik/N or mwot/NEG/PREFIX-ho/V, returns form and pos
        Fallback: kwoksik or mwot/NEG/PREFIX-ho, returns form and "UNK"
        """    
        if "/PREFIX-" in form_pos:
            if "/" in form_pos.split("/PREFIX-")[0]:
                prefix = form_pos.split("/PREFIX")[0].split("/")[0]
                lem = form_pos.split("/PREFIX-")[1].split("/")[0]
                lem = prefix + lem
                pos = form_pos

        elif "/" in form_pos:
            lem = form_pos.split("/")[0]
            pos = form_pos
        
        else: 
            lem = form_pos
            pos = form_pos + "/UNK"

        return [lem, pos]
    
    def _add_from_gold_morph(m: str) -> None:
        """
        Expected input: (LEMMA)/(POS)/LEM or (LEMMA)/(POS)/LEM-(SUFFIXES)
        Fallback: (Lemma)/LEM or (LEMMA)/LEM-(SUFFIXES)
        """
        if m is None:
            return
        
        m1 = m.split("/LEM")[0] # The part before "/LEM", e.g., kwoksik/N <-

        [lem, pos] = _assign_pos(m1)
        
        if lem in lex.keys():
            return
        lex[lem] = pos

    def _add_from_gold(g: str) -> None:
        """
        Expected input: (LEMMA)/(POS)/LEM or (LEMMA)/(POS)/LEM-(SUFFIXES)/INFL
        Fallback: (Lemma)/LEM or (LEMMA)/LEM-(SUFFIXES)/INFL
        """
        if g is None:
            return

        g1 = g.split("/LEM")[0]

        [lem, pos] = _assign_pos(g1)

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
            if line.startswith("#"): # Setting POS tag if line starts with #
                header = line.lstrip("#").strip()
                current_pos = header.split()[0].upper() if header else None
                continue
            if current_pos is None:
                raise ValueError(
                    f"Lemma '{line} appears before any POS header in {path}'"
                )
            pos = line + "/" + current_pos
            lex[line] = pos

    if training_data is not None:

        training_file = _resolve_training_data(training_data, period)

        try: 
            f = open(training_file, encoding="utf-8")
            for raw in f:

                obj = json.loads(raw)

                if not obj:
                    continue

                for k in ("gold_morph", "gold_morph_a", "gold_morph_b"):
                    m = obj.get(k)
                    if m:
                        _add_from_gold_morph(m)

                for k in ("gold", "gold_a", "gold_b"):
                    g = obj.get(k)
                    if g:
                        _add_from_gold(g)
        except:
            return

    return lex

def load_lemma_whitelist(period: int | str | None = None) -> set[str]:
    return set(load_lemma_lexicon(period).keys())

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
        return ""   # guard against missing yale
    
    if not rest_set:
        rest_set = set()

    if not lexicon:
        lexicon = dict()

    lemma_list = sorted(lexicon.keys(), key=len, reverse=True)
    
    # Check if yale starts with an item in the whitelist.

    for lem in lemma_list:
        if yale.startswith(lem):
            lem_pos = lexicon[lem]
            suffix = yale[len(lem):]
            if not suffix:
                return f"{lem_pos}/LEM"
                
            else:
                if suffix in rest_set:
                    return f"{lem_pos}/LEM-{suffix}/INFL"
                continue

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
            return f"{lem}/CH/LEM-{suf}/INFL"

        # 1-2. If yale contains any non-Chinese characters, parse a boundary between CH/LEM-...
        elif m2:
            lem = m2.group(1)
            suf = m2.group(2)
            return f"{lem}/CH/LEM-{suf}/INFL"

        # 1-3. else, yale is lemma.
        else:
            return f"{yale}/CH/LEM"

    
    for suf in infl_suffixes:
    # 2. Check if yale ends with an item in the inflection list

        # Inspect longer suffixes first

        if yale.endswith(suf):
            stem = yale[:-len(suf)]
            if not stem:
                return f"{yale}/LEM"
            if stem not in lexicon:
                continue
            else:
                pos = lexicon[stem]
                return f"{stem}/{pos}/LEM-{suf}/INFL"
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

def tag_tokens(
        tokens: list[Token], 
        rules: list[str], 
        *, 
        lexicon: dict[str, str], 
        rest_set: set[str],
        infl_decomp: dict[str,str] | None = None,
        debug_suffixes: bool = False
        ) -> list[Token]:
    """Enrich tokens with morphological tagging for downstream processing."""

    for token in tokens:
        token.coarse_form = analyze_yale(token.yale, rules, lexicon, rest_set)

        if "/INFL" not in token.coarse_form:
            continue

        if infl_decomp is not None:
            infl = infl_from_tagged_form(token.coarse_form)
            segmented = infl_decomp.get(infl)
            if segmented is None:
                continue
            token.tagged_form = token.coarse_form.split("/LEM", 1)[0] + "/LEM-" + segmented
            token.morphs = parse_segmented(segmented)

    return tokens

def infl_from_tagged_form(coarse_form: str) -> str:
    if not coarse_form:
        return None
    if "/LEM-" not in coarse_form or "/INFL" not in coarse_form:
        return None 
    return coarse_form.split("/LEM-",1)[1].split("/INFL",1)[0]

def parse_segmented(segmented: str) -> list[tuple[str,str]]:
    return [tuple(seg.rsplit("/",1)) for seg in segmented.split("-")]



