import pytest

from midkrregextool.tagger import parse_tagged_form

CASES = [
    # Case 1: default
    (
        "nilu/V/LEM-si/SUBJ/HON-ni/CONN",
        [("nilu", "V"), ("si", "SUBJ/HON"), ("ni", "CONN")],
    ),
    #  Case 2: no inflection
    (
        "tangta.ngi/ADV/LEM",
        [("tangta.ngi", "ADV")],
    ),
    #  Case 3: unanalyzable inflection
    (
        "ho/V/LEM-kesini/INFL",
        [("ho", "V"), ("kesini", "INFL")],
    ),
    # Case 4: token with no tagged_form
    (
        "mwusangchen/NO-TAGGED-FORM",
        [("mwusangchen", "UNK")],
    ),
    # Case 5: token with a prefix
    (
        "mwot/NEG/PREFIX-ho/V/LEM-ya/CONN",
        [("mwot", "NEG"), ("ho", "V"), ("ya", "CONN")],
    ),
    # Case 6: token with AUX
    (
        "ho/V/AUX/LEM-ni/CONN",
        [("ho", "V/AUX"), ("ni", "CONN")],
    ),
    # Case 7: token without tagged_form whose part is a part of "NO-TAGGED_FORM" flag.
    (
        "nom/NO-TAGGED-FORM",
        [("nom", "UNK")],
    ),
    # Guard
    (None, None),
    ("", None),
]


@pytest.mark.parametrize("given, expected", CASES)
def test_parse_tagged_form(given, expected):
    assert parse_tagged_form(given) == expected
