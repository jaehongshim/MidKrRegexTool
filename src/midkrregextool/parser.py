# parser.py
import re
from pathlib import Path
from typing import List

from .model import Token

# Source marker at the *beginning* of a line, e.g.: 
# <釋詳3:1a> [head] ...
# We capture the content inside angle brackets and allow optional whitespace after it:
SOURCE_TAG_RE = re.compile(r"<([^>]+)>\s*") # e.g. <釋詳3:1a>

# We treat [note] ... [/note] specially because we want to keep track of is_note.
NOTE_TAG_SPLIT_RE = re.compile(r"(\[note\]|\[/note\])")

# [head] / [add] markers: we keep their contents but remove the tags themselves.
HEAD_OPEN_RE = re.compile(r"\[head\]")
HEAD_CLOSE_RE = re.compile(r"\[/head\]")

ADD_OPEN_RE = re.compile(r"\[add\]")
ADD_CLOSE_RE = re.compile(r"\[/add\]")

def parse_file(path: str | Path) -> List[Token]:
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
    with open(path, encoding="utf-8") as f:
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
                current_source_id = m.group(1) # the strings wrapped with ()

                # Reset token numbering within this source section.
                token_index = 0

                # Remove the source tag prefix from the line and continue
                # processing the remainder as normal text.
                line = line[m.end():].lstrip() 

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
            '''
            e.g., 
            parts = [
                "무상천으로 가리니 ", 
                "[note]",
                " 그저긔 阿私陁이 ",
                "[/note]",
                " 몯 미처"
                ]
            '''
            

            for part in parts:
                if not part: 
                    continue # Skip the remaining processes and go on to the next cycle.

                if part == "[note]":
                    # Enter note mode: subsequent tokens will have is_note=True.
                    inside_note = True
                    continue

                if part == "[/note]":
                    # Exit note mode: subsequent tokens will have is_note=False.
                    inside_note = False
                    continue

                # This is a normal text segment (either inside or outside a note).
                # We split it into words on whitespace.
                words = part.split() # e.g., words = ["무상천으로", "가리니"]
                if not words: 
                    continue

                for w in words: # e.g., as for "무상천으로" in ["무상천으로", "가리니"]
                    token_index += 1
                    tokens.append(
                        Token(
                            source_id=current_source_id,
                            token_index=token_index,
                            pua=w,
                            is_note=inside_note,
                        )
                    )

    return tokens