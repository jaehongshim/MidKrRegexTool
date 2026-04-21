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

## 2026-04-15

### What I did today
- Support `exclude_ch` mode to improve efficency
  - When `exclude_ch` mode is on, only tokens with Chinese characters are excluded from the further pipeline. 
- Support a tagged-corpus print function to overview morpheme-tagging performance.
  - To be developed further.