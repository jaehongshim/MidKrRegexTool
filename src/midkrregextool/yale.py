"""
Yale romanization helpers for MidKrRegexTool.

This module uses the external `YaleKorean` package to:
1. Convert Hanyang PUA-encoded strings to Unicode Hangul/jamo.
2. Convert Middle Korean Unicode strings to Yale Romanization.

Pipeline for each token (conceptually):
    token.pua               --(PUAtoUni)-->     token.unicode_form
    token.unicode_form      --(YaleMid)-->      token.yale
"""

from __future__ import annotations  # Prevent type errors

from typing import Iterable

from .model import Token
import unicodedata

try:
    import YaleKorean   # type: ignore[import]
except ImportError:     # pragma: no cover
    YaleKorean = None

class YaleKoreanNotInstalledError(ImportError):
    """Raised when the YaleKorean package is required but not installed."""

# Formatting how to report the result either on the command line or in a separate file.
def normalize_modern_only(s: str) -> str:
    return unicodedata.normalize("NFC", s)

def _require_yalekorean() -> None:
    """Ensure that the external YaleKorean package is available."""
    if YaleKorean is None:
        raise YaleKoreanNotInstalledError(
            "The 'YaleKorean' package is not installed.\n"
            "Install it with: \n\n"
            "   pip install YaleKorean\n"
        )
    
def pua_to_unicode(text: str) -> str:
    """
    Convert a Hanyang-PUA encoded string to Unicode Hangul/jamo.
    
    This is a thin wrapper around YaleKorean.PUAtoUni().
    """
    _require_yalekorean()
    return YaleKorean.PUAtoUni(text)

def unicode_to_yale_mid(text: str) -> str:
    """
    Convert a Unicode Middle Korean string to Yale Romanization.

    This is a thin wrapper around YaleKorean.YaleMid().
    """
    _require_yalekorean()
    return YaleKorean.YaleMid(text)

def pua_to_yale(text: str) -> tuple[str, str]:
    """
    Convenience function: PUA string -> (unicode_form, yale).

    Returns:
        (unicode_form, yale_form)
    """
    uni = pua_to_unicode(text)
    yale = unicode_to_yale_mid(uni)
    return uni, yale


def convert_token(token: Token) -> Token:
    """
    Fill `unicode_form` and `yale` fields of a single Token in-place.

    - token.pua must contain the original Hanyang PUA string.
    - After this function:
        token.unicode_form: Unicode Middle Korean form
        token.yale: Yale Romanization of the Unicode form
    """
    unicode_form, yale_form = pua_to_yale(token.pua)
    token.unicode_form = normalize_modern_only(unicode_form)
    token.yale = yale_form
    if token.context is not None:
        token.context = normalize_modern_only(pua_to_unicode(token.context))
    return token

def attach_yale(tokens: Iterable[Token]) -> list[Token]:
    """
    Convert all tokens from PUA to Unicode + Yale, returning a new list.

    This mutates the Token objects in-place, but also returns them as a convenience.

    Example usage:

        from midkrregextool.parser import parse_file
        from midkrregextool.yale import attach_yale

        tokens = parse_file("path/to/file.txt")
        tokens = attach_yale(tokens)

        for t in tokens[:10]:
            print(t.pua, "→", t.unicode_form, "→", t.yale)
    """
    result: list[Token] = []
    for token in tokens:
        result.append(convert_token(token))
    return result