# src/midkrregextool/cli.py

from __future__ import annotations

import argparse                 # To avoid positional arguments
import sys
from dataclasses import dataclass
from pathlib import Path                    # is_file(), is_dir()

from midkrregextool.parser import parse_file    
from midkrregextool.yale import attach_yale
from midkrregextool.search import search_tokens
from midkrregextool.report import report_hits, maybe_save_hits
from midkrregextool.tagger import tag_tokens, load_infl_suffixes, load_lemma_whitelist, train, load_learned_infl_suffixes, update_suffix_counter, dump_known_lemmas, finalize_suffix_proposals, display_lemma_candidates, display_suffix_candidates, load_infl_decomp_from_training
import re
from collections import Counter
import xml.etree.ElementTree as ET

@dataclass(frozen=True)
class CLIArgs:
    path: Path
    pattern: str | None
    purpose: str | None
    period: str | None
    sort: str | None
    encoding: str = "utf-16"
    displaycontext: str = "n"
    training_mode: bool = False
    candidate_mining: str | None = None
    training_data: Path | None = None

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="midkrregextool",
        description="Parse Middle Korean text and run regex search."
    )

    p.add_argument("--path", type=Path, help="Input file or directory.")
    p.add_argument("--pattern", type=str, default=None, help="Regex pattern to search over Yale-romanized Korean texts. When used over a training mode, only matching tokens are shown.")
    p.add_argument("--purpose", type=str, default=None, help="User's purposes for the performed regex search")
    p.add_argument("--encoding", type=str, default="utf-16", help="File encoding (default: utf-16)")
    p.add_argument("--displaycontext", type=str, default = "n", help="Display context around matches (y/n), (default n)")
    p.add_argument("--period", type=str, default=None, help="Filter by historical period")
    p.add_argument ("--training-mode", action="store_true", help="Enable training mode (interactive labeling)")
    p.add_argument("--training-data", type=Path, default=None, help="Path to training data for suffix proposal generation")
    p.add_argument("--candidate-mining", type=str, default = None, choices=["lemma", "suffix"], help="Enable candidate mining mode")
    p.add_argument("--sort", type=str, default=None, choices=["published_year"], help="XML files only; sort by published year string")

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

    # if ns.training-mode is None:
    # if ns.pattern is None: raise SystemExit("[Error] --pattern is required.")

    training_mode = ns.training_mode
    candidate_mining = ns.candidate_mining
    pattern = ns.pattern

    # Search mode requires --pattern
    if (not training_mode) and (not candidate_mining):
        if pattern is None:
            raise SystemExit("[Error] --pattern is required unless --training-mode or --candidate-mining is set.")
    
    # Guard clause for missing --training-data

    training_data: Path | None = None
    
    if ns.training_data is not None:
        training_data = Path(ns.training_data)

        if not training_data.is_absolute():
            repo_root = Path(__file__).resolve().parents[2]
            training_data = (repo_root / training_data).resolve()
        else:
            training_data = training_data.resolve()

    # Guard: training data requires explicit period
    if ns.training_data is not None and ns.period is None:
        raise SystemExit("[Error] --training-data requires --period.")
    
    # Guard clause for invalid options for --candidate-mining

    if ns.candidate_mining is not None and ns.candidate_mining not in ("lemma", "suffix"):
        raise SystemExit("[ERROR] Invalid options for --candidate-mining. Please use \"lemma\" or \"suffix\"")
    
    return CLIArgs(
        path,
        pattern=ns.pattern,
        purpose=ns.purpose,
        encoding=ns.encoding,
        displaycontext=ns.displaycontext,
        period=ns.period,
        sort=ns.sort,
        training_mode=ns.training_mode,
        training_data=training_data,
        candidate_mining = ns.candidate_mining
    )

# Input-file-collecting function

def collect_input_files(path: Path, period: int | None, *, sort: str | None = None) -> list[Path]:

    if path.is_file():
        return [path]
    
    if period is None:
        return sorted([*path.rglob("*.txt"), *path.rglob("*.xml")])

    matched_files: list[Path] = []
    
    sorting_key: dict[Path, str] = {}

    # period filtering: XML metadata(date) needed

    for file in path.rglob("*.xml"):
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError as e:
            print(f"[ERROR] Malformed XML file skipped:")
            print(f"        file = {file}")
            print(f"        error = {e}")
            continue

        published_year = (root.findtext(".//teiHeader//titleStmt//date") or root.findtext(".//date") or "").strip()

        if not published_year:
            print("[WARN] No <date> found; skipped:")
            print(f"       file = {file}")
            continue

        published_century = convert_to_century(published_year)
        if published_century == period:
            matched_files.append(file)

        if sort is not None:
            sorting_key[file] = published_year

    if sort is not None:
        return sorted(matched_files, key=lambda f: sorting_key[f])

    return sorted(matched_files)

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
    
def build_rules(*, training_data: Path | None, period: int | None) -> list[str]:
    rules = load_infl_suffixes() # base rules

    if training_data is not None and period is not None:
        learned = load_learned_infl_suffixes(training_data, period=period)
        if learned:
            print(f"[INFO] Loaded {len(learned)} learned INFL suffixes (period={period}c).")
        else:
            print(f"[INFO] No existing training data found (period={period}c). Using base rules only.")
        rules = sorted(set(rules) | set(learned), key=len, reverse=True)

    return rules
    
def run_train(args: CLIArgs) -> None:

    # Training-only mode

    # Assigning objects to the arguments
    encoding = args.encoding
    period = convert_to_century(args.period)
    displaycontext = "y"
    training_data = args.training_data
    sort = args.sort
    pattern = args.pattern

    VALID = [15, 16, 17, 18, 19, 20] # Valid centuries for period filtering
    
    # Guard clause: training mode requires an explicit period argument

    while period is None:
        raw = input("[INFO] Training mode requires period filtering. Enter 15-20: ").strip()
        period = convert_to_century(raw)

        while period not in VALID:
            raw = input("[ERROR] Please enter a valid period (e.g., 15 for 15th century): ").strip()
            period = convert_to_century(raw)


    files = collect_input_files(args.path, period, sort=sort)

    # Period argument has been provided and validated. 
    
    # Guard clause: no files to train on -> exit early
    if not files:
        print(f"[INFO] No supported files found for period={period}c")
        print(f"[INFO] Training aborted.")
        return
    
    # Import the existing rules
    rules = build_rules(training_data=training_data, period=period)
    lemma_list = load_lemma_whitelist()

    # Collect tokens.
    all_tokens = []


    # Load 

    for file_path in files:

        tokens = attach_yale(parse_file(file_path, encoding=encoding, displaycontext=displaycontext))

        tokens = tag_tokens(tokens, rules, lemma_list)

        all_tokens.extend(tokens)

    # Optional: restrict training targets to tokens whose tagged_form matches a pattern
    if pattern:
        print(f"[INFO] Training-mode pattern filter enabled: {pattern!r} (matched against token.tagged_form).")
        rx = re.compile(pattern)
        all_tokens = [t for t in all_tokens if t.tagged_form and rx.search(t.tagged_form)]

    train(all_tokens, rules, period=period, training_data=training_data)

    return

def run_search(args: CLIArgs) -> None:

    # search mode

    # Assigning objects to arguments
    pattern = args.pattern
    purpose = args.purpose
    encoding = args.encoding
    displaycontext = args.displaycontext
    period = convert_to_century(args.period)
    training_data = args.training_data
    sort = args.sort
    files = collect_input_files(args.path, period, sort=sort)

    last_period = period # Cache the current period to avoid re-collecting input files unless the period changes.

    # No input files found
    if not files:
        print(f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)") 
        return

    # Search loop

    rules = build_rules(training_data=training_data, period=period)
    lemmas = load_lemma_whitelist()
    lemma_list = sorted(lemmas, key=len, reverse=True)

    within_result_search = "n"
        
    while True:

        # Recollect input files when period filter is changed

        if period != last_period:

            files = collect_input_files(args.path, period, sort=sort)
            last_period = period

            if not files:
                print(f"[INFO] No supported files found for period={period}.")
                continue

        # Initial search or non-within-previous-results search
        if within_result_search == "n":

            bigram_flag = " " in pattern

            all_hits = []

            infl_decomp = None
            if training_data is not None:
                infl_decomp = load_infl_decomp_from_training(training_data / f"training_{period}c.jsonl",period=period)

            for file_path in files:
                tokens = attach_yale(parse_file(file_path,encoding=encoding,displaycontext=displaycontext))

                tokens = tag_tokens(tokens, rules, lemma_list, infl_decomp=infl_decomp)

                hits = search_tokens(tokens, pattern)

                # If there is no hit in the current file, skip it.

                if len(hits) == 0:
                    continue

                print(f"[INFO] Searching in file: {file_path}")
                print(f"[INFO] pattern={pattern!r} hits={len(hits)} purposes={purpose!r}")
                print("-" * 70)

                report_hits(hits, bigram_flag)

                all_hits.extend(hits)

        # Search within previous results
        elif within_result_search == "y":
            original_hits = all_hits
            all_hits = []

            rx = re.compile(pattern)

            for hit in original_hits:
                # Reassign the matched strings attribute for each hit
                joined = " ".join((tok.morph_str or tok.tagged_form) for tok in hit)
                m = rx.search(joined)
                if m:
                    # Store the matched span for display/save
                    hit[0].matched_part = m.group(0)
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

            # Guard clause: if there is no hits, no within-results search and no result save
            if len(all_hits) == 0:
                print("[INFO] No previous hits. Running a fresh search.")
                within_result_search = "n"
                save_before_next = "n"

            # If results exist, ask if the user wants to perform a within-results earch and save results before moving on
            else:
                # Save before proceeding to the next search?
                save_before_next = input("Do you want to save the current results before the next search? Type \"y\" if you want, otherwise press any keys: ").strip().lower()

                if save_before_next == "y":
                    maybe_save_hits(all_hits, pattern=pattern, purpose=purpose)

                # Ask if within-previous-results search is desired
                within_result_search = input("Do you want to search within the previous results? Type \"y\" or \"n\": ").strip().lower()

                # Guard for valid input
                if within_result_search not in ("y","n"):
                    within_result_search = input("Please type 'y' or 'n': ").strip().lower()

            # Ask if period changes if not within-result search
            if within_result_search == "n":
                new_period = input("Provide a new period filter if you want to change (e.g., 15c). Otherwise, type enter:").strip()

                if new_period:
                    new_period_c = convert_to_century(new_period)
                    if new_period_c is None:
                        print("[ERROR] Invalid period. Keeping the previous period.")
                    else:
                        period = new_period_c

            while True:
                pattern = input("Enter new regex pattern: ").strip("\"")
                try:
                    re.compile(pattern)
                    break
                except re.error as e:
                    print(f"[ERROR] Invalid regex pattern: {e}")
                    print(f"[INFO] Please enter a valid regex.")
            
            bigram_flag = " " in pattern
            new_purpose = input("Enter purpose for the new search (or press Enter if you wish to maintain the purpose of the previous search): ").strip()
            if new_purpose:
                purpose = new_purpose


    # After all searches are done, ask to save the results
    if all_hits:
        maybe_save_hits(all_hits, pattern=pattern, purpose=purpose)

def run_candidate_mining(args: CLIArgs) -> None:

    # Assign objects
    training_data = args.training_data
    period = convert_to_century(args.period)
    displaycontext = args.displaycontext
    encoding = args.encoding
    sort = args.sort
    files = collect_input_files(args.path, period, sort=sort)
    
    if args.candidate_mining == "lemma":
        lemma_flag = True
        suffix_flag = False

    else: 
        lemma_flag = False
        suffix_flag = True

    # Placeholder for suffix anchor
    suffix_anchor = args.pattern

    # No input files found
    if not files:
        print(f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)") 
        return

    c = Counter()

    rules = build_rules(training_data=training_data, period=period)
    lemma_counter: Counter[str] = Counter()
    lemmas = load_lemma_whitelist()
    lemma_list = sorted(lemmas, key=len, reverse=True)

    for file_path in files:
        tokens = attach_yale(parse_file(file_path,encoding=encoding,displaycontext=displaycontext))
        tokens = tag_tokens(tokens, rules, lemma_list, debug_suffixes = suffix_flag)

        if suffix_flag:
            update_suffix_counter(c, tokens, rules, max_len = 8, suffix_must_endwith=suffix_anchor)

        elif lemma_flag:
            for lem, cnt in dump_known_lemmas(tokens, rules, lemma_list, top_k=50):
                lemma_counter[lem] += cnt


    all_proposals = finalize_suffix_proposals(c, rules, top_k=50, min_count = 1)

    if suffix_flag:
        display_suffix_candidates(all_proposals)

    if lemma_flag:
        display_lemma_candidates(lemma_counter)

def run(args: CLIArgs) -> None:

    # Candidate-mining mode

    if args.candidate_mining:
        run_candidate_mining(args)
        return

    # Training mode

    if args.training_mode:
        run_train(args)
        return
    
    run_search(args)
    
def main(argv: list[str] | None = None) -> None:
    args = parse_cli_args(argv)
    run(args)