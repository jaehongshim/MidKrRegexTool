# src/midkrregextool/cli.py

from __future__ import annotations

import argparse  # To avoid positional arguments
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path  # is_file(), is_dir()

from tqdm import tqdm

from midkrregextool.conllu import tokens_to_conllu
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
    corpus_list: bool = False
    training_mode: bool = False
    training_data: Path | None = None
    classical_ch: bool = False
    token_repr: str | None = None
    exclude_ch: bool = False
    print_corpus: bool = False
    document_type: str | None = None
    export_conllu: bool = False


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
        choices=["published_year", "published_century"],
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
        "--classical-ch",
        action="store_true",
        help="Train or search also on classical Chinese texts minimally annotated with Korean",
    )
    p.add_argument(
        "--corpus-list",
        action="store_true",
        help="Print the full list of corpora.",
    )
    p.add_argument(
        "--exclude-ch",
        action="store_true",
        help="Exclude tokens with Chinese characters when for training or search",
    )
    p.add_argument(
        "--print-corpus",
        action="store_true",
        help="Print tagged corpus",
    )
    p.add_argument(
        "--document-type",
        type=str,
        default=None,
        choices=[
            "letter",
            "non-letter",
            # To be elaborated
        ],
        help="Train or search on a specific type of documents.",
    )
    p.add_argument(
        "--export-conllu",
        action="store_true",
        help="Perform a Universal-Dependencies analysis",
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
    print_corpus = ns.print_corpus
    pattern = ns.pattern
    document_type = ns.document_type
    corpus_list = ns.corpus_list
    export_conllu = ns.export_conllu

    if document_type:
        print(
            f"[INFO] document_type has been set to `{document_type}.` Any subsequent steps will be operated only on {document_type} files."
        )
    else:
        print(
            "[INFO] document_type argument has not been provided. All the available files in the file path will be processed."
        )

    # Search mode requires --pattern
    if not (training_mode or print_corpus or corpus_list or export_conllu):
        if pattern is None:
            raise SystemExit(
                "[ERROR] --pattern is required unless --training-mode is set."
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
        raise SystemExit("[ERROR] --training-data requires --period.")

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
        corpus_list=ns.corpus_list,
        period=ns.period,
        sort=ns.sort,
        training_mode=ns.training_mode,
        classical_ch=ns.classical_ch,
        training_data=training_data,
        token_repr=token_repr,
        exclude_ch=ns.exclude_ch,
        print_corpus=ns.print_corpus,
        document_type=ns.document_type,
        export_conllu=export_conllu,
    )


# Input-file-collecting function


def collect_input_files(
    path: Path,
    period: int | None,
    *,
    sort: str | None = None,
    document_type: str | None = None,
    corpus_list: bool | None = None,
) -> list[Path]:

    if path.is_file():
        return [path]

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

        # Document selecting field

        if document_type == "letter":
            if root.find(".//letter") is None:
                continue
        elif document_type == "non-letter":
            if root.find(".//letter") is not None:
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

        if corpus_list:
            matched_files.append(file)

        else:
            if published_century == period:
                matched_files.append(file)
            else:
                continue

        if sort is not None:
            if sort == "published_year":
                sorting_key[file] = published_year
            elif sort == "published_century":
                sorting_key[file] = published_century

    if sort is not None:
        return sorted(matched_files, key=lambda f: sorting_key[f])

    return sorted(matched_files)


def convert_to_century(year: str) -> int | None:
    year = (year or "").strip()
    if not year:
        return None

    m = re.search(r"\d+", year)
    if m is None:
        return None

    y = int(m.group())

    if y < 20:
        return y

    return (y - 1) // 100 + 1


def build_rules(*, training_data: Path | None, period: int | None) -> list[str]:
    return load_infl_suffixes(period=period)


def run_corpus_list(args: CLIArgs) -> None:

    period = convert_to_century(args.period)
    document_type = args.document_type
    corpus_list = args.corpus_list
    sort = args.sort

    files = collect_input_files(
        args.path,
        period,
        sort=sort,
        document_type=document_type,
        corpus_list=corpus_list,
    )

    with open("corpus_list.txt", "w", encoding="utf-8") as out:

        out.write("Directory\tFile name\tCentury\tTitle\tVolume\tYear\tauthor\n")
        for file_path in files:
            root = ET.parse(file_path).getroot()

            title = (
                root.findtext(".//teiHeader//titleStmt//title")
                or root.findtext(".//title")
            ).strip()

            volume = root.find(".//teiHeader//titleStmt//volume")

            if volume is not None:
                volume_n = volume.get("n")
            else:
                volume_n = ""

            author = root.findtext(".//teiHeader//titleStmt//author")

            if author is None:
                author = ""

            published_year = (
                root.findtext(".//teiHeader//titleStmt//date")
                or root.findtext(".//date")
                or ""
            ).strip()

            published_century = convert_to_century(published_year)

            relative_path = file_path.relative_to(Path.cwd())

            m = re.match(r"(^.+?\\)([^\\]+?xml)$", str(relative_path))
            directory_name = m.group(1)
            file_name = m.group(2)

            print(
                f"{directory_name}\t{file_name}\t{published_century}\t{title}\t{volume_n}\t{published_year}\t{author}"
            )
            out.write(
                f"{directory_name}\t{file_name}\t{published_century}\t{title}\t{volume_n}\t{published_year}\t{author}\n"
            )


def run_train(args: CLIArgs) -> None:

    # Training-only mode

    # Assigning objects to the arguments
    encoding = args.encoding
    period = convert_to_century(args.period)
    training_data = args.training_data
    sort = args.sort
    document_type = args.document_type
    pattern = args.pattern
    token_repr = args.token_repr
    display_context = True
    classical_ch = args.classical_ch
    exclude_ch = args.exclude_ch

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
    files = collect_input_files(
        args.path, period, sort=sort, document_type=document_type
    )
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
            classical_ch,
            exclude_ch,
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
                tok.tagged_form.endswith("NO-TAGGED_FORM")
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
    document_type = args.document_type
    sort = args.sort
    files = collect_input_files(
        args.path, period, sort=sort, document_type=document_type
    )
    token_repr = args.token_repr
    classical_ch = args.classical_ch
    exclude_ch = args.exclude_ch

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

            files = collect_input_files(
                args.path, period, sort=sort, document_type=document_type
            )
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
                    classical_ch,
                    exclude_ch,
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

        print(f"[INFO] Search completed for pattern `{pattern}`")
        print(f"\tTotal hits: {len(all_hits)}")

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


def run_print_corpus(args: CLIArgs) -> None:

    # print corpus mode

    # Assigning objects to arguments
    encoding = args.encoding
    period = convert_to_century(args.period)
    training_data = args.training_data
    sort = args.sort
    document_type = args.document_type
    files = collect_input_files(
        args.path, period, sort=sort, document_type=document_type
    )
    display_context = args.display_context
    classical_ch = args.classical_ch
    exclude_ch = False

    # No input files found
    if not files:
        print(
            f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)"
        )
        return

    # Print loop

    rules = build_rules(training_data=training_data, period=period)
    lexicon = load_lemma_lexicon(period, training_data=training_data)

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

    for file_path in files:
        tokens = attach_yale(
            parse_file(file_path, encoding=encoding, display_context=display_context),
            classical_ch,
            exclude_ch,
        )

        tokens = tag_tokens(
            tokens,
            rules,
            lexicon=lexicon,
            rest_set=rest_set,
            infl_decomp=infl_decomp,
            pos_to_allowed_morphemes=pos_to_allowed_morphemes,
        )

        for token in tokens:
            print(f"{token.unicode_form}: {token.tagged_form}")


def run_export_conllu(args: CLIArgs) -> None:

    # Assigning objects to arguments
    encoding = args.encoding
    period = convert_to_century(args.period)
    training_data = args.training_data
    sort = args.sort
    document_type = args.document_type
    files = collect_input_files(
        args.path, period, sort=sort, document_type=document_type
    )
    display_context = args.display_context
    classical_ch = args.classical_ch
    exclude_ch = False

    # No input files found
    if not files:
        print(
            f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)"
        )
        return

    # Print loop

    rules = build_rules(training_data=training_data, period=period)
    lexicon = load_lemma_lexicon(period, training_data=training_data)

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

    output_path = Path.cwd() / "results" / "output.conllu"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out:

        for file_path in tqdm(files, desc="Processing files"):
            tokens = attach_yale(
                parse_file(
                    file_path, encoding=encoding, display_context=display_context
                ),
                classical_ch,
                exclude_ch,
            )

            tokens = tag_tokens(
                tokens,
                rules,
                lexicon=lexicon,
                rest_set=rest_set,
                infl_decomp=infl_decomp,
                pos_to_allowed_morphemes=pos_to_allowed_morphemes,
            )

            for source_id, group in groupby(tokens, key=lambda t: t.source_id):
                token_group = list(group)

                block = tokens_to_conllu(token_group, sent_id=source_id)

                print(f"{block}")

                out.write(block + "\n\n")


def run(args: CLIArgs) -> None:

    if args.corpus_list:
        run_corpus_list(args)
        return

    if args.classical_ch:
        print(
            "[INFO] All tokens including minimally-annotated classical Chinese texts are processed."
        )
    else:
        print(
            "[INFO] Tokens from minimally-annotated classical Chinese texts are now filtered out."
        )

    if args.exclude_ch:
        if run_print_corpus is None:
            print(
                "[INFO] exclude_ch mode is on. Any tokens containing Chinese characters will not be included in token analysis."
            )

    # Training mode

    if args.training_mode:
        run_train(args)
        return

    # Print corpus mode

    if args.print_corpus:
        print(
            "[INFO] print_corpus mode is on. Corpora will be printed with tagged morphemes based on the current training data."
        )
        run_print_corpus(args)
        return

    # ConLLU mode

    if args.export_conllu:
        print(
            "[INFO] export_conllu mode is on. A Universal-Dependencies analysis will be performed."
        )
        run_export_conllu(args)
        return

    run_search(args)


def main(argv: list[str] | None = None) -> None:
    args = parse_cli_args(argv)
    run(args)
