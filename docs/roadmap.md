<!-- Last updated: 2026-04-21 -->

# Roadmap: Pipeline-oriented Refactoring & Feature Expansion

## Overall goal
Gradually refactor the system into a clear, modular pipeline  
(**parse → romanize → tag → analyze/train → search → report**),  
while extending the morphological tagger to analyze internal structure of
inflectional morphology (beyond a flat `/INFL` label).

---

## Phase 1. CLI & Pipeline Stabilization ✅

- ~~Split `run()` into mode-specific pipelines (`run_search`, `run_train`, `run_print_corpus`)~~
- ~~Clarify mode semantics: training mode triggered by `--training-mode`, print mode by `--print-corpus`~~
- ~~Remove dead/unreachable branches~~
- ~~Update documentation to reflect updated pipeline~~
- ⬜ Develop cleaner argument system for NIKL corpora (`--document-type`)

---

## Phase 2. Tagger Refactoring: Engine vs Interaction ✅ (partial)

- ~~Separate analysis logic from interactive UI: `training.py` extracted from `tagger.py`~~
- ~~Consolidate training loop and candidate generation into `training.py`~~
- ⬜ Consolidate duplicated interaction helpers (e.g. `ask_yes_no`) into a shared utility layer
- ⬜ Improve handling of tokens where a Chinese character is followed by its phonetic realization

---

## Phase 3. Morphological Analysis Expansion ✅

- ~~Extend analysis model to support stem + ordered inflectional morpheme chains~~
  - e.g., `nilo/V/LEM-te/IPFV-si/HON-ni/FIN`
- ~~Redesign training data format to store inflectional segmentation (`gold_morph` in JSONL)~~
- ~~Introduce morpheme-level lexicon built from training data (`infl_decomp`, `pos_to_allowed_morphemes`)~~
- ~~Implement inflection-internal segmenter (learned suffix decomposition from training data)~~

---

## Phase 4. Training Efficiency

- ~~Skip tokens already present in `token_gold` (re-annotation prevention)~~
- ~~Skip tokens fully parseable from existing lexicon + `infl_decomp` (`has_known_parse`)~~
  - Monogram loop: implemented
  - Bigram loop: deferred — skip criteria depend on definition of "important bigram" (analytic constructions), which has not yet been decided
- ~~Add candidate caching to avoid repeated `candidate_generator()` calls~~
- ~~Add timing instrumentation to training pipeline~~
- ⬜ Define and implement bigram skip criteria based on analytic construction patterns

---

## Phase 5. Analysis / Corpus Overview Mode

- ~~`--print-corpus` mode: prints `unicode_form: tagged_form` per token~~
- ~~Coverage display in training mode (covered/total tokens)~~
- ⬜ Collect and rank unanalyzed residual strings for targeted training
- ⬜ Export frequent residuals to guide further annotation

---

## Phase 6. Search & Reporting Enhancements

- ⬜ Improve bigram regex pattern UX (more intuitive input)
- ⬜ Support morpheme-level tagging for bigram search results
- ⬜ Fix word-final boundary issue in monogram searches
- ⬜ Ignore bigram hits where the first token is the last word in its context
- ⬜ Improve handling of Unicode input by automatically providing PUA mappings
- ⬜ Visualize progress when tagging very large corpora
- ⬜ (Future) Enable searching by morphological tags or tag sequences

---

## Completed features (reference)

- ~~Support multiple searches without reopening the program~~
- ~~Support searching within existing search results~~
- ~~Rename `--comment` to `--purpose`; allow optional comment when saving results~~
- ~~Support `--displaycontext` / `--display-context` to inspect surrounding context of hits~~
- ~~If no `--path` is given, search in the current working directory~~
- ~~Major refactoring to support NIKL XML corpus structure~~
- ~~Period-based file filtering via `<date>` TEI metadata~~
- ~~Bigram search support (space-triggered)~~
- ~~`--exclude-ch`: exclude tokens with Chinese characters~~
- ~~`--classical-ch`: include minimally-annotated classical Chinese tokens~~
- ~~`--sort published_year` for XML files~~
- ~~`--token-repr`: select `yale` vs `tagged_form` for search/training~~

---

## Notes

- Completed features are intentionally kept visible to preserve development history.
- Each phase is designed to be commit-friendly and independently testable.
- The roadmap prioritizes pipeline clarity and research-driven extensibility over short-term feature additions.
- `/LEM`-only tagged tokens will eventually require a dedicated relabeling session to attach finer-grained POS information.
