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
from midkrregextool.report import report_hits, report_bigram_hits, maybe_save_hits, maybe_save_bigram_hits, ask_yes_no

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

    # Optional comments
    p.add_argument(
        "--comment", 
        type=str, 
        default=None,
        help="An optional comment field to help the user keep track of the intended purpose of a given regex search"
        )
    
    return p.parse_args(argv)    

def cont() -> bool:
    """Ask the user whether to continue execution."""
    return ask_yes_no("Continue?")

# Make a file list
def collect_input_files(path: Path) -> list[Path]:
    """
    If `path` is a file: return [path]
    If `path` is a directory: return all .txt files inside (non-recursive) sorted by name
    """
    if path.is_file():
        return [path]
    
    if path.is_dir():
        return sorted([p for p in path.iterdir() if p.is_file() and p.suffix ==".txt"])
    
    return []

def main(argv: list[str] | None = None) -> None:
    """Main entry point for the quick parser inspection script."""
    if argv is None:
        argv = sys.argv[1:]
    
    args = parse_args(argv)

    path: Path = args.path
    n_tokens: int = args.n
    pattern: str | None = args.pattern
    comment: str | None = args.comment

    files = collect_input_files(path)

    if not files:
        print(f"[Error] No input files found: {path}")
        return
    
    batch_mode = (len(files) > 1)

    for file_path in files:
        print("-" * 70)
        print("[INFO] Parsing:")
        print(f"{file_path}")

        tokens = attach_yale(parse_file(file_path))

        # if not batch_mode:
        #     print("[INFO] Displaying the result of `parser.parse_file`")
        #     print(f"[INFO] Total tokens: {len(tokens)}")
        #     print(f"[INFO] Showing first {min(n_tokens, len(tokens))} tokens:")
        #     print("-" * 70)

        #     if not cont():
        #         return
            
        #     print("-" * 70)

        #     # Display a token preview grouped by source_id
        #     last_source_id = None
        #     for token in tokens[:n_tokens]:
        #         if token.source_id != last_source_id:
        #             print(f"\n--- SOURCE {token.source_id} ---")
        #             last_source_id = token.source_id
        #         print(format_token(token))

        #     print("-" * 70)
        #     print("[INFO] Go onto the regex searching tool.")

        #     if not cont():
        #         return
            
        #     print("-" * 70)
        
        # else:
        #     print("[INFO] Displaying the result of `parser.parse_file`")
        #     print(f"[INFO] Total tokens: {len(tokens)}")
        #     print(f"[INFO] Showing first {min(n_tokens, len(tokens))} tokens:")
        #     print("-" * 70)

        #     # Display a token preview grouped by source_id
        #     last_source_id = None
        #     for token in tokens[:n_tokens]:
        #         if token.source_id != last_source_id:
        #             print(f"\n--- SOURCE {token.source_id} ---")
        #             last_source_id = token.source_id
        #         print(format_token(token))

        #     print("-" * 70)
        #     print("[INFO] Go onto the regex searching tool.")
            
        #     print("-" * 70)

        if pattern is not None:
            hits = search_tokens(tokens, pattern)

            # Display search results
            if " " in pattern:
                report_bigram_hits(hits, pattern=pattern, comment=comment)
                # Optionally save the search results to a file.
                if not batch_mode:
                    maybe_save_bigram_hits(hits, pattern=pattern, comment=comment)
            else:
                report_hits(hits, pattern=pattern, comment=comment)
                # Optionally save the search results to a file.
                if not batch_mode:
                    maybe_save_hits(hits, pattern=pattern, comment=comment)




if __name__== "__main__":
    main()
