# src/midkrregextool/cli.py

from __future__ import annotations

import argparse  # To avoid positional arguments
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path  # is_file(), is_dir()

from midkrregextool.parser import parse_file
from midkrregextool.report import maybe_save_hits, report_hits
from midkrregextool.search import search_tokens
from midkrregextool.tagger import (
    load_infl_suffixes,
    load_lemma_lexicon,
    tag_tokens,
)
from midkrregextool.training import (
    load_infl_decomp_from_training,
    load_pos_to_allowed_morphemes_inventory_from_training,
    load_rest_surfaces_from_training,
    train,
    training_priority,
)
from midkrregextool.yale import attach_yale


@dataclass(frozen=True)
class CLIArgs:
    path: Path
    pattern: str | None
    purpose: str | None
    period: str | None
    sort: str | None
    encoding: str = "utf-16"
    display_context: bool = False
    training_mode: bool = False
    training_data: Path | None = None
    include_ch: bool = False
    token_repr: str | None = None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="midkrregextool",
        description="Parse Middle Korean text and run regex search.",
    )

    p.add_argument("--path", type=Path, help="Input file or directory.")
    p.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Regex pattern to search over Yale-romanized Korean texts. When used over a training mode, only matching tokens are shown.",
    )
    p.add_argument(
        "--purpose",
        type=str,
        default=None,
        help="User's purposes for the performed regex search",
    )
    p.add_argument(
        "--encoding", type=str, default="utf-16", help="File encoding (default: utf-16)"
    )
    p.add_argument(
        "--display-context",
        action="store_true",
        help="Enable a context-display function",
    )
    p.add_argument(
        "--period", type=str, default=None, help="Filter by historical period"
    )
    p.add_argument(
        "--training-mode",
        action="store_true",
        help="Enable training mode (interactive labeling)",
    )
    p.add_argument(
        "--training-data",
        type=Path,
        default=None,
        help="Path to training data for suffix proposal generation",
    )
    p.add_argument(
        "--sort",
        type=str,
        default=None,
        choices=["published_year"],
        help="XML files only; sort by published year string",
    )
    p.add_argument(
        "--token-repr",
        type=str,
        default=None,
        choices=["yale", "tagged_form"],
        help="Select the token representation used for search or training.",
    )
    p.add_argument(
        "--include-ch",
        action="store_true",
        help="Train or search also on classical Chinese texts minimally annotated with Korean",
    )

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
    pattern = ns.pattern

    # Search mode requires --pattern
    if not training_mode:
        if pattern is None:
            raise SystemExit(
                "[Error] --pattern is required unless --training-mode is set."
            )

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

    # Set the default value of repr: "yale" for training-mode and "tagged_form" for search-mode
    if (training_mode) and (ns.token_repr is None):
        token_repr = "yale"
    elif (not training_mode) and (ns.token_repr) is None:
        token_repr = "tagged_form"
    else:
        token_repr = ns.token_repr

    return CLIArgs(
        path,
        pattern=ns.pattern,
        purpose=ns.purpose,
        encoding=ns.encoding,
        display_context=ns.display_context,
        period=ns.period,
        sort=ns.sort,
        training_mode=ns.training_mode,
        include_ch=ns.include_ch,
        training_data=training_data,
        token_repr=token_repr,
    )


# Input-file-collecting function


def collect_input_files(
    path: Path, period: int | None, *, sort: str | None = None
) -> list[Path]:

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
            print("[ERROR] Malformed XML file skipped:")
            print(f"        file = {file}")
            print(f"        error = {e}")
            continue

        published_year = (
            root.findtext(".//teiHeader//titleStmt//date")
            or root.findtext(".//date")
            or ""
        ).strip()

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
    return load_infl_suffixes(period=period)


def run_train(args: CLIArgs) -> None:

    # Training-only mode

    # Assigning objects to the arguments
    encoding = args.encoding
    period = convert_to_century(args.period)
    training_data = args.training_data
    sort = args.sort
    pattern = args.pattern
    token_repr = args.token_repr
    display_context = True
    include_ch = args.include_ch

    VALID = [15, 16, 17, 18, 19, 20]  # Valid centuries for period filtering

    # Guard clause: training mode requires an explicit period argument

    while period is None:
        raw = input(
            "[INFO] Training mode requires period filtering. Enter 15-20: "
        ).strip()
        period = convert_to_century(raw)

        while period not in VALID:
            raw = input(
                "[ERROR] Please enter a valid period (e.g., 15 for 15th century): "
            ).strip()
            period = convert_to_century(raw)

    lexicon = load_lemma_lexicon(period, training_data=training_data)

    t0 = time.perf_counter()
    files = collect_input_files(args.path, period, sort=sort)
    print(f"[TIMING] collect_input_files: {time.perf_counter() - t0:.3f}s")

    # Period argument has been provided and validated.

    # Guard clause: no files to train on -> exit early
    if not files:
        print(f"[INFO] No supported files found for period={period}c")
        print("[INFO] Training aborted.")
        return

    # Import the existing rules
    rules = build_rules(training_data=training_data, period=period)

    # Collect tokens.
    all_tokens = []
    bigram_hits = []  # Collect per-file bigram hits only when needed.

    rx = None
    is_bigram = False

    if pattern:
        if token_repr == "tagged_form":
            print(
                f"[INFO] Training-mode pattern filter enabled: {pattern!r} (matched against token.tagged_form)."
            )
        rx = re.compile(pattern)
        is_bigram = (
            " " in pattern
        )  # If pattern has a space, training unit becomes (Token, Token)

    # Load
    infl_decomp = None
    rest_set = set()
    pos_to_allowed_morphemes: dict[str, set[str]] = {}

    if training_data is not None:
        infl_decomp = load_infl_decomp_from_training(
            training_data / f"training_{period}c.jsonl"
        )
        rest_set = load_rest_surfaces_from_training(training_data, period)
        pos_to_allowed_morphemes = (
            load_pos_to_allowed_morphemes_inventory_from_training(training_data, period)
        )

    t_tag = time.perf_counter()
    for file_path in files:

        tokens = attach_yale(
            parse_file(file_path, encoding=encoding, display_context=display_context),
            include_ch,
        )

        tokens = tag_tokens(
            tokens,
            rules,
            lexicon=lexicon,
            rest_set=rest_set,
            infl_decomp=infl_decomp,
            pos_to_allowed_morphemes=pos_to_allowed_morphemes,
        )

        all_tokens.extend(tokens)

        if pattern and is_bigram:
            # Bigram hits must be collected per file (do NOT cross file boundaries).
            bigram_hits.extend(search_tokens(tokens, pattern, token_repr))

    print(f"[TIMING] tag_tokens {file_path.name}: {time.perf_counter() - t_tag:.3f}s")

    # Coverage measurement

    total_tokens = 0
    covered_tokens = 0

    for tok in all_tokens:
        total_tokens += 1
        if tok.tagged_form:
            if tok.tagged_form.endswith("/INFL") or (
                tok.tagged_form == "NO-TAGGED-FORM"
            ):
                continue
            covered_tokens += 1

    if total_tokens > 0:
        print(
            f"[INFO] Analysis coverage: {covered_tokens}/{total_tokens} ({covered_tokens/total_tokens:.1%})"
        )
    else:
        print("[INFO] Analysis coverage: 0/0 (0.0%)")

    token_lookup = {(t.source_id, t.token_index): t for t in all_tokens}

    # Decide training targets after collecting everything.
    t_select = time.perf_counter()
    if pattern and is_bigram:
        train_targets = bigram_hits
    elif pattern:
        if token_repr == "tagged_form":
            train_targets = [
                t for t in all_tokens if t.tagged_form and rx.search(t.tagged_form)
            ]
        else:
            train_targets = [t for t in all_tokens if t.yale and rx.search(t.yale)]
    else:
        train_targets = all_tokens
    print(f"[TIMING] target selection: {time.perf_counter() - t_select:.3f}s")

    known_rests = rest_set

    t_sort = time.perf_counter()
    train_targets = sorted(
        train_targets,
        key=lambda tok: training_priority(
            tok,
            lexicon=lexicon,
            known_rests=known_rests,
        ),
    )
    print(f"[TIMING] target sorting: {time.perf_counter() - t_sort:.3f}s")

    t_train = time.perf_counter()
    train(
        train_targets,
        rules,
        period=period,
        training_data=training_data,
        lexicon=lexicon,
        token_lookup=token_lookup,
    )
    print(f"[TIMING] train(): {time.perf_counter() - t_train:.3f}s")

    return


def run_search(args: CLIArgs) -> None:

    # search mode

    # Assigning objects to arguments
    pattern = args.pattern
    purpose = args.purpose
    encoding = args.encoding
    display_context = args.display_context
    period = convert_to_century(args.period)
    training_data = args.training_data
    sort = args.sort
    files = collect_input_files(args.path, period, sort=sort)
    token_repr = args.token_repr
    include_ch = args.include_ch

    last_period = period  # Cache the current period to avoid re-collecting input files unless the period changes.

    # No input files found
    if not files:
        print(
            f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)"
        )
        return

    # Search loop

    rules = build_rules(training_data=training_data, period=period)
    lexicon = load_lemma_lexicon(period, training_data=training_data)

    within_result_search = "n"

    while True:
        bigram_flag = " " in pattern

        # Recollect input files when period filter is changed

        if period != last_period:

            files = collect_input_files(args.path, period, sort=sort)
            last_period = period
            rules = build_rules(training_data=training_data, period=period)
            lexicon = load_lemma_lexicon(period, training_data=training_data)

            if not files:
                print(f"[INFO] No supported files found for period={period}.")
                continue

        # Initial search or non-within-previous-results search
        if within_result_search == "n":

            all_hits = []

            infl_decomp = None
            rest_set = set()
            pos_to_allowed_morphemes: dict[str, set[str]] = {}

            if training_data is not None:
                infl_decomp = load_infl_decomp_from_training(
                    training_data / f"training_{period}c.jsonl"
                )
                rest_set = load_rest_surfaces_from_training(training_data, period)
                pos_to_allowed_morphemes = (
                    load_pos_to_allowed_morphemes_inventory_from_training(
                        training_data, period
                    )
                )

            for file_path in files:
                tokens = attach_yale(
                    parse_file(
                        file_path, encoding=encoding, display_context=display_context
                    ),
                    include_ch,
                )

                tokens = tag_tokens(
                    tokens,
                    rules,
                    lexicon=lexicon,
                    rest_set=rest_set,
                    infl_decomp=infl_decomp,
                    pos_to_allowed_morphemes=pos_to_allowed_morphemes,
                )

                hits = search_tokens(tokens, pattern, token_repr)

                # If there is no hit in the current file, skip it.

                if len(hits) == 0:
                    continue

                print(f"[INFO] Searching in file: {file_path}")
                print(
                    f"[INFO] pattern={pattern!r} hits={len(hits)} purposes={purpose!r}"
                )
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
                joined = " ".join((tok.tagged_form or tok.yale) for tok in hit)
                m = rx.search(joined)
                if m:
                    # Store the matched span for display/save
                    hit[0].matched_part = m.group(0)
                    all_hits.append(hit)
            print("[INFO] Searching within previous results")
            print(
                f"[INFO] pattern={pattern!r} hits={len(all_hits)} purposes={purpose!r}"
            )
            report_hits(all_hits, bigram_flag)

        # Ask if another search is to be performed
        another_search = (
            input(
                'Do you want to run another search? Type Enter to continue, "q" to exit: '
            )
            .strip()
            .lower()
        )

        # Guard for valid input
        if another_search not in ("", "q"):
            another_search = (
                input("Please type Enter to continue, or 'q' to exit: ").strip().lower()
            )

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
                save_before_next = (
                    input(
                        'Do you want to save the current results before the next search? Type "y" if you want, otherwise press any keys: '
                    )
                    .strip()
                    .lower()
                )

                if save_before_next == "y":
                    maybe_save_hits(all_hits, pattern=pattern, purpose=purpose)

                # Ask if within-previous-results search is desired
                within_result_search = (
                    input(
                        'Do you want to search within the previous results? Type "y" or "n": '
                    )
                    .strip()
                    .lower()
                )

                # Guard for valid input
                if within_result_search not in ("y", "n"):
                    within_result_search = (
                        input("Please type 'y' or 'n': ").strip().lower()
                    )

            # Ask if period changes if not within-result search
            if within_result_search == "n":
                new_period = input(
                    "Provide a new period filter if you want to change (e.g., 15c). Otherwise, type enter:"
                ).strip()

                if new_period:
                    new_period_c = convert_to_century(new_period)
                    if new_period_c is None:
                        print("[ERROR] Invalid period. Keeping the previous period.")
                    else:
                        period = new_period_c

            while True:
                pattern = input("Enter new regex pattern: ").strip('"')
                try:
                    re.compile(pattern)
                    break
                except re.error as e:
                    print(f"[ERROR] Invalid regex pattern: {e}")
                    print("[INFO] Please enter a valid regex.")

            new_purpose = input(
                "Enter purpose for the new search (or press Enter if you wish to maintain the purpose of the previous search): "
            ).strip()
            if new_purpose:
                purpose = new_purpose

    # After all searches are done, ask to save the results
    if all_hits:
        maybe_save_hits(all_hits, pattern=pattern, purpose=purpose)


def run(args: CLIArgs) -> None:

    if args.include_ch:
        print(
            "[INFO] All tokens including minimally-annotated classical Chinese texts are processed."
        )
    else:
        print(
            "[INFO] Tokens from minimally-annotated classical Chinese texts are now filtered out."
        )

    # Training mode

    if args.training_mode:
        run_train(args)
        return

    run_search(args)


def main(argv: list[str] | None = None) -> None:
    args = parse_cli_args(argv)
    run(args)
