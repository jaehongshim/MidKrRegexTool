<!-- 2026. 01. 27. -->

# Roadmap: Pipeline-oriented Refactoring & Feature Expansion

## Overall goal
Gradually refactor the system into a clear, modular pipeline  
(**parse → romanize → tag → analyze/train → search → report**),  
while extending the morphological tagger to analyze internal structure of
inflectional morphology (beyond a flat `/INFL` label).

---

## Phase 1. CLI & Pipeline Stabilization (Infrastructure)
**Goal:** Make each execution mode correspond to a single, readable pipeline.

- Split `run()` into mode-specific pipelines:
  - `run_search`
  - `run_train`
  - `run_analyze` (successor of the legacy debug loop)
- Clarify mode semantics:
  - Training mode is triggered only when `--training-mode` is given **without a search pattern**.
- Remove dead / unreachable branches related to training inside the search loop.
- Develop a cleaner argument system for the NIKL corpora:
  - ~~`--period`~~
  - `--document-type`
- Update `README.md` and additional documents to reflect the updated pipeline.

---

## Phase 2. Tagger Refactoring: Engine vs Interaction
**Goal:** Prevent `tagger.py` from becoming a monolith as functionality grows.

- Separate *analysis logic* from *interactive UI*:
  - **Analysis engine**
    - candidate generation
    - scoring and constraints
    - (future) inflection-internal segmentation
  - **Training UI**
    - interactive prompts
    - gold confirmation and saving
- Consolidate duplicated interaction helpers (e.g. `ask_yes_no`) into a shared utility layer.
- Improve handling of tokens where a Chinese character is followed by its phonetic realization.

---

## Phase 3. Morphological Analysis Expansion (Core Research Feature)
**Goal:** Move from flat `/INFL` tagging to structured inflectional analysis.

- Extend the analysis model to support:
  - stem + ordered list of inflectional morphemes  
    (e.g. `nilo/LEM-te/IPFV-si/HON-ni/FIN`)
- Redesign training data format to store:
  - unique token IDs (e.g. `source_id:token_index`)
  - internal inflectional segmentation
- Introduce a morpheme-level lexicon and ordering constraints  
  (e.g. TAM → HON → FIN).
- Implement an inflection-internal segmenter (DP / Viterbi-style)
  that minimizes residuals and constraint violations.

---

## Phase 4. Analysis Mode (Successor of the Debug Loop)
**Goal:** Turn ad-hoc debugging into a productive exploratory tool.

- Replace the legacy debug loop with an explicit *analysis mode*:
  - Collect and rank unanalysed residual strings.
  - Export frequent residuals to guide further training.
- Support configurable options:
  - minimum frequency
  - suffix / residual filters
  - top-K output
- Use this mode to narrow down candidates **before** interactive training.

---

## Phase 5. Search & Reporting Enhancements
**Goal:** Make advanced analyses visible and searchable.

- Improve user experience by typing bigram regex patterns in a more intuitive way.
- Support morpheme tagging for bigram searches.
- Fix the issue where word-final boundaries are not respected in monogram searches.
- Modify the bigram-searching function to ignore hits where the first target
  is the last word of the context.
- Improve handling of Unicode input by automatically providing PUA mappings.
- Visualize progress when tagging very large sentences.
- (Future) Enable searching by morphological tags or tag sequences.

---

## Completed / Implemented Features (for reference)
- ~~Support multiple searches without reopening the program~~
- ~~Support searching within existing search results~~
- ~~Rename the `--comment` argument to `--purpose`, and allow adding an optional comment when saving results~~
- ~~Support `--displaycontext` to inspect surrounding context of hits~~
- ~~If no `--path` is given, search in the current working directory~~
- ~~Major refactoring to support newly obtained corpus structures~~
  - structured tokens: sentence → tokens within sentence

---

## Notes
- Completed features are intentionally kept visible to preserve development history.
- Each phase is designed to be commit-friendly and independently testable.
- The roadmap prioritizes pipeline clarity and research-driven extensibility
  over short-term feature additions.