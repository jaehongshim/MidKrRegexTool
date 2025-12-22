# src/midkrregextool/cli.py

from __future__ import annotations

import argparse                 # To avoid positional arguments
import sys
from dataclasses import dataclass
from pathlib import Path                    # is_file(), is_dir()

from midkrregextool.parser import parse_file    
from midkrregextool.model import Token
from midkrregextool.yale import attach_yale
from midkrregextool.search import search_tokens
from midkrregextool.report import report_hits, maybe_save_hits, ask_yes_no

@dataclass(frozen=True)
class CLIArgs:
    path: Path
    pattern: str
    comment: str | None

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="midkrregextool",
        description="Parse Middle Korean text and run regex search."
    )

    p.add_argument("--path", type=Path, help="Input file or directory.")
    p.add_argument("--pattern", type=str, default=None, help="Regex pattern to search over Yale-romanized Korean texts")
    p.add_argument("--comment", type=str, default=None, help="User's comments for the performed regex search")

    return p

def parse_cli_args(args: list[str] | None) -> CLIArgs:

    if args is None:
        args = sys.argv[1:]

    parser = build_parser()
    ns = parser.parse_args(args)

    # If --path argument is not provided, set the current working directory as path
    path = ns.path if ns.path is not None else Path.cwd()

    if ns.path is None:
        print(f"[INFO] No --path provided. Running on the working directory: {path}")

    if ns.pattern is None: raise SystemExit("[Error] --pattern is required.")

    return CLIArgs(
        path,
        pattern=ns.pattern,
        comment=ns.comment
    )

# Input-file-collecting function

def collect_input_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".txt")
    
    return []


def run(args: CLIArgs) -> None:
    
    # Assigning objects to arguments
    pattern = args.pattern
    comment = args.comment
    files = collect_input_files(args.path)
    if not files:
        return
    
    batch_mode = (len(files) > 1)

    all_hits = []

    for file_path in files:
        tokens = attach_yale(parse_file(file_path))

        hits = search_tokens(tokens, pattern)

        report_hits(hits,pattern=pattern,comment=comment)

        all_hits.extend(hits)

    maybe_save_hits(all_hits, pattern=pattern, comment=comment)

def main(argv: list[str] | None = None) -> None:
    args = parse_cli_args(argv)
    run(args)