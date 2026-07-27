# parser.py
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .model import Token

# Source marker at the *beginning* of a line, e.g.:
# <釋詳3:1a> [head] ...
# We capture the content inside angle brackets and allow optional whitespace after it:
SOURCE_TAG_RE = re.compile(r"<([^>]+)>\s*")  # e.g. <釋詳3:1a>

# We treat [note] ... [/note] specially because we want to keep track of is_note.
NOTE_TAGS = {"[note]", "[/note]"}
NOTE_TAG_SPLIT_RE = re.compile(r"(\[note\]|\[/note\]|【|】)")

# [head] / [add] markers: we keep their contents but remove the tags themselves.
HEAD_OPEN_RE = re.compile(r"\[head\]")
HEAD_CLOSE_RE = re.compile(r"\[/head\]")

ADD_OPEN_RE = re.compile(r"\[add\]")
ADD_CLOSE_RE = re.compile(r"\[/add\]")


def trimming_date(raw_year: str | int) -> int | str | None:

    if not raw_year:
        return None

    elif isinstance(raw_year, int):
        return raw_year

    elif raw_year.isdigit():
        return int(raw_year)

    m1 = re.match(r"(\d{4})[년年]", raw_year)

    if m1:
        year = int(m1.group(1))
        return year

    # year specified only for century
    m2 = re.match(r"(^\d{2})[Cc]$", raw_year)
    m3 = re.match(r"(^\d{2})세기$", raw_year)

    if "미상" in raw_year or "알 수 없음" in raw_year:
        m4 = re.match(r".+(\d{2}).+", raw_year)
        if m4:
            year = int(m4.group(1)) * 100 - 100
            year = f"{year}s"
            return year

        return "<UNK>"

    # 17c
    if m2:
        year = int(m2.group(1)) * 100 - 100
        year = f"{year}s"
        return year
    # 17세기
    elif m3:
        year = int(m3.group(1)) * 100 - 100
        year = f"{year}s"
        return year

    else:
        return None


def convert_to_century(year: str | int | None) -> int | None:

    if not year:
        return None

    elif isinstance(year, str):

        year = (year or "").strip()

        m = re.search(r"\d+", year)
        if m is None:
            return None

        y = int(m.group())

    else:
        y = year

    if y <= 20:
        return y

    return (y - 1) // 100 + 1


@dataclass
class LetterInfo:
    element: ET.Element
    letter_n: str
    sender: str
    receiver: str
    raw_year: str
    published_year: int | str
    published_century: int | None


def letter_sort_key(info: LetterInfo) -> tuple:
    """Sort key ordering int values before str values (numeric, then lexical)."""
    century = info.published_century
    year = info.published_year
    return (
        (0, century) if isinstance(century, int) else (1, str(century)),
        (0, year) if isinstance(year, int) else (1, str(year)),
    )


def has_letters(root: ET.Element) -> bool:
    return root.find(".//letter") is not None


def _get_element_text(element: ET.Element, tags: str | tuple[str, ...]) -> str:
    if isinstance(tags, str):
        tags = (tags,)
    for tag in tags:
        found = element.find(tag)
        if found is not None:
            text = (found.text or "").strip()
            if text:
                return text
    return ""


def _find_parent(root: ET.Element, target: ET.Element) -> ET.Element | None:
    for parent in root.iter():
        for child in parent:
            if child is target:
                return parent
    return None


def _get_corresponding_sibling_text(
    parent: ET.Element,
    letter_index: int,
    tag_names: tuple[str, ...],
) -> str:
    """
    Find metadata text among `parent`'s children that corresponds to the
    <letter> at `letter_index`, without crossing into a neighboring letter's
    metadata segment. Prefers the nearest preceding sibling, then the
    nearest following one, both bounded by adjacent <letter> siblings.
    """
    children = list(parent)

    start = 0
    for i in range(letter_index - 1, -1, -1):
        if children[i].tag == "letter":
            start = i + 1
            break

    end = len(children)
    for i in range(letter_index + 1, len(children)):
        if children[i].tag == "letter":
            end = i
            break

    for i in range(letter_index - 1, start - 1, -1):
        if children[i].tag in tag_names:
            return (children[i].text or "").strip()

    for i in range(letter_index + 1, end):
        if children[i].tag in tag_names:
            return (children[i].text or "").strip()

    return ""


def get_info_from_letters(root: ET.Element) -> list[LetterInfo]:
    """
    Normalize sender/receiver/year metadata for every <letter> in `root`,
    regardless of whether that metadata lives in <letter> attributes, in
    child elements of <letter>, or in sibling elements next to <letter>.
    """
    infos: list[LetterInfo] = []

    for letter in root.findall(".//letter"):
        parent = _find_parent(root, letter)
        letter_index = list(parent).index(letter) if parent is not None else None

        letter_n = (letter.get("n") or "").strip()

        # sender: letter@sender > letter@writer > inner <writer> > sibling <writer>
        sender = (letter.get("sender") or letter.get("writer") or "").strip()
        if not sender:
            sender = _get_element_text(letter, "writer")
        if not sender and letter_index is not None:
            sender = _get_corresponding_sibling_text(parent, letter_index, ("writer",))

        # receiver: letter@receiver > inner <addressee>/<adressee> > sibling <addressee>/<adressee>
        # ("adressee", missing a "d", is a common misspelling in NIKL source XML.)
        receiver = (letter.get("receiver") or "").strip()
        if not receiver:
            receiver = _get_element_text(letter, ("addressee", "adressee"))
        if not receiver and letter_index is not None:
            receiver = _get_corresponding_sibling_text(
                parent, letter_index, ("addressee", "adressee")
            )

        # year: letter@year > inner <year> > inner <date> > sibling <year> > sibling <date>
        raw_year = (letter.get("year") or "").strip()
        if not raw_year:
            raw_year = _get_element_text(letter, "year")
        if not raw_year:
            raw_year = _get_element_text(letter, "date")
        if not raw_year and letter_index is not None:
            raw_year = _get_corresponding_sibling_text(parent, letter_index, ("year",))
        if not raw_year and letter_index is not None:
            raw_year = _get_corresponding_sibling_text(parent, letter_index, ("date",))

        published_year = trimming_date(raw_year)
        if not published_year:
            published_year = raw_year

        published_century = convert_to_century(published_year)

        infos.append(
            LetterInfo(
                element=letter,
                letter_n=letter_n,
                sender=sender,
                receiver=receiver,
                raw_year=raw_year,
                published_year=published_year,
                published_century=published_century,
            )
        )

    return infos


def parse_file(
    path: str | Path,
    *,
    encoding: str = "utf-16",
    period: int | None = None,
    # display_context: bool = False,
) -> List[Token]:
    # Guard: XML inputs are collected by the CLI, but XML parsing/extraction is not implemented yet.
    if path.suffix.lower() == ".xml":
        return parse_xml_file(path, encoding=encoding, period=period)

    # Flag for displaying context
    # want_ctx = display_context
    """
    Parse a Middle Korean text file encoded in Hanyang PUA and return a list of tokens.
    
    This parser:


    1. Detects source markers like <釋詳3:1a> and updates the current source context.
        - It updates the current `source_id` and resets the `token_index`.
    
    2. Handles [head] / [add] markers by cleaning them from the line (text inside them is treated the same as normal text).

    3. Handles [note] ... [/note] markers by:
        - Toggling an `inside_note` flag when [note] / [/note] are encountered.
        - Splitting the line into segments separated by note tags.
        - Tokenizing each text segment, assigning `is_note=True` to tokens that occur while `inside_note` is True, and `False` otherwise.

    4. Creates Token objects with source_id, token_index, and PUA lexical form. 
    """

    tokens: List[Token] = []

    # Tracks which source block the parser is currently in (e.g., "釋詳3:1a")
    current_source_id: str | None = None
    token_index: int = 0

    # Tracks whether we are currently inside a [note]...[/note] block.
    inside_note = False

    # Open the file for reading.

    f = open(path, encoding=encoding)

    # Try UTF-16 first, then fall back to UTF-8

    # try:
    #     f = open(path, encoding="utf-16")
    # except UnicodeError:
    #     f = open(path, encoding="utf-8")

    with f:
        for raw_line in f:
            # Remove surrounding whitespace, but keep internal spacing.
            line = raw_line.strip()

            # Skip empty lines; they do not contribute tokens.
            if not line:
                continue

            # --------------------------------------------------------------
            # 1. Detect source markers such as <釋詳3:1a>
            # --------------------------------------------------------------
            m = SOURCE_TAG_RE.match(line)
            if m:
                # Update the current source context
                current_source_id = m.group(1)  # the strings wrapped with ()

                # Remove the source tag prefix from the line and continue
                # processing the remainder as normal text.
                line = line[m.end() :].lstrip()

                # If nothing remains on this line, move on to the next line.
                if not line:
                    continue

            # If we still don't have a source_id (no source tag seen yet),
            # we might choose to skip tokens or raise an error.
            # For now, we skip lines without an established source.
            if current_source_id is None:
                continue

            # ----------------------------------------------------------
            # 2. Remove [head] / [/head] and [add] / [/add] tags.
            #    Their contents are treated as normal text.
            # ----------------------------------------------------------
            line = HEAD_OPEN_RE.sub("", line)
            line = HEAD_CLOSE_RE.sub("", line)
            line = ADD_OPEN_RE.sub("", line)
            line = ADD_CLOSE_RE.sub("", line)

            # ----------------------------------------------------------
            # 3. Process [note] and [/note] markers with segment-level control
            #
            # We split the line into a sequence of:
            #   - text segments
            #   - "[note]" markers
            #   - "[/note]" markers
            #
            # Example:
            #   "foo [note] bar baz [/note] qux"
            # becomes:
            #   ["foo ", "[note]", " bar baz ", "[/note]", " qux"]
            #
            # We then iterate through this list and:
            #   - toggle inside_note when we see [note]/[/note]
            #   - tokenize text segments according to the current inside_note
            # ----------------------------------------------------------

            parts = NOTE_TAG_SPLIT_RE.split(line)
            """
            e.g., 
            parts = [
                "무상천으로 가리니 ", 
                "[note]",
                " 그저긔 阿私陁이 ",
                "[/note]",
                " 몯 미처"
                ]
            """

            context = " ".join(p for p in parts if p and p not in NOTE_TAGS)

            inside_note = "MAIN"  # The beginning is always the main body text, so set the flag as "MAIN"

            for part in parts:

                # Reset token numbering within this part section.

                if not part:
                    continue  # Skip the remaining processes and go on to the next cycle.

                token_index = 0

                if part == "[note]":
                    # Enter note mode: subsequent tokens will have is_note=True.
                    inside_note = "NOTE"
                    continue

                if part == "[/note]":
                    # Exit note mode: subsequent tokens will have is_note=False.
                    inside_note = "MAIN"
                    continue

                # This is a normal text segment (either inside or outside a note).
                # We split it into words on whitespace.

                words = part.split()  # e.g., words = ["무상천으로", "가리니"]
                if not words:
                    continue

                for w in words:  # e.g., as for "무상천으로" in ["무상천으로", "가리니"]
                    token_index += 1
                    tokens.append(
                        Token(
                            path=path,
                            source_id=current_source_id,
                            token_index=token_index,
                            pua=w,
                            is_note=inside_note,
                            context=context,
                        )
                    )

    return tokens


def parse_xml_file(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    # display_context: bool = False,
    classical_ch: bool = False,
    period: int | None = None,
) -> List[Token]:
    """
    Parse NIKL-style XML file where sentences are stored as <sent ...>TEXT</sent>.

    We create a fresh source_id per <sent>, so token_index resets for each sentence.

    Letter XML (files containing <letter>) treat each <letter> as its own
    document instead of the whole file; see `_parse_letter_xml()`.
    """
    path = Path(path)
    root = ET.parse(path).getroot()

    if has_letters(root):
        return _parse_letter_xml(root, path, period)

    tokens: list[Token] = []

    # Iterate over all <sent> elements anywhere in the document.

    doc_name = (root.findtext(".//title") or "").strip()

    published_year = (
        root.findtext(".//teiHeader//titleStmt//date") or root.findtext(".//date")
    ).strip()
    published_year = (published_year or "").strip()

    # Extract volume information if available.
    volume_el = root.find(".//teiHeader//titleStmt//volume")
    volume = volume_el.get("n") if volume_el is not None else None
    if published_year:
        if volume:
            doc_name = f"{published_year}_{doc_name}{volume}"
        else:
            doc_name = f"{published_year}_{doc_name}"

    if not published_year:
        if volume:
            doc_name = f"unknown_{doc_name}{volume}"
        else:
            doc_name = f"unknown_{doc_name}"

    for sent in root.iterfind(".//sent"):
        text = (sent.text or "").strip()
        if not text:
            continue

        context = text

        # Build a stable source_id from attributes if available.
        page = sent.get("page")
        n = sent.get("n")
        lang = sent.get("lang")
        sent_type = sent.get("type")

        source_id = f"{doc_name}:{page}:{n}:{lang}"

        token_index = 0

        if sent_type == "dharani":
            continue

        for word in text.split():
            token_index += 1

            contextwords = context.split()
            contextwords[token_index - 1] = f"<<{contextwords[token_index-1]}>>"
            current_context = " ".join(contextwords)

            tokens.append(
                Token(
                    path=path,
                    source_id=source_id,
                    token_index=token_index,
                    pua=word,
                    is_note=sent_type,
                    context=current_context,
                    lang=lang,
                    sent_type=sent_type,
                )
            )

    return tokens


def _parse_letter_xml(
    root: ET.Element,
    path: Path,
    period: int | None,
) -> List[Token]:
    """
    Letter XML: each <letter> is its own document. When `period` is given,
    only letters whose published_century matches it are converted to Token;
    <sent> elements belonging to other letters are left untouched.
    """
    tokens: list[Token] = []

    letters = get_info_from_letters(root)

    if period is not None:
        letters = [info for info in letters if info.published_century == period]

    letters = sorted(letters, key=letter_sort_key)

    # Fallback file-level title, used since <letter> rarely carries its own.
    doc_title = (root.findtext(".//title") or "").strip()

    for letter_index, info in enumerate(letters):
        year_part = info.raw_year or "unknown"
        doc_name = f"{year_part}_{doc_title}_{info.sender}-{info.receiver}"

        for sent in info.element.iterfind(".//sent"):
            text = (sent.text or "").strip()
            if not text:
                continue

            context = text

            page = sent.get("page")
            n = sent.get("n")
            lang = sent.get("lang")
            sent_type = sent.get("type")

            if sent_type == "dharani":
                continue

            # letter_index disambiguates letters that share identical
            # year/sender/receiver metadata within the same file.
            source_id = f"{doc_name}:{letter_index}:{page}:{n}:{lang}"

            token_index = 0
            for word in text.split():
                token_index += 1

                contextwords = context.split()
                contextwords[token_index - 1] = f"<<{contextwords[token_index-1]}>>"
                current_context = " ".join(contextwords)

                tokens.append(
                    Token(
                        path=path,
                        source_id=source_id,
                        token_index=token_index,
                        pua=word,
                        is_note=sent_type,
                        context=current_context,
                        lang=lang,
                        sent_type=sent_type,
                    )
                )

    return tokens
