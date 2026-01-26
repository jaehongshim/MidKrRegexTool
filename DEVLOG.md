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

## 2026-01-05  
*(work carried out roughly between 2025-12-24 and 2026-01-05, committed on 2026-01-05)*

### Work summary

- Introduced an initial **morphological tagging layer** (`tagger.py`) on top of the existing
  parser → Yale conversion pipeline.
- Extended the `Token` model with a `tagged_form` field to store morphologically annotated output.
- Implemented a **suffix-based lemma/inflection split** over Yale-romanized forms, designed as a
  preprocessing step prior to regex-based search.
- Added support for **externalized suffix management**:
  - inflectional suffixes are now loaded from a separate text file (`infl_suffixes.txt`),
    rather than being hard-coded.
- Implemented a **corpus-driven suffix discovery mechanism**:
  - suffix candidates are collected from tokens where inflectional parsing fails,
  - candidate suffixes are aggregated across all input files using a global `Counter`,
  - final proposals are generated once at the end of batch processing.
- Integrated the suffix discovery pipeline into the CLI execution flow,
  while keeping it clearly separated from the core search functionality.

### Design notes

- The suffix discovery logic is intentionally **non-destructive**:
  automatically proposed suffixes are *not* added to the active suffix list,
  but are instead intended for manual review and incremental refinement.
- Inflectional parsing currently relies on suffix matching heuristics;
  this is recognized as an intentionally incomplete baseline to be improved
  with lemma-aware and score-based decision rules in later iterations.

### Timeline / status

- This work spans several incremental development sessions following the
  stabilization of the package-level CLI (post-2025-12-23).
- All changes related to the tagging layer and suffix proposal mechanism
  are committed together in this update on **2026-01-05**.

### Next tasks

- Refine the inflectional parser to reduce false positives:
  - move from greedy suffix matching to candidate-based scoring,
  - incorporate lemma-level heuristics and/or lemma whitelists.
- Improve filtering of automatically proposed suffixes
  (e.g., minimum lemma quality, script boundaries, noise reduction).
- Decide how tagged forms should interact with downstream regex search
  (search over raw Yale vs. tagged representations).

  ## 2026-01-06

### What I did today
- Introduced a lemma whitelist mechanism to guide morphological analysis.
- Added `lemma_whitelist.txt` and implemented loading known lemmas as a `set`.
- Added support for consulting a lemma whitelist during tagging.
- Extended the analyzer to support han-aware lemma–inflection splits
  (e.g. Chinese character + verbalizer patterns).
- Refined lemma candidate collection by separating exploratory tools
  (lemma/suffix proposal) from the main tagging logic.
- Integrated lemma seed collection into the CLI as a debug-only workflow.

### Design decisions
- Lemma whitelist is introduced as an explicit external resource
  but its matching strategy is still under active development.
- Lemma/suffix proposal mechanisms are kept inspectable and non-automatic.
- Core tagging logic and exploratory diagnostics are explicitly separated.

### Notes
- Some whitelist-based matching strategies were explored and temporarily
  commented out during development; only the stable structure is recorded here.

## 2026-01-07

### What I did today
- Refactored `analyze_yale()` to make the decision order explicit (whitelist → han-aware rules → inflection suffix rules → fallback).
- Removed unintended `/INFL` tagging when the lemma exactly matches the input.
- Replaced unordered set-based lemma iteration with a length-sorted list to ensure deterministic and stable whitelist matching.
- As a result, improved both correctness and runtime stability of the tagging process.

### Notes
- Set the corpus directory path as an environment variable using `setx`, allowing access via `%midkr15c%` in `cmd`.

## 2026-01-08

### What I did today
- Tested the program with practical purposes.
- Came up with some additional features (described below)

## 2026-01-13

### What I did today
- Enabled multiple searches without restarting the program, using a `while True` loop with an Enter / `q` control flow.
- Implemented searching within existing search results by filtering the hit list from the previous search, supporting both monogram and bigram hits. 

### Next step
- Improve monogram search to correctly respect word-final boundaries.
- Add a context display option (`--displaycontext`) to show surrounding tokens of matched items. 
- Rename the `--comment` argument to `--purpose`, and allow adding an optional free-form comment when saving results.


## 2026-01-14

### What I did today
- Implement `--encoding` argument to support files with non-UTF-16 encodings.

## 2026-01-19

### What I did today
- Implemented XML parsing support and integrated it into the existing parsing pipeline.

### Next task
- Improve monogram search to correctly respect word-final boundaries.
- Add a context display option (`--displaycontext`) to show surrounding tokens of matched items. 
- Rename the `--comment` argument to `--purpose`, and allow adding an optional free-form comment when saving results.

## 2026-01-22

### What I did today
- Added a context display option (`--displaycontext`) to show the sentence-level context containing matched items.
  - When `--displaycontext` is enabled, the context is displayed with the matched token highlighted using brackets (`<<...>>`).
  - Context highlighting is implemented based on token indices, so that only the actual hit token is highlighted even when the same string appears multiple times.
- Added a period selection option (`--period`) as a date filter for corpus files.
  - XML files are filtered by extracting year information from `<date>` tags and converting it to centuries. 
  - Currently, searching over more than one century is not implemented.
- Rename the `--comment` argument to `--purpose`, allowing an optional free-form description to be attached when saving results.

## 2026-01-23

### What I did today
- Reassigned the `token_index` to be scoped to the part-level loop rather than the line-level loop in `parse_file` (`parser.py`) to ensure correct context display for matched items in TXT files.
- Updated the saving workflow so that results can be saved without terminating the search session.
- Added support for optional notes/comments for each search round.

## 2026-01-24

### What I did today
- **Started developing an automatic tagging function**
  - Initiated `feature/label-mode` branch

## 2026-01-25

### What I did today
- Introduced an interactive training pipeline for manual morphological annotation.
  - Implemented a `train()` function that presents candidate analyses per token and records gold selections in a JSONL file.
  - Training data are now saved separately by period (e.g., `training_15c.jsonl`) to prevent cross-period contamination.
- Refactored CLI logic to support training-mode interaction across multiple search rounds.
  - Period filtering is enforced in training mode and can be updated between rounds.
  - Tokens from all target files are aggregated before training to support batch annotation.
- Standardized period handling by normalizing user input to integer centuries internally and tagging outputs with a canonical `{period}c` format.
- Added scaffolding for a rule-based candidate generation framework.
  - `candidate_generator()` is currently a placeholder and will be extended to generate LEM/INFL split candidates based on suffix rules.

### Notes
- At this stage, lemma lists are intentionally not used in candidate generation to prioritize recall.
- Lemma-based filtering or weighting will be introduced in a later iteration once INFL segmentation is stabilized.


### Additional features to develop
- Improve user experience by typing bigram regex patterns in a more intuitive way
- Support morpheme tagging for bigrams.
- Improve handling of tokens where a Chinese character is followed by its phonetic realization.
- 모노그램 검색 시 단어 끝 경계가 검색에 반영되지 않는 문제 해결
- 입력이 unicode일 경우 pua를 제공하도록 프로그램 확장
- 아주 큰 문장에 태깅할 때 진행 상황 시각화 해서 보이기
- ~~Support multiple searches without reopening the program~~
- ~~Support searching within existing search results~~
- ~~Rename the `--comment` argument to `--purpose`, and allow adding an optional comment when saving results.~~ 
- ~~--displycontext 인수 지원하여 단어의 주변 환경 확인 가능하게 하기~~
- ~~path 인수 안 주면 current working directory에서 찾도록~~
- ~~새로 얻은 코퍼스 구조를 고려하여 큰 변개가 필요함~~
  - 구조화된 토큰: 문장 -> 문장 내 토큰
- Develop argument system for the NIKL corpora
  - ~~--period~~
  - --document-type
- The bigram-searching function has to be modified to ignore the hit if the first target is the last word of the context.

### Things to do
- Update `README.md` and additional documents