# quick_check_parser.py

"""

Small helper script to manually inspect the output of the parser.

Usage:
    python quick_check_parser.py
    python quick_check_parser.py --pattern "s[iy]"
    python quick_check_parser.py --pattern "s[iy]" --n 50
    python quick_check_parser.py --path tests/fixtures/sample_sekpo_excerpt.txt --pattern "s[iy]"
    python quick_check_parser.py --path tests/fixtures/sample_sekpo_excerpt.txt --n 100

"""

import sys
import argparse                 # To avoid positional arguments
from pathlib import Path

# Ensure that Python can locate the "midkrregex" package under src/.
# This allows the script to be run directly without installing the package.
Root = Path(__file__).resolve().parent      # Directory containing this script.
SRC_DIR = Root / "src"                      # Source directory containing the package.
if str(SRC_DIR) not in sys.path:            # Append SRC_DIR to sys.path so that Python finds "midkrregextool" package.
    sys.path.append(str(SRC_DIR))

from midkrregextool.parser import parse_file    
from midkrregextool.model import Token
from midkrregextool.yale import attach_yale
from midkrregextool.search import search_tokens
from midkrregextool.report import report_hits, report_bigram_hits, maybe_save_hits, ask_yes_no

def format_token(token: Token) -> str:                      
    """
    Return a one-line string representation of a token for quick inspection.
    
    Example output:
        釋詳3:1a |   1 | MAIN | 淨飯王이 | 淨飯王이 | 淨飯王i
    """
    note_flag = "NOTE" if token.is_note else "MAIN"
    return (
        f"{token.source_id:>10} | {token.token_index:>3} | {note_flag:4} | {token.pua} | {token.unicode_form} | {token.yale}"
        )

def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the quick inspection script."""
    default_path = Root / "tests" / "fixtures" / "sample_sekpo_excerpt.txt"
    
    p = argparse.ArgumentParser(
        prog="quick_check_parser.py",
        description="Inspect parsed tokens and optionally run a regex search over token.yale."
    )

    # Optional path (no positional dependency)
    p.add_argument(
        "--path",
        type=Path,
        default=default_path,
        help="Input text file path (default: sample excerpt in tests/fixtures)."
    )

    # Optional n for preview
    p.add_argument(
        "--n",
        type=int,
        default=30,
        help="Number of tokens to show in the preview (default: 30)"
    )

    # Optional regex pattern
    p.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Regex pattern to search over token.yale. If omitted, search is skipped."
    )

    return p.parse_args(argv)    

def cont() -> bool:
    """Ask the user whether to continue execution."""
    return ask_yes_no("Continue?")

def main(argv: list[str] | None = None) -> None:
    """Main entry point for the quick parser inspection script."""
    if argv is None:
        argv = sys.argv[1:]
    
    args = parse_args(argv)

    path: Path = args.path
    n_tokens: int = args.n
    pattern: str | None = args.pattern

    if not path.exists():
        print(f"[Error] File not found: {path}")
        return
    
    # Display basic parsing information.
    print("-" * (len(str(path))))
    print("[INFO] Parsing:")
    print(f"{path}")
    
    # Parse the file and attach Yale romanization.
    tokens = attach_yale(parse_file(path))

    print("[INFO] Displaying the result of `parser.parse_file`")
    print(f"[INFO] Total tokens: {len(tokens)}")
    print(f"[INFO] Showing first {min(n_tokens, len(tokens))} tokens:")
    print("-" * (len(str(path))))

    if not cont():
        return
    
    print("-" * (len(str(path))))

    # Display a token preview grouped by source_id
    last_source_id = None
    for token in tokens[:n_tokens]:
        if token.source_id != last_source_id:
            print(f"\n--- SOURCE {token.source_id} ---")
            last_source_id = token.source_id
        print(format_token(token))

    print("-" * (len(str(path))))
    print("[INFO] Go onto the regex searching tool.")

    if not cont():
        return
    
    print("-" * (len(str(path))))

    if pattern is not None:
        hits = search_tokens(tokens, pattern)

        # Display search results
        if " " in pattern:
            report_bigram_hits(hits, pattern=pattern)
        else:
            report_hits(hits, pattern=pattern)

        # Optionally save the search results to a file.
        maybe_save_hits(hits, pattern=pattern)

if __name__== "__main__":
    main()
