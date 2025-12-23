# DEVLOG - MidKrRegexTool

## 2025-12-08

### What I did today
- Created the Github repository `MidKrRegexTool' and cloned it locally.
- Added `README.md`, `DEVLOG.md`, and basic documents under `docs/`.

### Decisions made
- DEVLOG will primarily be maintained in this repository (as a version-controlled file).
- Notion will be used as an external mirrored reference for DEVLOG, updated manually for now (automation can be added later).
- No additional normalization step is required for now, since the input corpus is already consistent in Hanyang PUA.
- The original Middle Korean corpus does not need to be stored inside this repository.
The tool will always take one or more external file paths as input.

### Next tasks
- Draft the overall architecture in `docs/design.md` (e.g., CLI tool structure, module layout).
- Decide on the initial module layout under `src/` (parsing, conversion, search, CLI)

## 2025-12-09

### Goal
- Draft the overall architecture in `docs/design.md`
- Decide on the initial module layout under `src/`

### What I actually did today
- Implemented the first functional version of `parser.py`, which:
    - detects source markers (e.g., `<釋詳3:1a>`),
    - performs whitespace-based tokenization on Middle Korean text encoded in Hanyang PUA,
    - handles both main text and note content (wrapped with [note] ... [/note] markers),
    and assign token-level metadata (`source_id`, `token_index`, `is_note`).
- Checked if `parser.py` works properly using `sample_sekpo_excerpt.txt`, confirming:
    - correct source marker detection and `token_index` reset,
    - correct identification of note vs. non-note segments,
    - and stable handling of Hanyang PUA characters.

### Decisions made
- Notes (`[note] ... [/note]`) are included in the token stream, distinguished only by an `is_note` flag.
- Automated tests (pytest) will be added after the Yale conversion and regex-based search modules are drafted.

### Next tasks
- Begin drafting the Yale conversion layer (`yale.py`) to fill the `yale` field of tokens.
- Draft `search.py`, which will search specific strings based on regex.
- Later: add `pytest`-based tests for parser behavior.

## 2025-12-10

### What I did today
- Improved `quick_check_parser.py` to make parser verification easier:
- Reviewed parser behavior with the sample excerpt and confirmed correct handling of:
    - source marker resets,
    - note vs. main text distinction,
    - token indexing logic.
- Add parser behavior documentation to `design.md`.

### Next tasks
- Begin drafting the Yale conversion module (`yale.py`)

## 2025-12-11

### What I did today
- Implemented `yale.py`
    - Used YaleKorean package (https://github.com/SeHaan/YaleKorean/)
- Connected the parser output to the Yale conversion module (`yale.py`).
- Verified the pipeline using `quick_check_parser.py`, confirming:
    - correct PUA -> Unicode -> Yale transformations,
    - consistent behavior for mixed hanja/PUA tokens,
    - Collected several post-processing rule candidates based on the observed ouput patterns. 

### Decisions made
- Yale conversion will be kept as a separate stage rather than integrated into the parser.
- Post-processing of Yale output will be handled later, after the search module is implemented.

### Next tasks
- Begin implementing `search.py`, which will support:
    - regex search over Yale forms,
    - extraction of matched tokens and their metadata,
- After search is stable, revisit and finalize the post-processing rules.

## 2025-12-12 (logged on 2025-12-15)

> Note: The following work was carried on December 12, 2025
> but is being committed and logged on December 15, 2025

### Work summary

- Implemented and experimented with a helper script (`quick_check_parser.py`).
- Explored how parsed tokens flow through:
    - file parsing (`parse_file`)
    - token objects (`Token`)
    - Yale romanization attachment (`attach_yale`)
    - regex-based search over `token.yale`
- Encountered significant complexity relative to the intended goal of a "quick" inspection script.

### Notes

- The helper script was helpful for checking whether the program runs as expected, but not helpful at all in terms of learning how to implement programs. 

## 2025-12-16

### Work summary

- Implemented `report.py`, which plays the following two key roles:
    1. Display search results
    2. Optionally save the results as a UTF-8 text file.
- Designed `report.py` so that only `report_hits` and `maybe_save_hits` are exposed as its public interface. 

### Next tasks

- Extend the module to support processing multiple files at once. 
- Add an optional `comment` field to the list of `Token` objects so that the researcher can keep track of what they intended to investigate with a given regex pattern.

## 2025-12-17

### Work summary

- Extended the regex search to **bigram searches**.
    - Bigram search is triggered when the user's regex pattern contains a **literal space character** (`" "`, as opposed to `\s`).
- Updated `search.py` so that:
    - monogram search returns `list[Token]`
    - bigram search returns `list[tuple[Token, Token]]`
- Updated `readme.md` to reflect the current search behavior and limitation.

### Example

- Monogram search:
```bash
python quick_check_parser.py --pattern "[^\s]+[ae]"
```
- Bigram search:
```bash
python quick_check_parser.py --pattern "[^\s]+[ae] is"
```

### Known limitations
- Bigram search results are not yet saved as a UTF-8 text file.
- The tool currently processes only a single input file at a time.

### Next tasks
- Extend the module to support processing multiple input files at once. 
- Add an optional `comment` field to the `Token` objects so that the researcher can keep track of the intended purpose of a given regex pattern.
- Implement `maybe_save_hits` support for bigram search results. 
    
## 2025-12-18

### What I did today 
- Implemented a batch function for regex searches 
- Implemented UTF-8 file output support for bigram search results
- Added UTF-16 (with UTF-8 fallback) support for input text files by modifying the file-opening logic in `parser.py`.

### What to do next 
- Needs to improve the file-saving function to support UTF-16 output. 
- Implement a full CLI interface (beyond `quick_check_parser.py`)
- Reorganize argument handling and search-mode selection logic.
- Unify monogram and bigram search APIs to improve usability (schematically: monogram functions + bigram functions -> unified functions)

## 2025-12-19

### What I did today
- Started migrating `quick_check_parser.py` into the package as `cli.py`.
- Added a minimal CLI scaffold using `argparse` (`build_parser`) and a typed argument container (`CLIArgs`).
- Kept the existing search + report pipeline (batch accumulation and save-at-end behavior)
- Added a contemporary Korean charcters normalization function to combine Hangul characters properly.

### What to do next
- Finish wiring `build_parser()` into `main()` and remove the legacy `parse_args()` path.
- Clean up migration leftovers (typos, missing imports, unused preview/interactive code).
- Add a package entry point (`__main__.py`) for `python -m midkrregextool`.

## 2025-12-22

### What I did today
- Completed the migration from the helper script (`quick_check_parser.py`) to a full package-level CLI (`cli.py`).
- Finalized the CLI execution pipeline.
    - argument parsing via `argparse`
    - validation and normalization in `parse_cli_args`
    - batch-capable execution logic in `run`
- Added support for running the tool on the **working directory** when no `--path` argument is provided. 
- Enforced `--pattern` as a required argument with a clear error message.
- Verified that the tool runs correctly via the package entry point (`python -m midkrregextool`)
- Confirmed stable behavior for:
    - directory-based batch searches,
    - monogram and bigram regex patterns,
    - interactive saving of aggregated search results.

### Decisions made
- Argument validation (e.g., missing `--pattern`, default path resolution) is handled exclusively in `parse_cli_args`, keeping `run` free of input validation logic.
- When a directory is provided (explicitly or via working directory fallback), search results are accumulated and saved once at the end.
- the CLI now assumes that a valid regex pattern is always provided; graceful handling of missing patterns is treated as a CLI-level error, not a runtime condition.

### Next tasks
- Prepare the package for public installation via `pip`:
    - finalize `pyproject.toml`,
    - add console entry points if needed.
- Revise and expand `README.md` with:
    - installation instructions,
    - CLI usage examples,
    - sample outputs.

## 2025-12-23

### What I did today
- Added a minimal `pyproject.toml` to support standard Python packaging.
- Enabled editable installation (`pip install -e .`) for `MidKrRegexTool`.
- Confirmed that `python -m midkrregextool` works independently of CWD.
- Registered a console script entry point (`midkrregextool`).
- Finalized the `src/`-layout-compatible packaging configuration.

### Notes
- This change removes the previous reliance on `PYTHONPATH` / CWD-dependent execution.
- The project is now ready for pip-based usage and future PyPI distribution.