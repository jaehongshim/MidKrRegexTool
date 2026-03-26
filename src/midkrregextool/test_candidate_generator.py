# test_candidate_generator.py

from pathlib import Path

from midkrregextool.model import Token
from midkrregextool.tagger import load_infl_suffixes, load_lemma_lexicon
from midkrregextool.training import candidate_generator, load_infl_decomp_from_training


def make_token(yale: str, prev_tagged: str | None = None):
    t = Token(
        path="",
        source_id="test",
        token_index=1,
        pua="",
        lang="kor",
        yale=yale,
        tagged_form=None,
    )

    if prev_tagged is not None:
        prev = Token(
            path="",
            source_id="test",
            token_index=0,
            pua="",
            lang="kor",
            yale="",
            tagged_form=prev_tagged,
        )
        token_lookup = {("test", 0): prev}
    else:
        token_lookup = {}

    return t, token_lookup


TEST_CASES = [
    {
        "name": "basic learned suffix",
        "yale": "hosinila",
        "prev": None,
    },
    {
        "name": "suffix-first case",
        "yale": "nwolwomila",
        "prev": None,
    },
    {
        "name": "aux context",
        "yale": "polikwo",
        "prev": "ho/V/LEM-ya/CONN",
    },
    {
        "name": "lemma-only",
        "yale": "twuluhhye",
        "prev": None,
    },
    {
        "name": "sino-korean noun",
        "yale": "種子",
        "prev": None,
    },
    {
        "name": "sino-korean + suffix",
        "yale": "種子lol",
        "prev": None,
    },
]


def run_tests():
    period = 15
    repo_root = Path(__file__).resolve().parents[2]
    training_data = repo_root / "data" / "training"

    rules = load_infl_suffixes(period=period)
    lexicon = load_lemma_lexicon(period, training_data=training_data)
    infl_decomp = load_infl_decomp_from_training(
        training_data / f"training_{period}c.jsonl"
    )

    for case in TEST_CASES:
        token, token_lookup = make_token(case["yale"], case["prev"])

        out = candidate_generator(
            token,
            rules,
            period=period,
            token_lookup=token_lookup,
            infl_decomp=infl_decomp,
            lexicon=lexicon,
        )

        print(f"\n[CASE] {case['name']}")
        print(f"yale = {case['yale']}")
        print(f"prev = {case['prev']}")
        print("OUTPUT = [")
        for cand in out:
            print(f'    "{cand}",')
        print("]")


if __name__ == "__main__":
    run_tests()
