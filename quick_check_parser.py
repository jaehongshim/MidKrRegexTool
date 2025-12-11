# quick_check_parser.py

"""

Small helper script to manually inspect the output of the parser.

Usage:
    python quick_check_parser.py
    python quick_check_parser.py tests/fixtures/sample_sekpo_excerpt.txt
    python quick_check_parser.py tests/fixtures/sample_sekpo_excerpt.txt 50
"""

import sys
from pathlib import Path

# Make sure Python can find "midkrregextool" package under src/ so that import command works for it.
Root = Path(__file__).resolve().parent                      # Project root path
SRC_DIR = Root / "src"                                      # Folder path
if str(SRC_DIR) not in sys.path:                            # Append SRC_DIR to sys.path so that Python finds "midkrregextool" package.
    sys.path.append(str(SRC_DIR))

from midkrregextool.parser import parse_file    
from midkrregextool.model import Token
from midkrregextool.yale import pua_to_yale, convert_token, attach_yale

def format_token(token: Token) -> str:                      # Print a token in a line, e.g. 釋詳3:1a # 1 MAIN 淨飯王이
    """Return a one-line string representation of a token for quick inspection."""
    note_flag = "NOTE" if token.is_note else "MAIN"
    return f"{token.source_id:>10} | {token.token_index:>3} | {note_flag:4} | {token.pua} | {token.unicode_form} | {token.yale}"

def main(argv: list[str] | None = None) -> None:
    # "argv: list[str] | None" -> The type of the argument vector is either a list of strings or None. 
    # "= None" -> If there is no argument, None is assigned as a default value.
    # "-> None" -> This function does not return a value.
    if argv is None:                    # If no argument vector is transmitted to main()
        argv = sys.argv[1:]             # Use the arguments given in the command line except for the executed file name.

    # Default: use the sample excerpt and show first 30 tokens.
    default_path = Root / "tests" / "fixtures" / "sample_sekpo_excerpt.txt"
    path = Path(argv[0]) if argv else default_path
    n_tokens = int(argv[1]) if len(argv) > 1 else 30

    if not path.exists():               # Error message for non-existing files
        print(f"[ERROR] File not found: {path}")
        return
    
    print(f"[INFO] Parsing: {path}")
    tokens = parse_file(path)

    print(f"[INFO] Total tokens: {len(tokens)}")
    print(f"[INFO] Showing first {min(n_tokens, len(tokens))} tokens:\n")

    last_source_id = None
    
    for token in tokens[:n_tokens]:
        token = convert_token(token)
        if token.source_id != last_source_id:
            print(f"\n--- SOURCE {token.source_id} ---")
            last_source_id = token.source_id
        print(format_token(token))

if __name__ == "__main__":
    main()
