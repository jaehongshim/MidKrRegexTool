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

## 2026-01-26

### What I did today
- Improved `parse_xml_file` to detect the volume information in a given file and incorporate it into `doc_name`.

## 2026-01-27

### What I did today
- Included the published year of a given source to `source_id` for XML files.
- Implemented an interactive training pipeline for morphological tagging.
  - Added a `train()` routine that presents candidate analyses and records gold labels.
  - Introduced period-specific training data files (e.g. `training_15c.jsonl`).
- Initiated `candidate_generator()` and connected it to the training loop.
- Added support for reusing previously trained data:
  - Loaded gold analyses from existing training files.
  - Extended candidate rules with learned INFL suffixes.
- Created a dedicated `data/training` under the root repo to manage training corpora.
- Randomized the order of tokens during training to avoid biased data accumulation.
- Implemented a training-only mode when a `--pattern` argument is not provided. 
- Refactored the CLI control flow to separate search logic from the main dispatcher.
  - Added `run_search()` and moved the interactive search loop into it.
  - Simplified `run()` to act as a lightweight mode dispatcher (`run_train` vs. `run_search`).
- Fixed boolean flag parsing for training mode by switching `--training-mode` to `action="store_true"`.
- Added a `build_rules()` helper to construct tagging rules by merging base INFL suffixes with learned suffixes from training data (when `--training-data` and `--period` are provided).
- Tightened CLI validation so that `--pattern` is required unless `--training-mode` is enabled.
- Expanded `collect_input_files()` to include `.txt` files even when no period filter is given, while keeping XML-only period filtering based on `<date>` metadata.

## 2026-01-31

### What I did today
- Implemented `--sort` argument to control the ordering of input files.
- Added support for period-based sorting (`--sort published_year`) for XML files using metadata dates.

## 2026-02-01

### What I did today
- Added a dedicated candidate-mining mode to the CLI
  - Introduced `--candidate-mining {lemma, suffix}` as a first-class execution mode.
  - Implemented `run_candidate_mining()` as a top-level CLI workflow, replacing the former debug-only logic.
  - Candidate-mining now runs independently from search and training.
- Reorganized CLI execution logic around three explicit modes
  - Search mode: requires `--pattern`
  - Training mode: allows running without `--pattern`
  - Candidate-mining mode: allows running without `--pattern` (with `pattern` optionally reused as a suffix anchor).
  - Updated `parse_cli_args()` accordingly so that `--pattern` is required *only* in search mode.
- Removed legacy debug scaffolding and consolidated it into a reusable workflow
- Stabilized the candidate-mining execution path
- Extablished a clear roadmap for further refactoring

## 2026-02-05

### Summary
Implemented morph-aware search infrastructure on top of the existing coarse (LEM/INFL) tagger, and improved training/search usability.

### Training mode
- Extended training data format to optionally store morph-level analyses (`gold_morph`) alongside coarse `gold`.
- Allowed manual input of full morph strings (e.g. `si/HON-li/FUT-le/IPFV-la/DECL`) in training mode.
- Normalized morph-level input to coarse `gold` + `gold_morph` at save time.
- Ensured training mode can be restricted to tokens matching a regex pattern via `--pattern`.

### Tagging
- Tokens are always assigned a coarse `tagged_form`.
- If morph analyses exist in training data, corresponding tokens are enriched with:
  - `token.morph_str` (full morph string)
  - `token.morphs` (parsed list of `(form, tag)` pairs)

### Search
- Search now prefers `token.morph_str` when available, falling back to `tagged_form`.
- Added `matched_part` attribute to tokens to store the exact regex match.
- Search results display matched substrings explicitly.

### Reporting
- Search output now includes:
  - `[TAGGED-FORM]`
  - `[MORPH-STR]` (when available)
  - `[MATCHED-PART]`
  - `[CONTEXT]`

### Notes
- No attempt was made to auto-generate morph candidates during training yet.
- Current changes focus on infrastructure and correctness, not coverage.

## 2026-02-08

### What I did today
- Implemented a bigram training function.

### What to do next
- Support an interactive "active training" entry mode for adding gold annotations from the CLI.

## 2026-02-12

### What I did today
- Rename attributes in the `Token` class:
  - `tagged_form` -> `coarse_form`
  - `morph_str` -> `tagged_form`
- Add a `token-repr` argument to allow the user to select the token representation used in both search and training modes.  
  - If `token-repr` is not provided, "yale" is used as the default for training mode and "tagged_form" for search mode.

## 2026-02-23

### What I did today
- Temporarily disabled the `candidate-mining` module to simplify the pipeline.
- Separated training logic into a new `training.py`, simplifying `tagger.py` and clarifying module responsibilities.
- Reduced false positives and false negatives in stem-suffix boundary detection.
  - Boundary evaluation is now performed **only when both the lemma and the suffix are attested** in the recorded lexicon and training files.
- Incorporated POS information provided during training into the existing lemma inventory to improve tagging accuracy. 
- Enabled optional POS output during search/training.
- Identified a limitation:
  - Negative prefixes are recorded separately in the training file, but prefix information is not currently reflected in tagging. -> Temporarily solved by an ad hoc solution.
  - Possible optimal solution: introduce a small, controlled prefix list and handle prefix annotation explicitly.

## 2026-02-24

### What I did today
- Renamed `displaycontext` -> `display-context` and converted it into a boolean flag for cleaner CLI behavior.
- Introduced an empty `rest_set()` fallback for cases where `--training-data` is not provided.
- Restructured the `lexicon` dictionary to support prefix annotation.
  - Legacy structure: {"mwotho":"V", "kwoksik":"N", ...}
  - Updated structure: {"mwotho":"mwot/NEG/PREFIX-ho/V", "kwoksik":"kwoksik/N"}
- Integrated jsonl training file lookup into `candidate_generator`.
  - Added `load_lemma_lexicon` support inside `candidate_generator`
- Enabled full training-from-scratch workflow.
- Refined `parse_gold_morph_to_coarse` function to correctly render coarse forms. 

### Detected issues
- The current lemma whitelist does not properly handle tokens with prefixes.
  - Temporary workaround: remove such tokens from the whitelist and delegate handling to the jsonl-based training lexicon. 
- Need a more efficient strategy for predicates with Sino-Korean (Chinese) roots.

## 2026-02-26

### Detected issue
- Classical Chinese segments (e.g., <sent type="main" lang="chi" page="04b" n="5">孟子ᅵ 對曰</sent>) do not need to be included in default search or training.
  - These texts are minimally annotated and irrelevant to the core Middle Korean analysis.
  - Example: <sent type="main" lang="chi" page="04b" n="5">孟子ᅵ 對曰</sent>

## 2026-02-27

### What I did today
- Excluded minimally annotated classical Chinese (`lang="chi"`) segments from search and training **by default**. 
  - Users must explicitly pass `--include-ch` to include such texts.  
  - Updated `attach_yale` in `yale.py`:
    - Tokens with `lang="chi"` are filtered out unless `--include-ch` argument is provided.
- Forced context display in training mode to ensure full visibility during training diagnostics.

## 2026-03-09

### What I did today
- Removed `gold` and `coarse_form` attributes entirely from the pipeline.
- Implemented candidate generation based on learned suffix decompositions (`infl_decomp`) and the lemma lexicon, enabling automatic suggestions of `gold_morph` candidates during training.
- Refactored training data loading so that suffix decompositions are derived directly from the current period-specific training file.
- Implemented an analysis coverage display in training mode.
- Improved training UI when tagging tokens containing Sino-Korean characters.
- Introduced context-sensitive tagging support for auxiliary verbs (based on preceding verb + -a/e form).

## 2026-03-11

### What I did today
- Supported searching phonologically reduced form, if relevant underlying forms are trained by the user. 

## 2026-03-26

## 2026-03-25 (committed on 2026-03-26)

### What I did today
- Introduced split-point based search in `training_priority()` to eliminate full lexicon/rest scans.
- Removed redundant training data loading in `run_train()` (reused `rest_set` instead of reloading).
- Added timing instrumentation to training pipeline:
  - file collection
  - parsing + Yale attachment
  - tagging
  - target selection
  - sorting
  - training loop
- Implemented candidate caching in `train()`:
  - cache key based on `(yale, aux_context)`
  - avoided repeated calls to `candidate_generator()` for identical inputs
- Built a minimal test script (`test_candidate_generator.py`) to verify candidate equivalence before/after refactoring.

### Performance note
- Current bottleneck is `tag_tokens`, taking approximately **2 minutes 30 seconds** during training.

### Why this matters
- Eliminates major sources of repeated computation in training mode.
- Establishs measurement points to identify real bottlenecks.
- Ensures all optimizations preserve original candidate generation behavior.

### Notes
- No linguistic behavior was changed.
- All optimizations are strictly structural (performance-oriented).

## 2026-03-28

### What I did today
- Fixed an issue where tokens not present in the lexicon were incorrectly tagged as /LEM.
	- Debugging strategy:
		- Inspected all outputs returned by `analyze_yale`.

	- Issue 1: Misanalysis of Sino-Korean tokens containing Roman letters
		- Some tokens containing Hanja + Roman letters were incorrectly analyzed as /N.CH/LEM.

		- Cause:
			- These tokens should have been matched by `m2`, but some failed to match. 
			- `m2` was intended to match C+N+.
			- Tokens not matched by `m1` or `m2` fall back to "/N.CH/LEM".
		- Problem:
			- Some Chinese characters in the corpus are not covered by the predefined Hanja filter.
			- -> These tokens failed to match `m2`.
			- -> These tokens fall back to "/N.CH/LEM".
		
	- Fix:
		- Observed that all intended `m2` targets end with Roman letters.
		- Updated filtering condition:
			- `^(.+?)([\.A-Za-z]+)$`
		- This captures all tokens ending in Roman letters as `m2`.

	- Result:
		- Only pure Hanja tokens (no Roman letters) fall back to elsewhere. 
		- Visual inspection suggests expected behavior is carried on. 

- Issue 2: Incorrect fallback behavior
	- Cause:
		- Likely inherited from legacy code
	- Fix:
		- Removed the problematic final fallback logic from `analyze_yale()`
		- Verified outputs under the current pipeline assumptions.

- Excluded tokens with `type="dharani"` from both training and search targets. 
- Refined fallback behavior for unanalyzable tokens:

	- If neither stem nor suffix is analyzable:
		- Assign "NO-TAGGED-FORM" to `tagged_form`

	- If stem is analyzable but suffix is not found in `infl_decomp` with the given stem:
		- Preserve the output of `analyze_yale()` as being assgined to `tagged_form`

## 2026-03-29

### What I did today
- Expand look-up function for a more precise tagging function. 
	- Tokens now look up not only previous tokens but also following tokens (Test required)


## 2026-04-15

### What I did today
- Support `exclude_ch` mode to improve efficency
  - When `exclude_ch` mode is on, only tokens with Chinese characters are excluded from the further pipeline. 
- Support a tagged-corpus print function to overview morpheme-tagging performance.
  - To be developed further.

## 2026-04-21

### What I did today
- Improved monogram training mode to skip tokens that are already fully parseable from known data.
  - Added `has_known_parse()` in `training.py`:
    - Returns `True` if a token's Yale form can be split into a lexicon stem + a known `infl_decomp` suffix, or vice versa.
    - Checks only learned suffix decompositions (`infl_decomp`), not the base inflectional suffix rules — avoiding over-confident skips.
  - In the monogram training loop, tokens that pass `has_known_parse` are skipped before the candidate prompt is shown.
  - Bigram training loop is unchanged for now; criteria for skipping bigrams require further consideration.

### Design note
- The motivation: tokens like `듣ᄌᆞᄫᆞ시고` (tut/V + coWosikwo suffix) were surfacing as training candidates even though both components existed in the training data. The fix ensures that only genuinely ambiguous or unknown tokens reach the annotation prompt.
- Bigram skip criteria are deferred: the appropriate definition of a "known" bigram depends on what analytic constructions are worth training, which has not yet been decided.

## 2026-04-26

### What I did today
- Support specifying the document type via --document-type argument.
- Improve xml parsing function
  - There was a bug in which vernacular letter files were filtered from analysis in a wholesale way. 
  - The problem stemmed from `analyze_yale` function's Classical Chinese-filtering line where tokens without `lang` attribute are completely filtered out.  

## 2026-05-08

### What I did today
- Develop a function to print the list of corpus

## 2026-06-10

### What I did today
- Try to integrate the Universal Dependencies framework

## 2026-07-12

### 한 일

- 새 브랜치를 파기 전에 `universal-dependencies`의 working tree를 정리(커밋)해둠
- `tagger.py` 재점검: 지금은 토큰마다 후보 하나만 고르고 나머지는 버리는 구조.
  BiLSTM 기반 disambiguation을 적용하려면 이 구조부터 바꿔야 함
- 브랜치 로드맵 정리:
  - `tagger-candidates`(main에서 새로 분기) — `tagger.py`가 후보를 전부
    노출하도록 리팩토링
  - 완료되면 `main`에 merge
  - `universal-dependencies`는 그 뒤에 `main`을 merge해서 리팩토링 결과를 받아옴
  - `bilstm-disambiguation`(갱신된 `main`에서 새로 분기)에서 BiLSTM 작업 시작
  - 두 브랜치 모두 리팩토링된 `tagger.py` 위에 올라간 뒤에는 서로 독립적으로 진행
- `tagger-candidates` 브랜치 생성

- `infl_suffixes.txt`, `lemma_whitelist.txt` 재평가
  - 둘 다 손으로 되는대로 적어둔 불완전한 placeholder였지, 신뢰할 수 있는
    언어학적 참고자료가 아니었음. 특히 `infl_suffixes.txt`는 형태소 배열
    제약이 전혀 없는 원자 단위 목록이라, 이걸 그대로 쓰는 코드 경로는
    구조적으로 overgeneration에 취약함
  - 16~18세기 구간은 이미 파일 내용이 비어있는 상태로도 도구가 멀쩡히
    돌아간다는 걸 실증적으로 확인 — `rest_set`(training jsonl 기반)이
    이미 같은 역할을 더 나은 형태로 대신하고 있었기 때문
  - 결정: 두 파일 다 삭제. 이건 코드만 봐서 판단할 수 있는 게 아니라,
    코퍼스에 대한 도메인 지식에 기반한 내 판단

- 월~화 계획 (수요일 오전 이상아 교수님 미팅 전)
  - 월: `tagger-candidates` 리뷰 + `main` merge만. BiLSTM은 손대지 않음
  - 화: `bilstm-disambiguation` 브랜치, 최소 동작 baseline 한 번 — 목표는
    "정확도"가 아니라 "에러 없이 한 바퀴 도는 것". 뭐가 나오든 수요일
    미팅에 그대로 들고 가기

- Claude Code로 기계적 리팩토링 실행 (판단은 위에서 이미 끝났고, 이 커밋은
  그걸 코드에 반영한 것뿐 — atomic commit으로 분리)
  - `infl_suffixes`/`rules` 완전 제거. `infl_suffixes.txt` 삭제 이후
    `build_rules()`가 이미 무조건 `[]`를 반환하고 있어서, 그 아래 딸린
    파라미터와 분기(`analyze_yale()`의 `infl_suffixes` 관련 두 분기,
    `tag_tokens()`의 `rules` 파라미터, `candidate_generator()`의 fallback
    블록 3–4번)가 전부 죽은 코드였음
  - `rest_set`을 `infl_decomp`으로 통합. 둘 다 같은 training jsonl의
    `gold_morph` 필드에서 동일한 파싱 로직으로 만들어지고 있었음
    (`load_rest_surfaces_from_training()`이 `load_infl_decomp_from_training()`의
    키 생성 로직을 그대로 중복). `analyze_yale()`의 `suffix in rest_set`은
    `suffix in infl_decomp`과 동치라서(dict 멤버십 검사는 키만 봄) `rest_set`은
    중복이었음
  - `tag_tokens()`를 실제 15세기 training 데이터로 돌려보고
    `test_candidate_generator.py`로 검증 완료

## 2026-07-13

### 한 일

- [x] `analyze_yale()` 리팩토링
  - `tagger.py`의 `analyze_yale()` 함수가 이미 매치된 lemma가 있어도 더 짧은 lemma로 분석될 수 있는지 검토하도록 리팩토링. 
    - `analyze_yale()`의 아웃풋 시그니처를 str에서 list[str]으로 변경
    - `analyze_yale()`의 시작 지점에 candidates = []로 초기화
    - 이전에 매치된 어형을 return 시키던 라인을 모두 candidates.append...로 교체
  - 가능한 모든 분석을 `tag_tokens()`가 뽑아낼 수 있도록 리팩토링해야 함. 
- [x] 커맨드 라인 인자 개선
  - `--training-data` 인자 관련 사용성 개선: `--training-data` 인자가 주어지지 않으면 기본 디렉토리로 리디렉트하도록 개선함. 
  - `--display-context` 인자 삭제: 기본적으로 context를 보이도록 함. 
- [x] `tag_tokens()` 리팩토링
- [x] `Token` 모델 리팩토링

## 2026-07-14

### 한 일

- 현 상황 진단
	- PyTorch가 활용할 수 있는 `형태 분석형 후보 목록` -- `정답` 매치가 필요함. 
	- 현재 트레이닝 JSONL 파일에는 토큰의 gold 어형이 있지만 각 토큰의 앞 뒤 맥락이 주어져 있지 않다는 문제가 있어 이를 먼저 해결.
- 중요 결정 사항: 
	- **BiLSTM 모델링 목적으로는 기존 트레이닝 파일 폐기 및 트레이닝 방식 변경**
	- training.py 수정 필요
		- sent type에 따른 단위별 트레이닝 가능하게 할 것
		- 청크는 랜덤화하되 각 청크 안에서는 모든 토큰을 순차적으로 트레이닝하게 할 것
		- 트레이닝 스키마 확장

- 트레이닝 파이프 라인 개편 (CLAUDE 이용)
	- [x] training_15c.jsonl 레거시 파일로 유지
	- [x] cii.py: anno 청크 선택 로직 추가
		<span class="note">나중에 anno가 아닌 다른 sent type도 고려할 가능성??</span>
	- [x] training.py의 train() 수정
		- [x] 청크를 입력으로 받도록 변경
			- [x] 특정 청크를 --chunk-start 인자로 받도록 추가
		- [x] random.shuffle(tokens) 제거
		- [x] 트레이닝 파일 스키마에 `source_id`, `token_index` 필드 추가
	- [x] 중복 트레이닝 방지 기준 변경
		- if token.unicode_form in token_gold -> (source_id, token_index) 기준
	- [x] training_priority() 정렬 로직 처리

- 실제 태깅으로 toy 데이터 만들기
	- [x] 추천된 청크 --training-mode로 태깅

- BiLSTM 학습 데이터 변환
	- [x] 학습 예시 뽑아내기
	- [x] 문자를 숫자로 바꾸기
	- [x] PyTorch Dataset으로 포장

- 모델과 학습
	- [x] BiLSTM 모델 뼈대
	- [x] 학습 루프 작성: **이해는 일단 포기**
	- [x] 테스트

## 2026-07-15

### 미팅 결과 할 일 

- `training` 관련 용어 수정: `annotation`으로
- `annotation` 파이프라인 개선
	- segmentation과 annotation 분리
- 다음 미팅까지 BiLSTM 구현 목표
	- 컨택스트가 주어졌을 때 후보 각각의 존재 확률을 구하는 방식으로 최적형 판단하게 구현.

## 2026-07-17

### 오늘 한 일

- `annotation` (`training`) 모듈 개선
	- [x] `training` 관련 용어 모두 `annotation`으로 수정
		- CLAUDE CODE에 CLAUDE.md만 수정하라고 말하기.
	- [x] `annotation` 절차 세분화해서 편의성 증진
		- `annotation.py` 모듈의 `prompt_gold`에서 segmentation (if ans == "")
		- [x] `_segmentation()` 함수
		- [x] `_labeling()` 함수
- annotation 진행

- 나중 과제: 파일이 path로 주어질 때 period 등 필요한 정보 안 주어져도 바로 뽑아쓸 수 있게 구현 필요

## 2026-07-18

### 오늘 한 일

- [x] `annotation.py`의 `prompt_gold()` 사용성 개선
  - `_segmentation()`의 출력 `parsed_forms`의 원소가 한자로 시작하면 사용자 인터페이스에 미리 plausible gold를 제시.
    
    - 예: 

      > parsed_form == 巖
      >
      > Please label 巖 with an appropriate label: 巖/N.CH/LEM <- 기본 제시

  - 현재 비슷한 기능을 수행하는 부분이 `tagger.py`의 `analyze_yale`에 있으므로 `tagger.py`에 이 부분을 전담하는 함수 `label_han()`을 구현
    - `candidate_generator()`에도 비슷한 부분이 있어 정리 필요할 수 있음. 

## 2026-07-19

### 오늘 한 일

- 유저 편의성 증진
  - [x] 개별 파일이 `--path`로 들어오면 `--period` 인자가 주어지지 않아도 그냥 모든 모드를 실행시킬 수 있도록 함.  
    - `parse_cli()` 초단부에서 `--path`가 개별 파일인 것으로 확인되면 강제로 `--period` 인자를 주는 방식

- [x] `sent type`을 토큰 메타데이터로 받아올 수 있게 `model.py`의 `Token` 자료형j 확장
  - [x] 이미 훈련한 데이터에 `sent_type` = "anno" 따위의 데이터 추가할 것

- `annotation.py` 확장
  - gold에 `sent_type` 필드 추가
  - `anno` 뿐 아니라 모든 sent type을 할 수 있게.
    - [x] `build_anno_chunks()` 함수 이름을 `sent_type_selection()`으로 변경 
    - [x] `cli.py`의 `sent_type_selection()` 초단에 해당 코퍼스의 `sent type`이 무엇이 있는지 모두 보여주고 분석 원하는 sent type 선택하게 하기. 
    - [x] annotation에 포함할 `sent_type` 선택하는 유저 인터페이스 추가

## 2026-07-22
### 오늘 한 일
- `tagger.py`에 bilstm 이용한 추론 함수 `predict_best_candidate()` 구현
  - [x] 함수 파이프라인 구현
  - [x] tag_tokens()의 기존 candidate 선택 라인 대체
    - [x] tag_tokens()의 input에 다음을 추가
      - model: CandidateScorer | None = None,
      - vocab: dict[str, int] | None = None,
    - [x] tag_tokens()의 기존 candidate selection line은 fallback으로 남겨 둠. 

## 2026-07-23

### 오늘 한 일

- gold file 관련
  - [x] gold file의 tagged_form이 모두 surface form에 기반하도록 업데이트
    - 괄호 포함하는 토큰 검색해서 수정
  - 현재 모델 트레이닝 시 context 정보가 직접적으로 들어가고 있지 않다는 문제가 있음. 
    - 앞 뒤 sent chunk를 gold에 정보로 넣어 이후 트레이닝 시 context가 필요하면 바로 활용할 수 있도록 확장
    - 지금까지 annotation한 토큰에 context 정보 넣을 수 있도록 확장 필요함.

      1. [x] annotate.py의 annotate()에서 저장 코드에 다음 필드를 추가.
        - "context": token.context
        - "prev_context": prev_context
        - "next_context": next_context

      2. [x] prev_context와 next_context 할당
        - 다음 정보를 기반으로 처리:
          - 현재 token_index
          - 현재 sent_type
        - 이전 컨텍스트와 다음 컨텍스트는 모두 **sent_type**이 같은 것 가운데
          **source_id**가 가장 가까운 것을 가져온다 (중간에 다른 sent_type이
          끼어 있어도 건너뛰고, 같은 sent_type 안에서만 가장 가까운 이웃을 찾음).
        - 구현 방식:
          - [x] 토큰에 태깅된 직후, sent_type별로 (그 sent_type에 속한 토큰만
                필터링된) source_id:token.context 사전을 담은
                context_by_sent_type 생성
          - [x] sent_type이 바뀔 때만 context_by_source_id / context_idx를
                새로 계산하고, 그 외에는 직전에 계산해둔 것을 재사용
                (재계산 여부와 무관하게, 매 토큰은 항상 처리된다)
          - [x] current_context_idx = context_idx.index(token.source_id)로
                현재 위치 확인
          - [x] prev_context, next_context는 서로 독립적으로 판단 —
                맨 처음 위치면 prev_context = None, 맨 마지막 위치면
                next_context = None, 그 외에는 각각
                context_idx[current_context_idx - 1] /
                context_idx[current_context_idx + 1]로 조회
          - [x] main과 anno 모두 동일한 방식(sent_type별 사전 + source_id 순서
                색인)으로 처리
          - [ ] lang까지 같이 걸러서 그룹 짓는 것은 아직 미반영 —
                지금은 sent_type만으로 그룹화 (다음 단계 과제)

      3. [x] 지금까지 한 annotation 파일에 context 정보(context/prev_context/
            next_context)를 소급 추가 -> Claude AI 활용

      4. [x] anno의 prev/next_context가 실제로는 인접하지 않은 경우까지
            연결되는 버그 수정
        - 문제: sent_type별로 필터링된 source_id 목록에서만 이웃을 찾다 보니,
          두 anno 문장 사이에 main 문장이 끼어 있어도(즉, 실제 원문 순서상
          서로 떨어져 있어도) "같은 sent_type 안에서 가장 가까운 이웃"으로
          잘못 연결되고 있었음.
        - 수정: sent_type == "anno"인 토큰에 한해서는, 전체 문서 순서
          (sent_type 무관, cli.py의 sent_type_by_source_id)상 바로 이전/다음
          source_id를 확인하고, 그 source_id도 sent_type == "anno"일 때만
          prev_context/next_context로 사용. main은 기존 방식 그대로 유지.
        - annotation_15c.jsonl의 기존 anno 항목(659개 중 655개)도 corpus
          원문(D:\Corpus\NIKL 소재 XML)을 다시 파싱해 소급 수정.

      4. [x] sent_type = "anno"일 경우 인접한 chunk만을 context로 참조하게 리팩토링.

## 2026-07-24

### 오늘 한 일

### 오늘 할 일
- BiLSTM 모듈 개선
  - [x] bilstm.py > build_annotated_examples() > annotated_example 확장
    - 목표: annotated_example에 prev_context, next_context를 추가
      - 선결 과제: prev_context와 next_context를 bilstm.py에서 참조할 수 있는 방안 마련
        - 지금은 prev_context와 next_context가 annotation.py > annotate()에서 할당되어 골드로 들어가기 때문에 bilstm 파이프라인에서 이를 직접 참조할 수 없음. 
        - 해결 방안:
          - [x] annotate.py > annotate()에서 prev_context와 next_context 및 current_context를 만드는 로직을 build_adjacent_contexts()로 함수화. 
            - 이 함수는 다음 입력을 필요로 함.
              - tokens
              - sent_type_by_source_id
              - context_by_source_id
            - 출력은 모든 토큰 각각의 source_id를 키로 하여 (sent_type, prev_context, current_context, next_context)를 값으로 하는 dictionary
            - 맨 끝단에서 다른 출전에서 나온 것들끼리 context로 잡는 것을 막을 수 있도록 guard clause 넣어줄 것. 
          - [x] source_id 만을 입력으로 받는 래퍼 함수 get_adjacent_context()도 함수화.
          - [x] cli.py에 맞추어 리팩토링
          - [x] sent_type_selection()을 prompt_sent_types()와 filter_chunks_by_sent_type()으로 분리. 

## 2026-07-27

### 오늘 한 일
- BiLSTM 모듈 개선
  - [x] 자소가 아닌 형태소 단위로 토큰화해서 encode할 수 있도록 refactoring
    - 실제 나오는 vocab 확인할 것
    - [x] build_morph_vocab() 구현
  - 기반하는 모델을 선택하도록 하는 model_parameter 도입
    - [x] 자소 단위(접두사 c_)와 형태소 단위(접두사 m_)로 각각 학습
    - [x] 자소 단위 모델을 쓸지 형태소 기반 모델을 쓸지 결정하도록 하는 인자 model_parameter 도입.
      - tagger.py > tag_tokens() > predict_best_candidate() > encode_string() 파이프라인에서 encode_string()이 model_parameter()를 필요로 함.
        - [x] cli.py에서 tag_tokens()에 model_parameter가 전달되어야 함.  
        - [x] predict_best_candidate()과 encode_string()에 model_parameter 인자 추가
        - encode_string()이 받는 vocab을 m_vocab으로 할지 c_vocab으로 할지 정해주는 분기
          - [x] load_bilstm_artifacts()에 model_parameter 분기

- [ ] 모델 성능 비교할 수 있도록 시각화

### 오늘 할 일

    - 트레이닝 결과 display 성능 형태로 대상 토큰 n개 중 몇 개가 제대로 되었는지
  - [ ] training 이루어진 것과 이루어지지 않은 것 사이 즉각 비교 가능하도록 구현

  - 중기:
    - 트레이닝을 한글 input으로 진행할 가능성
    - 트레이닝에 context 적절히 구현할 방법