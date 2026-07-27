# src/midkrregextool/cli.py

from __future__ import annotations

import argparse  # To avoid positional arguments
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path  # is_file(), is_dir()

from midkrregextool.annotation import (
    annotate,
    annotation_priority,
    build_adjacent_contexts,
    load_infl_decomp_from_annotation,
    load_pos_to_allowed_morphemes_inventory_from_annotation,
    prompt_with_default,
)
from midkrregextool.model import Token
from midkrregextool.parser import (
    convert_to_century,
    get_info_from_letters,
    has_letters,
    letter_sort_key,
    parse_file,
    trimming_date,
)
from midkrregextool.report import maybe_save_hits, report_hits
from midkrregextool.search import search_tokens
from midkrregextool.tagger import (
    default_annotation_dir,
    load_bilstm_artifacts,
    load_lemma_lexicon,
    tag_tokens,
)
from midkrregextool.yale import attach_yale


@dataclass(frozen=True)
class CLIArgs:
    path: Path
    period: str | None
    model_parameter: str | None
    pattern: str | None
    purpose: str | None
    sort: str | None
    encoding: str = "utf-16"
    # display_context: bool = False
    corpus_list: bool = False
    annotation_mode: bool = False
    annotation_data: Path | None = None
    classical_ch: bool = False
    token_repr: str | None = None
    exclude_ch: bool = False
    print_corpus: bool = False
    document_type: str | None = None
    chunk_start: str | None = None


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
        help="Regex pattern to search over Yale-romanized Korean texts. When used in annotation mode, only matching tokens are shown.",
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
    # p.add_argument(
    #     "--display-context",
    #     action="store_true",
    #     help="Enable a context-display function",
    # )
    p.add_argument(
        "--period", type=str, default=None, help="Filter by historical period"
    )
    p.add_argument(
        "--annotation-mode",
        action="store_true",
        help="Enable annotation mode (interactive labeling)",
    )
    p.add_argument(
        "--annotation-data",
        type=Path,
        default=None,
        help="Path to annotation data for suffix proposal generation",
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
        help="Select the token representation used for search or annotation.",
    )
    p.add_argument(
        "--classical-ch",
        action="store_true",
        help="Annotate or search also on classical Chinese texts minimally annotated with Korean",
    )
    p.add_argument(
        "--corpus-list",
        action="store_true",
        help="Print the full list of corpora.",
    )
    p.add_argument(
        "--exclude-ch",
        action="store_true",
        help="Exclude tokens with Chinese characters when for annotation or search",
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
        help="Annotate or search on a specific type of documents.",
    )
    p.add_argument(
        "--chunk-start",
        type=str,
        default=None,
        help="Annotate or search on a specific chunk, based on `source_id` field",
    )
    p.add_argument(
        "--model-parameter",
        type=str,
        default=None,
        choices=["c", "m"],
        help="Specify the model unit: 'c' for character-based or 'm' for model-based.",
    )

    return p


def parse_cli_args(args: list[str] | None) -> CLIArgs:

    if args is None:
        args = sys.argv[1:]

    parser = build_parser()
    ns = parser.parse_args(args)

    # If --path argument is not provided, set the current working directory as path
    path = ns.path if ns.path is not None else Path.cwd()

    annotation_mode = ns.annotation_mode

    if ns.chunk_start is not None and not annotation_mode:
        raise SystemExit(
            "[ERROR] --chunk-start field is activated only when --annotation-mode is on."
        )

    if ns.path is None:
        print(f"[INFO] No --path provided. Running on the working directory: {path}")

        if ns.chunk_start is not None:
            raise SystemExit(
                "[ERROR] --chunk-start field requires --path argument referring to the specific document."
            )

    else:
        path = ns.path

    # if ns.annotation-mode is None:
    # if ns.pattern is None: raise SystemExit("[Error] --pattern is required.")

    annotation_mode = ns.annotation_mode
    print_corpus = ns.print_corpus
    pattern = ns.pattern
    document_type = ns.document_type
    corpus_list = ns.corpus_list

    if document_type:
        print(
            f"[INFO] document_type has been set to `{document_type}.` Any subsequent steps will be operated only on {document_type} files."
        )
    else:
        print(
            "[INFO] document_type argument has not been provided. All the available files in the file path will be processed."
        )

    # Search mode requires --pattern
    if not (annotation_mode or print_corpus or corpus_list):
        if pattern is None:
            raise SystemExit(
                "[ERROR] --pattern is required unless --annotation-mode is set."
            )

    annotation_data: Path | None = None

    if ns.annotation_data is not None:
        annotation_data = Path(ns.annotation_data)

        if not annotation_data.is_absolute():
            repo_root = Path(__file__).resolve().parents[2]
            annotation_data = (repo_root / annotation_data).resolve()
        else:
            annotation_data = annotation_data.resolve()

    # If --annotation-data argument is not provided, set the default annotation file directory as annotation_data

    else:
        annotation_data = default_annotation_dir()
        print(
            f"[INFO] No --annotation-data provided. Using the files in the default annotation file directory: {annotation_data}"
        )

    # Guard clause: no --period; individual file as --path

    if path.is_file() and ns.period is None:
        root = ET.parse(path).getroot()

        published_year = (
            root.findtext(".//teiHeader//titleStmt//date") or root.findtext(".//date")
        ).strip()
        published_year = (published_year or "").strip()

        period = convert_to_century(published_year)

    elif ns.period is not None:
        period = ns.period

    else:
        period = ""

    # Guard: annotation data requires explicit period
    if ns.annotation_data is not None and period == "":
        raise SystemExit("[ERROR] --annotation-data requires --period.")

    # Guard for unspecified model_parameter argument.

    model_parameter = ns.model_parameter

    while not model_parameter and not corpus_list:
        model_parameter = input(
            "Specify the model unit: 'c' for character-based or 'm' for model-based: "
        )

        if model_parameter not in ["m", "c"]:
            model_parameter = None

    # Set the default value of repr: "yale" for annotation-mode and "tagged_form" for search-mode
    if (annotation_mode) and (ns.token_repr is None):
        token_repr = "yale"
    elif (not annotation_mode) and (ns.token_repr) is None:
        token_repr = "tagged_form"
    else:
        token_repr = ns.token_repr

    return CLIArgs(
        path,
        period,
        model_parameter,
        pattern=ns.pattern,
        purpose=ns.purpose,
        encoding=ns.encoding,
        # display_context=ns.display_context,
        corpus_list=ns.corpus_list,
        sort=ns.sort,
        annotation_mode=ns.annotation_mode,
        classical_ch=ns.classical_ch,
        annotation_data=annotation_data,
        token_repr=token_repr,
        exclude_ch=ns.exclude_ch,
        print_corpus=ns.print_corpus,
        document_type=ns.document_type,
        chunk_start=ns.chunk_start,
    )


# Input-file-collecting function


def _century_sort_key(century: int | str | None) -> tuple:
    return (0, century) if isinstance(century, int) else (1, str(century))


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

    sorting_key: dict[Path, tuple] = {}

    # period filtering: XML metadata(date) needed

    for file in path.rglob("*.xml"):
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError as e:
            print("[ERROR] Malformed XML file skipped:")
            print(f"        file = {file}")
            print(f"        error = {e}")
            continue

        is_letter_file = has_letters(root)

        # Document selecting field

        if document_type == "letter":
            if not is_letter_file:
                continue
        elif document_type == "non-letter":
            if is_letter_file:
                continue

        if is_letter_file:
            # Letter XML: filtering/sorting unit is <letter>, not the file.
            # get_info_from_letters() normalizes all the structural variants.
            letters = get_info_from_letters(root)

            if corpus_list:
                matched_files.append(file)
                candidates = letters
            else:
                candidates = [
                    info for info in letters if info.published_century == period
                ]
                if not candidates:
                    continue
                matched_files.append(file)

            if sort is not None:
                letter_keys = [letter_sort_key(info) for info in candidates]
                if sort == "published_century":
                    sorting_key[file] = (
                        min(k[0] for k in letter_keys) if letter_keys else (1, "None")
                    )
                else:  # published_year
                    sorting_key[file] = (
                        min(letter_keys) if letter_keys else ((1, "None"), (1, "None"))
                    )

            continue

        raw_published_year = (
            root.findtext(".//teiHeader//titleStmt//date")
            or root.findtext(".//date")
            or ""
        ).strip()

        if not raw_published_year:

            print("[WARN] No <date> found; skipped:")
            print(f"       file = {file}")
            continue

        published_year = trimming_date(raw_published_year)

        if not published_year:
            published_year = raw_published_year

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
                sorting_key[file] = (
                    _century_sort_key(published_century),
                    (0, published_year)
                    if isinstance(published_year, int)
                    else (1, str(published_year)),
                )
            elif sort == "published_century":
                sorting_key[file] = _century_sort_key(published_century)

    if sort is not None:
        return sorted(matched_files, key=lambda f: sorting_key[f])

    return sorted(matched_files)


def collect_available_sent_types(
    files: list[Path], encoding: str, period: int | None = None
) -> set[str]:
    sent_types: set[str] = set()
    for file_path in files:
        tokens = parse_file(file_path, encoding=encoding, period=period)
        sent_types.update(t.sent_type for t in tokens)
    return sent_types


def prompt_sent_types(available_sent_types: set[str]) -> list[str]:
    displayable = sorted(t for t in available_sent_types if t is not None)
    if None in available_sent_types:
        print(
            "[WARN] Some tokens have no sent_type (None) and will be excluded unless explicitly handled."
        )

    print(f"[INFO]: Available sentence types: {displayable}")
    existing = ", ".join(displayable)
    chosen = prompt_with_default(
        "Please provide the sent_type you want to process, separated with commas: ",
        existing,
    ).strip()
    return chosen.split(", ")


def filter_chunks_by_sent_type(
    tokens: list[Token],
    chosen_sent_types: list[str],
    *,
    chunk_start: str | None = None,
) -> list[list[Token]]:
    chunks: list[list[Token]] = []
    current: list[Token] = []

    for token in tokens:
        if token.sent_type in chosen_sent_types:
            current.append(token)
        elif current:
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)

    if chunk_start is not None:
        chunks = [c for c in chunks if chunk_start in c[0].source_id]

    return chunks


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

    header = (
        "Directory\tFile name\tLetter #\tCentury\tTitle\tVolume\tYear\tRaw Year\t"
        "Author\tSender\tReceiver"
    )

    # (sort_key, line) pairs; sort_key is None when --sort is not requested,
    # in which case rows are emitted in `files` order (file order, then
    # document order of <letter> within a file).
    rows: list[tuple[tuple | None, str]] = []

    for file_path in files:
        root = ET.parse(file_path).getroot()

        title = (
            root.findtext(".//teiHeader//titleStmt//title")
            or root.findtext(".//title")
            or ""
        ).strip()

        volume = root.find(".//teiHeader//titleStmt//volume")
        volume_n = volume.get("n") if volume is not None else ""

        author = root.findtext(".//teiHeader//titleStmt//author") or ""

        relative_path = file_path.relative_to(Path.cwd())
        m = re.match(r"(^.+?\\)([^\\]+?xml)$", str(relative_path))
        directory_name = m.group(1)
        file_name = m.group(2)

        if has_letters(root):
            # One row per <letter>; a single file can contribute rows from
            # multiple centuries.
            letters = get_info_from_letters(root)
            if not corpus_list:
                letters = [
                    info for info in letters if info.published_century == period
                ]

            for info in letters:
                fields = [
                    directory_name,
                    file_name,
                    info.letter_n,
                    str(info.published_century),
                    title,
                    volume_n,
                    str(info.published_year),
                    info.raw_year,
                    author,
                    info.sender,
                    info.receiver,
                ]
                rows.append((letter_sort_key(info), "\t".join(fields)))

        else:
            raw_published_year = (
                root.findtext(".//teiHeader//titleStmt//date")
                or root.findtext(".//date")
                or ""
            ).strip()

            published_year = trimming_date(raw_published_year)
            if not published_year:
                published_year = raw_published_year

            published_century = convert_to_century(published_year)

            key = (
                _century_sort_key(published_century),
                (0, published_year)
                if isinstance(published_year, int)
                else (1, str(published_year)),
            )

            fields = [
                directory_name,
                file_name,
                "",
                str(published_century),
                title,
                volume_n,
                str(published_year),
                raw_published_year,
                author,
                "",
                "",
            ]
            rows.append((key, "\t".join(fields)))

    if sort == "published_year":
        rows.sort(key=lambda r: r[0])
    elif sort == "published_century":
        rows.sort(key=lambda r: r[0][0])

    with open("corpus_list.txt", "w", encoding="utf-8") as out:
        out.write(header + "\n")
        for _, line in rows:
            print(line)
            out.write(line + "\n")


def run_annotation(args: CLIArgs) -> None:

    # annotation-only mode

    # Assigning objects to the arguments
    encoding = args.encoding
    period = convert_to_century(args.period)
    annotation_data = args.annotation_data
    sort = args.sort
    document_type = args.document_type
    pattern = args.pattern
    token_repr = args.token_repr
    # display_context = True
    classical_ch = args.classical_ch
    exclude_ch = args.exclude_ch
    chunk_start = args.chunk_start
    model_parameter = args.model_parameter

    VALID = [15, 16, 17, 18, 19, 20]  # Valid centuries for period filtering

    # Guard clause: annotation mode requires an explicit period argument

    while period is None:

        raw = input(
            "[INFO] annotation mode requires period filtering. Enter 15-20: "
        ).strip()
        period = convert_to_century(raw)

        while period not in VALID:
            raw = input(
                "[ERROR] Please enter a valid period (e.g., 15 for 15th century): "
            ).strip()
            period = convert_to_century(raw)

    lexicon = load_lemma_lexicon(period, annotation_data=annotation_data)
    model, vocab = load_bilstm_artifacts(model_parameter=model_parameter)

    t0 = time.perf_counter()
    files = collect_input_files(
        args.path, period, sort=sort, document_type=document_type
    )
    print(f"[TIMING] collect_input_files: {time.perf_counter() - t0:.3f}s")

    # Period argument has been provided and validated.

    # Guard clause: no files to annotate on -> exit early
    if not files:
        print(f"[INFO] No supported files found for period={period}c")
        print("[INFO] annotation aborted.")
        return

    # Collect tokens.
    all_tokens = []
    all_chunks: list[list[Token]] = []  # anno chunks, built per file
    bigram_hits = []  # Collect per-file bigram hits only when needed.

    rx = None
    is_bigram = False

    if pattern:
        if token_repr == "tagged_form":
            print(
                f"[INFO] annotation-mode pattern filter enabled: {pattern!r} (matched against token.tagged_form)."
            )
        rx = re.compile(pattern)
        is_bigram = (
            " " in pattern
        )  # If pattern has a space, annotation unit becomes (Token, Token)

    # Load
    infl_decomp = None
    pos_to_allowed_morphemes: dict[str, set[str]] = {}

    if annotation_data is not None:
        infl_decomp = load_infl_decomp_from_annotation(
            annotation_data / f"annotation_{period}c.jsonl"
        )
        pos_to_allowed_morphemes = (
            load_pos_to_allowed_morphemes_inventory_from_annotation(
                annotation_data, period
            )
        )

    chosen_sent_types = prompt_sent_types(
        collect_available_sent_types(files, encoding, period)
    )

    t_tag = time.perf_counter()
    for file_path in files:

        tokens = attach_yale(
            parse_file(file_path, encoding=encoding, period=period),
            classical_ch,
            exclude_ch,
        )

        tokens = tag_tokens(
            tokens,
            lexicon=lexicon,
            infl_decomp=infl_decomp,
            pos_to_allowed_morphemes=pos_to_allowed_morphemes,
            model=model,
            vocab=vocab,
            model_parameter=model_parameter,
        )

        # 각각의 sent_type마다 독립된 처리 가능하도록 sent_type을 key로 하고 해당 token의 오름차순으로 정렬된 source_id 값과 거기에 대응하는 context로 이루어진 dict를 값으로 하는 dict context_by_sent_type

        if chosen_sent_types is None:
            available = {t.sent_type for t in tokens}
            chosen_sent_types = prompt_sent_types(available)

        all_tokens.extend(tokens)

        all_chunks.extend(
            filter_chunks_by_sent_type(
                tokens, chosen_sent_types, chunk_start=chunk_start
            )
        )

        if pattern and is_bigram:
            bigram_hits.extend(search_tokens(tokens, pattern, token_repr))

    print(f"[TIMING] tag_tokens {len(files)} files: {time.perf_counter() - t_tag:.3f}s")

    sent_types = {token.sent_type for token in all_tokens}

    context_by_sent_type = {
        sent_type: {
            token.source_id: token.context
            for token in all_tokens
            if token.sent_type == sent_type
        }
        for sent_type in sent_types
    }

    sent_type_by_source_id = {token.source_id: token.sent_type for token in all_tokens}

    t_build_adjacent_context = time.perf_counter()
    adjacent_contexts = build_adjacent_contexts(
        all_tokens, context_by_sent_type, sent_type_by_source_id
    )
    print(
        f"[TIMING] build_adjacent_contexts {file_path.name}: {time.perf_counter() - t_build_adjacent_context:.3f}s"
    )

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

    # Decide annotation targets after collecting everything.
    # Non-bigram targets are chunks (list[list[Token]]) so that anno-sentence
    # context/order is preserved for annotate(); a --pattern filter (without
    # bigram) still selects individual tokens, each wrapped as its own
    # single-token chunk.
    t_select = time.perf_counter()
    if pattern and is_bigram:
        annotate_targets = bigram_hits
    elif pattern:
        if token_repr == "tagged_form":
            annotate_targets = [
                [t] for t in all_tokens if t.tagged_form and rx.search(t.tagged_form)
            ]
        else:
            annotate_targets = [[t] for t in all_tokens if t.yale and rx.search(t.yale)]
    else:
        annotate_targets = all_chunks
    print(f"[TIMING] target selection: {time.perf_counter() - t_select:.3f}s")

    known_rests = set(infl_decomp) if infl_decomp else set()

    t_sort = time.perf_counter()
    if pattern and is_bigram:
        # annotation_priority() operates on a single Token, not a (Token, Token)
        # bigram pair, so bigram order is left as annotate() finds it.
        pass
    else:
        # Order chunks (not the tokens within them) by their most-urgent
        # token, so chunk-internal context order is never disturbed.
        annotate_targets = sorted(
            annotate_targets,
            key=lambda chunk: min(
                (
                    annotation_priority(tok, lexicon=lexicon, known_rests=known_rests)
                    for tok in chunk
                ),
                default=(3, ""),
            ),
        )
    print(f"[TIMING] target sorting: {time.perf_counter() - t_sort:.3f}s")

    t_annotate = time.perf_counter()
    annotate(
        annotate_targets,
        period,
        adjacent_contexts,
        annotation_data=annotation_data,
        lexicon=lexicon,
        token_lookup=token_lookup,
    )
    print(f"[TIMING] annotate(): {time.perf_counter() - t_annotate:.3f}s")

    return


def run_search(args: CLIArgs) -> None:

    # search mode

    # Assigning objects to arguments
    pattern = args.pattern
    purpose = args.purpose
    encoding = args.encoding
    # display_context = args.display_context
    period = convert_to_century(args.period)
    model_parameter = args.model_parameter
    annotation_data = args.annotation_data
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

    lexicon = load_lemma_lexicon(period, annotation_data=annotation_data)
    model, vocab = load_bilstm_artifacts(model_parameter=model_parameter)

    within_result_search = "n"

    while True:
        bigram_flag = " " in pattern

        # Recollect input files when period filter is changed

        if period != last_period:

            files = collect_input_files(
                args.path, period, sort=sort, document_type=document_type
            )
            last_period = period
            lexicon = load_lemma_lexicon(period, annotation_data=annotation_data)
            model, vocab = load_bilstm_artifacts(model_parameter=model_parameter)

            if not files:
                print(f"[INFO] No supported files found for period={period}.")
                continue

        # Initial search or non-within-previous-results search
        if within_result_search == "n":

            all_hits = []

            infl_decomp = None
            pos_to_allowed_morphemes: dict[str, set[str]] = {}

            if annotation_data is not None:
                infl_decomp = load_infl_decomp_from_annotation(
                    annotation_data / f"annotation_{period}c.jsonl"
                )
                pos_to_allowed_morphemes = (
                    load_pos_to_allowed_morphemes_inventory_from_annotation(
                        annotation_data, period
                    )
                )

            for file_path in files:
                tokens = attach_yale(
                    parse_file(file_path, encoding=encoding, period=period),
                    classical_ch,
                    exclude_ch,
                )

                tokens = tag_tokens(
                    tokens,
                    lexicon=lexicon,
                    infl_decomp=infl_decomp,
                    pos_to_allowed_morphemes=pos_to_allowed_morphemes,
                    model=model,
                    vocab=vocab,
                    model_parameter=model_parameter,
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
    annotation_data = args.annotation_data
    sort = args.sort
    document_type = args.document_type
    files = collect_input_files(
        args.path, period, sort=sort, document_type=document_type
    )
    # display_context = args.display_context
    classical_ch = args.classical_ch
    exclude_ch = False
    model_parameter = args.model_parameter

    # No input files found
    if not files:
        print(
            f"[INFO] No supported files found under: {args.path} (expected: .txt, .xml)"
        )
        return

    # Print loop

    lexicon = load_lemma_lexicon(period, annotation_data=annotation_data)
    model, vocab = load_bilstm_artifacts(model_parameter=model_parameter)

    infl_decomp = None
    pos_to_allowed_morphemes: dict[str, set[str]] = {}

    if annotation_data is not None:
        infl_decomp = load_infl_decomp_from_annotation(
            annotation_data / f"annotation_{period}c.jsonl"
        )
        pos_to_allowed_morphemes = (
            load_pos_to_allowed_morphemes_inventory_from_annotation(
                annotation_data, period
            )
        )

    for file_path in files:
        tokens = attach_yale(
            parse_file(file_path, encoding=encoding, period=period),
            classical_ch,
            exclude_ch,
        )

        tokens = tag_tokens(
            tokens,
            lexicon=lexicon,
            infl_decomp=infl_decomp,
            pos_to_allowed_morphemes=pos_to_allowed_morphemes,
            model=model,
            vocab=vocab,
            model_parameter=model_parameter,
        )

        for token in tokens:
            print(f"{token.unicode_form}: {token.tagged_form}")


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

    # annotation mode

    if args.annotation_mode:
        run_annotation(args)
        return

    # Print corpus mode

    if args.print_corpus:
        print(
            "[INFO] print_corpus mode is on. Corpora will be printed with tagged morphemes based on the current annotation data."
        )
        run_print_corpus(args)
        return

    run_search(args)


def main(argv: list[str] | None = None) -> None:
    args = parse_cli_args(argv)
    run(args)
