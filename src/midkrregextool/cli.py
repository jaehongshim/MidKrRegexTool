# src/midkrregextool/cli.py

from __future__ import annotations

import argparse                 # To avoid positional arguments
import sys
from dataclasses import dataclass
from pathlib import Path                    # is_file(), is_dir()
from collections import Counter

from midkrregextool.parser import parse_file    
from midkrregextool.model import Token
from midkrregextool.yale import attach_yale
from midkrregextool.search import search_tokens
from midkrregextool.report import report_hits, maybe_save_hits
from midkrregextool.tagger import tag_tokens, load_infl_suffixes, update_suffix_counter, finalize_suffix_proposals, dump_known_lemmas, display_lemma_candidates, display_suffix_candidates, load_lemma_whitelist, train
import re
import xml.etree.ElementTree as ET

@dataclass(frozen=True)
class CLIArgs:
    path: Path
    pattern: str
    purpose: str | None
    period: str | None
    encoding: str = "utf-16"
    displaycontext: str = "n"
    training_mode: bool = False
    training_data: Path | None = None

@dataclass(frozen=True)
class DebugOptions:
    suffix_proposals: bool = False
    suffix_must_endwith: str | None = None
    dump_lemma_seed: bool = False

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="midkrregextool",
        description="Parse Middle Korean text and run regex search."
    )

    p.add_argument("--path", type=Path, help="Input file or directory.")
    p.add_argument("--pattern", type=str, default=None, help="Regex pattern to search over Yale-romanized Korean texts")
    p.add_argument("--purpose", type=str, default=None, help="User's purposes for the performed regex search")
    p.add_argument("--encoding", type=str, default="utf-16", help="File encoding (default: utf-16)")
    p.add_argument("--displaycontext", type=str, default = "n", help="Display context around matches (y/n), (default n)")
    p.add_argument("--period", type=str, default=None, help="Filter by historical period")
    p.add_argument ("--training-mode", type=bool, default=False, help="Enable training mode for suffix proposal generation")
    p.add_argument ("--training-data", type=Path, default=None, help="Path to training data for suffix proposal generation")

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
        purpose=ns.purpose,
        encoding=ns.encoding,
        displaycontext=ns.displaycontext,
        period=ns.period,
        training_mode=ns.training_mode,
        training_data=ns.training_data
    )

# Input-file-collecting function

def collect_input_files(path: Path, period: int | None) -> list[Path]:

    if path.is_file():
        return [path]
    
    if path.is_dir():
        # When filtering by periods
        if period is not None:
            matched_files: list[Path] = []
            for file in path.iterdir():
                if file.suffix.lower() != ".txt" and file.suffix.lower() != ".xml":
                    continue
                if file.suffix.lower() == ".xml":
                    root = ET.parse(file).getroot()
                    published_year = (root.findtext(".//date")).strip()
                    published_century = convert_to_century(published_year)
                    if published_century == period:
                        matched_files.append(file)
                    else:
                        continue
            return sorted(matched_files)
        else:
            return sorted([*path.rglob("*.txt"),*path.rglob("*.xml")])
    
    return []

def convert_to_century(year: str) -> int | None:
    year = (year or "").strip()
    if not year:
        return None

    digits = "".join(ch for ch in year if ch.isdigit())
    if not digits:
        return None

    y = int(digits)

    # If the input is in the century format already
    if y < 20:
        return y
    
    # If the input is in the year format
    else:
        return (y - 1) // 100 + 1


def run(args: CLIArgs) -> None:
    
    # Assigning objects to arguments
    pattern = args.pattern
    purpose = args.purpose
    encoding = args.encoding
    displaycontext = args.displaycontext
    period = convert_to_century(args.period)
    bigram_flag = " " in pattern
    files = collect_input_files(args.path,period)
    training_mode = args.training_mode
    training_data = args.training_data


    # No input files found
    if not files:
        print(f"[INFO] No .txt files found under: {args.path}\n")
        print(f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)") 
        return
    
    # Debug mode?
    debug = DebugOptions(
        suffix_proposals = False,
        suffix_must_endwith="nila",
        dump_lemma_seed=False
    )
    debug_mode = False

    batch_mode = (len(files) > 1)


    c = Counter()

    if debug.dump_lemma_seed:
        lemma_counter: Counter[str] = Counter()

    infl_suffixes = load_infl_suffixes()
    lemmas = load_lemma_whitelist()
    lemma_list = sorted(lemmas, key=len, reverse=True)

    # debug loop

    if debug_mode == True:

        for file_path in files:

            tokens = attach_yale(parse_file(file_path,encoding=encoding,displaycontext=displaycontext))

            tokens = tag_tokens(tokens, infl_suffixes, lemma_list, debug_suffixes = debug.suffix_proposals)

            if debug.suffix_proposals:
                update_suffix_counter(c, tokens, infl_suffixes, max_len = 8, suffix_must_endwith=debug.suffix_must_endwith)

            if debug.dump_lemma_seed:
                for lem, cnt in dump_known_lemmas(tokens, infl_suffixes, lemma_list, top_k=50):
                    lemma_counter[lem] += cnt

        all_proposals = finalize_suffix_proposals(c, infl_suffixes, top_k=50, min_count = 1)

        if debug.suffix_proposals:
            display_suffix_candidates(all_proposals)

        if debug.dump_lemma_seed:
            display_lemma_candidates(lemma_counter)
    
    # Search loop

    VALID = [15, 16, 17, 18, 19, 20] # Valid centuries for period filtering

    within_result_search = "n"
        
    while True:

        if training_mode:
            # Ensure period filtering is set
            if period is not None:
                change = input(f"[INFO] Current period = {period}. Change period? (y/n) > ").strip().lower()
                if change == "y":
                    period = None

            # Reask period if not set
            if period is None:
                raw = input("[INFO] Training mode requires period filtering. Enter 15-20: ").strip()
                period = convert_to_century(raw)

                while period not in VALID:
                    raw = input("[ERROR] Please enter a valid period (e.g., 15 for 15th century): ").strip()
                    period = convert_to_century(raw)


            # Collect input files again in case period filter is changed

            
            rules = ["dummy_rule_1","dummy_rule_2"]  # Placeholder for actual rules

        # Recollect input files in case period filter is changed
        files = collect_input_files(args.path, period)

        if not files:
            print(f"[INFO] No supported files found for period={period}.")

        # Initial search or non-within-previous-results search
        if within_result_search == "n":

            bigram_flag = " " in pattern

            all_hits = []
            if training_mode:
                all_tokens = []

            for file_path in files:
                tokens = attach_yale(parse_file(file_path,encoding=encoding,displaycontext=displaycontext))

                tokens = tag_tokens(tokens, infl_suffixes, lemma_list, debug_suffixes = debug.suffix_proposals)

                hits = search_tokens(tokens, pattern)

                print(f"[INFO] Searching in file: {file_path}")
                print(f"[INFO] pattern={pattern!r} hits={len(hits)} purposes={purpose!r}")
                print("-" * 70)

                report_hits(hits, bigram_flag)

                all_hits.extend(hits)
                
                if training_mode:
                    all_tokens.extend(tokens)
        
            # Training mode is on
            if training_mode:
                train(all_tokens, rules, period, training_data)

        # Search within previous results
        elif within_result_search == "y":
            original_hits = all_hits
            all_hits = []

            rx = re.compile(pattern)

            for hit in original_hits:
                joined = " ".join(tok.tagged_form for tok in hit)
                if rx.search(joined):
                    all_hits.append(hit)
            print(f"[INFO] Searching within previous results")
            print(f"[INFO] pattern={pattern!r} hits={len(all_hits)} purposes={purpose!r}")
            report_hits(all_hits,bigram_flag)


        # Ask if another search is to be performed
        another_search = input("Do you want to run another search? Type Enter to continue, \"q\" to exit: ").strip().lower()

        # Guard for valid input
        if another_search not in ("","q"):
            another_search = input("Please type Enter to continue, or 'q' to exit: ").strip().lower()
        
        # Exit condition
        if another_search == "q":
            break

        # Continue condition
        elif another_search == "":

            # Save before proceeding to the next search?
            save_before_next = input("Do you want to save the current results before the next search? Type \"y\" if you want, otherwise press any keys: ").strip().lower()

            if save_before_next == "y":
                maybe_save_hits(all_hits, pattern=pattern, purpose=purpose)

            # Ask if within-previous-results search is desired
            within_result_search = input("Do you want to search within the previous results? Type \"y\" or \"n\": ").strip().lower()

            # Guard for valid input
            if within_result_search not in ("y","n"):
                within_result_search = input("Please type 'y' or 'n': ").strip().lower()
            pattern = input("Enter new regex pattern: ").strip("\"")
            new_purpose = input("Enter purpose for the new search (or press Enter if you wish to maintain the purpose of the previous search): ").strip()
            if new_purpose:
                purpose = new_purpose


    # After all searches are done, ask to save the results

    maybe_save_hits(all_hits, pattern=pattern, purpose=purpose)



def main(argv: list[str] | None = None) -> None:
    args = parse_cli_args(argv)
    run(args)